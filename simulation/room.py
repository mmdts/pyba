import traceback
from typing import Callable, List, Dict, Optional, Type
from flask_socketio import SocketIO
from threading import Thread
import json

from log import debug
from .base.player import Player
from .base.terrain import Action
from .game import Game
from .ai import Healer, Ai
from .interface_transmit import build_transmittable_object_from


class Room:
    DELAY_DURATION = 0.6
    DELAY = 0  # Delays for DELAY_DURATION between ticks. Deactivate this if instant-running.
    PAUSE = 1  # Pauses for confirmation between ticks. Deactivate this if using a GUI.
    F_FWD = 2  # Fast forwards. Useful for training a bot.

    def __init__(self, _id: str, server: SocketIO):
        self.is_alive: bool = True
        self.thread: Optional[Thread] = None
        # This room is related to a socketio room. The id (base64 encoded) is considered the room number.
        # The first player to connect to the room creates it, and defines a room id.
        self.id: str = _id
        # Connected SocketIO clients.
        self.clients_by_role: Dict[str, Optional[str]] = {"d": None, "a": None, "s": None, "c": None, "h": None}
        self.clients_by_id: Dict[str, bool] = {}  # The one that has the True is the room initiator.
        self.server: SocketIO = server

        self.ai: Dict[str, Optional[Type[Ai]]] = {
            # "c": RuleBasedCollector,
            "h": Healer,
        }

        self.game: Game = Game()
        self.player_action_queue: List[Action] = []
        self.game.set_new_players(self.ai)  # TODO: No AI. Fix this when AI is implemented.

        self.blocking_action = False  # Flips to true on the first tick of new_wave action.
        self.mode: int = Room.DELAY

    def __call__(self) -> None:
        if self.mode == Room.DELAY or self.mode == Room.F_FWD:
            assert self.thread is None, "You tried calling the room when the thread already exists!"

            def run(room: Room) -> None:
                while True:  # TODO: Multiple connections, multiple games.
                    assert room.is_alive, "Room died. This exception is meant to kill the thread."

                    try:
                        room.iterate()
                    except (TypeError, AssertionError, AttributeError, NotImplementedError, KeyError) as _:
                        debug("Room.__call__", "Encountered an error. Resetting game.")
                        traceback.print_exc()
                        room.game = Game()
                        self.game.set_new_players(self.ai)

                    if room.mode == Room.DELAY:
                        room.server.sleep(Room.DELAY_DURATION)
                    if room.mode == Room.PAUSE:
                        break

            self.thread = Thread(target=run, args=(self,))
            self.thread.start()
        if self.mode == Room.PAUSE:
            self.iterate()

    def iterate(self) -> None:
        assert self.is_alive, "Room died. Please start a new one."
        self.exhaust_queue()
        if self.game.wave is not None:
            if self.game():  # The game call happens here!
                self.blocking_action = False  # A tick passed, now actions can happen again.
                self.transmit()
            else:
                self.game.wave = None
                self.blocking_action = True
                self.player_action_queue.clear()

            # ANY CUSTOM PLAYER CODE GOES HERE!
            pass

    def transmit(self) -> None:
        # Should provide a full game state, ending on something that's Transmittable.
        rv = json.dumps({
            "game": build_transmittable_object_from(self.game.inspectable),
        })

        self.game.inspectable.text_payload = []

        return self.server.emit("game_state", rv, to=self.id)

    def get_player(self, client_id: str) -> Optional[Player]:
        for role in self.clients_by_role:
            if self.clients_by_role[role] == client_id:
                return self.game.players[role]
        return None

    def set_mode(self, mode: int) -> None:
        assert mode in [Room.DELAY, Room.PAUSE, Room.F_FWD], f"Invalid room mode {mode}."
        self.mode = mode
        if mode == Room.PAUSE:
            if self.thread is not None:
                self.thread.join()
            self.thread = None
        else:
            self()

    def accept_player_connection(self, client_id: str, role: str) -> None:
        assert role in self.clients_by_role.keys(), "Please choose a valid role when connecting to the room."
        assert self.clients_by_role[role] is None, \
            f"A player ({self.clients_by_role[role]}) is already assigned to the role {role}."
        self.clients_by_role[role] = client_id
        self.clients_by_id[client_id] = len(self.clients_by_id) == 0  # Set only the first player to True.
        if role in self.ai:
            del self.ai[role]
        if role in self.game.original_ai:
            del self.game.original_ai[role]
        if role in self.game.ai:
            del self.game.ai[role]

    def add(self, action: Callable, *args, **kwargs) -> None:
        self.player_action_queue.append((action, args, kwargs))

    def exhaust_queue(self) -> None:
        while len(self.player_action_queue) > 0:
            item = self.player_action_queue.pop(0)
            item[0](*item[1], **item[2])
