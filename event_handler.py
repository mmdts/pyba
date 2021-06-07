from typing import List, Callable, Optional, Dict, Tuple

from room import Room
from log import debug
from role_player import Defender, Healer, Collector, MainAttacker, SecondAttacker
from player import Player
from terrain import C, G, Terrain


class EventHandler:
    # This class only has static constants / static methods.

    # For each of the following constants, each key is the name of a function inside Player or a class that inherits
    # from it. The value at each key is a tuple that has two lambdas, the first being the check condition required
    # to execute this function, and the second being a lambda that morphs arguments passed from client into those
    # understood by said function.

    PLAYER_ACTIONS: Dict[str, Tuple[Callable, Callable]] = {
        # args: x, y
        "click_move": (
            lambda args: len(args) == 2,
            lambda args: (C(*args),)
        ),
        "click_select_call": (
            lambda args: len(args) == 1,
            lambda args: args
        ),
        # args: option (for healer)
        "click_use_dispenser": (
            lambda args: len(args) <= 1,
            lambda args: (len(args) and args[0] or None,)
        ),
        # args: which
        "click_use_cannon": (
            lambda args: len(args) == 1,
            lambda args: args
        ),  # TODO: BUILD click_use_cannon handling.
        # args: which
        "click_fire_egg": (
            lambda args: len(args) == 1,
            lambda args: args
        ),  # TODO: BUILD click_fire_egg handling.
        # args: None
        # args: slots
        "click_destroy_items": (
            lambda args: len(args) == 1,
            lambda args: args
        ),
        "click_idle": (
            lambda args: len(args) == 0,
            lambda args: ()
        ),
    }

    DEFENDER_ACTIONS: Dict[str, Tuple[Callable, Callable]] = {
        # args: item_uuid
        "click_pick_item": (
            lambda args: len(args) == 1,
            lambda args: (G.find_by_uuid(args[0]),)
        ),
        # args: None
        "click_repair_trap": (
            lambda args: len(args) <= 1,
            lambda args: args
        ),
        # args: which, count
        "click_drop_food": (
            lambda args: len(args) == 2,
            lambda args: args
        ),
        # args: slots
        "click_drop_select_food": (
            lambda args: len(args) == 1,
            lambda args: args
        ),
    }

    HEALER_ACTIONS = {
        # args: which
        "click_use_poison_food": (
            lambda args: len(args) == 1,
            lambda args: args
        ),  # TODO: BUILD click_use_poison_food handling.
    }

    COLLECTOR_ACTIONS = {  # TODO: Build actions for a/s/c roles.
    }

    MAIN_ATTACKER_ACTIONS = {
    }

    SECOND_ATTACKER_ACTIONS = {
    }

    @staticmethod
    def handle_room_event(action: str, args: List, room: Room, client: str) -> bool:
        # Only the True client (first client to connect to the room, and the room's creator) can cause room events.
        if client not in room.clients_by_id or not room.clients_by_id[client]:
            return False

        if action == "new_wave" and len(args) == 2:
            room.game.start_new_wave(args[0] - 1, Terrain.parse_runner_movements(args[1]))
            return True

        if action == "toggle_mode" and len(args) == 1:
            room.set_mode(args[0])
            return True

        if action == "step" and len(args) == 0:
            room.set_mode(Room.PAUSE)
            room()
            return True

        return False

    @staticmethod
    def handle_player_event(action: str, args: List, player: Player, add_fn: Callable,
                            actions_list: Optional[Dict[str, Tuple[Callable, Callable]]] = None) -> bool:
        if actions_list is None:
            actions_list = EventHandler.PLAYER_ACTIONS

        if action in actions_list and actions_list[action][0](args):
            add_fn(
                player.__getattribute__(action),
                *actions_list[action][1](args)
            )
            return True

        return False

    @staticmethod
    def handle_role_player_event(action: str, args: List, room: Room, client: str) -> bool:
        player = room.get_player(client)

        if player is None:
            return False

        actions_list = EventHandler.PLAYER_ACTIONS

        if isinstance(player, Defender):
            actions_list = EventHandler.DEFENDER_ACTIONS

        if isinstance(player, Healer):
            actions_list = EventHandler.HEALER_ACTIONS

        if isinstance(player, Collector):
            actions_list = EventHandler.COLLECTOR_ACTIONS

        if isinstance(player, MainAttacker):
            actions_list = EventHandler.MAIN_ATTACKER_ACTIONS

        if isinstance(player, SecondAttacker):
            actions_list = EventHandler.SECOND_ATTACKER_ACTIONS

        if EventHandler.handle_player_event(action, args, player, room.add, actions_list):
            return True

        return EventHandler.handle_player_event(action, args, player, room.add, EventHandler.PLAYER_ACTIONS)

    @staticmethod
    def handle(action: str, args: List, room: Room, client: str) -> bool:
        # Receives an action.
        debug("EventHandler.handle", "Received", action, args)

        if EventHandler.handle_room_event(action, args, room, client):
            return True

        if EventHandler.handle_role_player_event(action, args, room, client):
            return True

        return False
