import json
from typing import Dict
from uuid import UUID

from flask import Flask, request
from flask_socketio import SocketIO, join_room, leave_room

from log import debug
from simulation import EventHandler, Room
from .emit import build_emittable_object_from

# The architecture is:
# ONE interface (not a class).
# ONE EventHandler.
# Many Rooms.
# One Game per room.
# One or more players (real) per room.
# Rest are either AI or None.

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret!"
app.config["CORS_HEADERS"] = "Content-Type"
server: SocketIO = SocketIO(app, cors_allowed_origins="*")

rooms: Dict[str, Room] = {}
active_sids: Dict[str, str] = {}  # Maps from request.sid client ids to uuid room ids.
event_handler = EventHandler()


def emit(self) -> None:
    # Should provide a full game state, ending on something that's Transmittable.
    rv = json.dumps({
        "game": build_emittable_object_from(self.game.inspectable),
    })

    self.game.inspectable.text_payload = []

    return self.server.emit("game_state", rv, to=self.id)


setattr(Room, "emit_state", emit)


@server.on('disconnect')
def disconnect_handler() -> None:
    if request.sid not in active_sids:  # The user closed the client before creating / joining a room.
        return

    # This happens early so that spectators leave the room even though their leaving the room does not destroy it.
    leave_room(active_sids[request.sid])

    if active_sids[request.sid] not in rooms:  # Spectators cause this (among other weird cases).
        return

    if not isinstance(rooms[active_sids[request.sid]], Room):
        return

    if request.sid not in rooms[active_sids[request.sid]].clients_by_id:
        return

    del rooms[active_sids[request.sid]].clients_by_id[request.sid]

    if len(rooms[active_sids[request.sid]].clients_by_id) == 0:
        rooms[active_sids[request.sid]].is_alive = False
        del rooms[active_sids[request.sid]]

    debug("Interface.disconnect_handler", f"Room deleted. There are {len(rooms)} rooms left.")


@server.on("client_action")
def on_client_action(message=None) -> None:
    # This function is the roof of all exceptions. As no user code calls this function (Flask does), this function
    # has to internally handle all exceptions that arise from it, or from any part of the stack beneath it.
    try:
        if message is None or len(message) == 0:  # Polling messages do not have a message body.
            return
        preprocess = json.loads(message)

        assert "room" in preprocess, "Preprocessed JSON needs to have a room uuid."
        assert "args" in preprocess, "Preprocessed JSON needs to have an args array."
        assert "action" in preprocess, "Preprocessed JSON needs to have an action."
        room_id = preprocess["room"]
        args = preprocess["args"]
        action = preprocess["action"]

        # New rooms have to be handled here, as the EventHandler expects rooms to be passed as parameters.
        if action == "room_create":
            assert 1 <= len(args) <= 2, "Only the role and maybe mode should be passed as argument to room creation."
            room = room_create(room_id)
            if room_connect(room_id, request.sid, args[0]):
                join_room(room_id)
            if len(args) == 2:
                room.set_mode(args[1])

            # SET_MODE CALLS THE ROOM SO WE DON'T NEED TO CALL IT HERE USING rooms[room_id]()
            return

        # New rooms have to be handled here, as the EventHandler expects rooms to be passed as parameters.
        if action == "room_connect":
            assert len(args) == 1, "Only the role should be passed as argument to room connection."
            if room_connect(room_id, request.sid, args[0]):
                join_room(room_id)
            return

        event_existed = event_handler.handle(
            action=action,
            args=args,
            room=rooms[room_id],
            client=request.sid,
        )

        if event_existed:
            return

        assert event_existed, f"Either the action {action} does not exist, " \
                              f"an incorrect number of arguments {args} has been provided, " \
                              "or this type of player does not support this type of action."

    except (TypeError, AssertionError, AttributeError, NotImplementedError, KeyError) as e:
        server.emit("error", json.dumps(str(e)), to=request.sid)
        raise e


def is_valid_uuid(uuid_to_test, version=4) -> bool:
    try:
        uuid_obj = UUID(uuid_to_test, version=version)
    except ValueError:
        return False
    return str(uuid_obj) == uuid_to_test


def room_create(room_id: str) -> Room:
    assert is_valid_uuid(room_id), f"Please provide a syntactically valid uuid for the room instead of {room_id}."
    rooms[room_id] = Room(room_id, server)
    return rooms[room_id]


def room_connect(room_id: str, client_id: str, role: str) -> bool:
    if role == "_":  # A spectator
        active_sids[request.sid] = room_id
        return True

    try:
        assert room_id in rooms, f"You tried to connect to a room {room_id} that does not exist."
        rooms[room_id].accept_player_connection(client_id, role)
    except AssertionError as e:
        debug("Interface.room_connect", "AssertionError:", e)
        return False

    active_sids[client_id] = room_id
    return True


def kill_rooms() -> None:
    for room_id in rooms:
        if rooms[room_id].thread is not None:
            rooms[room_id].thread.join()
        rooms[room_id].thread = None


def run() -> None:
    # The exported function. This is the only thing anything outside this package needs to know about it.
    server.run(app)


def stop() -> None:
    # Currently, flask socketio servers have no way to stop gracefully except through a call from a client.
    server.stop()
    kill_rooms()
