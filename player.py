from abc import abstractmethod
from collections import deque
from random import random
from typing import Optional, List

from dispenser import Dispenser
from log import debug, J, C as LOG_C
from terrain import Terrain, C, Inspectable, Y, Locatable, D
from unit import Unit


# All manual player actions should ideally start with the click_ prefix, and they are:
# Player:    click_move, click_call,  click_use_dispenser,  click_use_cannon,   click_fire_egg,    click_idle
#            click_destroy_items
# Collector: click_use_egg_on_cannon, click_load_cannon,    click_empty_bag,    click_pick_item
# Attacker:  click_attack_combat_npc, click_change_weapon,  click_change_style, click_stall,       click_spec
# Defender:  click_pick_item,          click_repair_trap,   click_drop_food
# Healer:    click_use_poison_food
#
# Attacker.click_change_style is needed for guessing with human collectors that don't call (changes style or arrows).
#
# TODO: BUILD Render Distances [THREAD]
#       Check for tile render distance (30) when moving (cant move to healer cave when at dispenser in one click)
#       Check for item render distance when picking up items (cant pick logs/far eggs when at dispenser)
#       Check for game_object render dist (30) when interacting with one (can't repair west trap from east trap)
#       Check for unit render distance (15) when using poison food (can't poison a healer that's not rendered)
#       Check for rendering on all click_ functions.
class Player(Unit):
    # For pathing. The Barbarian Assault map is simple and small. It has 1116 pathable tiles, and therefore, we do not
    # need to consider the BFS distance to anything more.
    BFS_LIMIT: int = 1120
    INVENTORY_SPACE: int = 28
    CALL_COUNT: int = 3

    def __init__(self, location: C, game: Inspectable):
        super().__init__(location, game)
        self.is_running: bool = True
        self.calls_with: Optional[Player] = None
        self.inventory: List[str] = [Y.HORN] + [Y.EMPTY] * (Player.INVENTORY_SPACE - 1)
        self.busy_i: int = 0
        Terrain.block(self.location)

    def __call__(self):
        if self.busy_i > 0:  # Cannot move or do any other action when busy (repairing trap / using dispenser).
            debug("Player.__call__", f"{self} is currently busy with busy_i = {self.busy_i}.")
            self.busy_i -= 1
            return True

        return super().__call__()

    @property
    def name(self):
        # Currently used only for printing.
        return self.__class__.__name__

    def str_info(self) -> str:
        return f"{LOG_C}{self.name:<11}({self.game.tick:0>3}, _, _)@{self.location}{J}"

    @staticmethod
    @abstractmethod
    def access_letter() -> str:
        raise NotImplementedError("Access letter is not implemented for this player.")

    def get_closest_adjacent_square_to(self, target: Locatable) -> C:
        if not target.follow_allow_under and self.location == target.location:
            return target.location + D.W  # Players will always path west to get out from under an Npc.
        return target.location + (self.location - target.location).single_step_taxicab()

    def path(self, destination: C = None, start: C = None) -> C:
        # Smart pathfinding (referred to as Player.path) creates an entire path per call, using breadth-first search.
        # In theory, Player.path can be used with either move flavors (Npc.move or Unit.move), but using it with
        # Unit.move saves processing power, and is thus recommended.
        #
        # No use cases exist for using Player.path with Npc.move, therefore the decision to make this style of pathing
        # unique to the player instead of base on Unit, and setting the Unit.path method to abstract.
        #
        # Player pathing in Runescape has extra complexity with checkpoints, that causes quirks such as running past
        # the healer you're trying to poison, but for the purposes of this simulation, we can neglect such complexity
        # in order to save processing time and programming effort.
        #
        # Player pathing in Runescape also accounts for completely unreachable tiles, and trying to path to tiles that
        # require very long paths (like in a maze). However, neither are an issue in Barbarian Assault, and thus, such
        # complexity is not required for the purpose of this simulation.
        #
        # Player.path completely ignores path_more_than_one_tile, as it always paths the full thing.
        # The method argument is just there for compatibility with super().
        if start is None:
            start = self.location.copy()

        if destination is None:
            destination = self.destination.copy()

        closest = start  # We need to keep track of the closest tile in case BFS does not conclude.
        closest_distance = start.chebyshev_to(destination)  # The closest tile is decided based on chebyshev distance.
        visited = set()
        bfs_queue = deque([start])
        visited.add(start)
        bfs_i = 0

        while True:
            vertex = bfs_queue.popleft()
            vertex_distance = vertex.taxicab_to(destination)

            if vertex_distance < closest_distance:
                closest_distance = vertex_distance
                closest = vertex

            for tile in vertex.get_adjacent_tiles():
                if vertex.can_single_step(tile) and (tile not in visited):
                    tile.parent = vertex

                    if tile == destination:
                        return tile
                    visited.add(tile)
                    bfs_queue.append(tile)

            if len(bfs_queue) == 0:
                debug("Player.path", f"{self}'s bfs_queue finished before we find a path.")
                return closest

            bfs_i += 1

            # BFS queue should always be empty (triggering the condition above) before bfs_i hits BFS_LIMIT.
            # This condition should never be reached.
            if bfs_i == Player.BFS_LIMIT:
                debug("Player.path", f"{self} tried more than BFS_LIMIT pops "
                                     f"in bfs_queue but couldn't find a path.")
                return closest

    def move(self, destination: C) -> None:
        # Continuous path moving (referred to as Player.move), which tries to move straight to the destination,
        # and tries to build the entire pathing queue using Player.path.
        #
        # Continuous moving can be called once, and the rest of the "action" that happens every tick
        # to move the unit can be delegated to Unit.step, which exhausts the pathing queue at the rate of
        # one or two tiles per tick depending on whether the unit is running.
        #
        # Any move command should overwrite any existing move commands.
        debug("Player.move", f"{self} fires a move.")
        self.stop_movement()
        self.destination = destination  # For other classes to know that we're pathing.

        # First, we do pathing.
        destination = self.path(destination, None)

        # If a path is found, we follow it backwards and place it in the pathing_queue,
        # calculating checkpoints in the checkpoint_queue along the way.
        while destination is not None:
            self.pathing_queue.appendleft(destination)
            destination = destination.parent

        if len(self.pathing_queue) == 0:
            self.stop_movement()
            debug("Player.move.pathing_queue", f"{self} tried to path but ended up with an empty pathing queue.")
            return

        # The leftmost element should be the current tile, we pop it.
        self.pathing_queue.popleft()
        debug("Player.move.pathing_queue", f"{self}'s final pathing queue is: {Terrain.queue_info(self.pathing_queue)}")

    def cant_single_step_callback(self, tile: C) -> None:
        # This method is called if the single step fails.
        # Tile argument is present even though it's never used because the calling function
        # provides it, and we need to receive it.
        self.post_move_action_queue.clear()

    def single_step(self) -> bool:
        # Players will unblock the tile they move from and block the tile they move to,
        # otherwise doing a normal Unit.single_step.

        # The conditions for location change cannot be decided without inspecting the pathing queue, making it much
        # easier to inspect Unit.single_step return value instead of re-checking. However, Unit.single_step changes
        # our location. This is why we need to "remember" what out location before stepping was.
        old_location = self.location.copy()

        location_changed = super().single_step()

        if location_changed:
            Terrain.unblock(old_location)
            Terrain.block(self.location)
            debug("Player.single_step", f"{self} successfully single stepped to {self.location}.")

        return location_changed

    def _use_dispenser(self, dispenser: Dispenser, option: Optional[int] = None) -> None:
        # You self._use_dispenser() in all Player.use_dispenser implementations.
        # Previously, we used to run checks like self.location == E.DEFENDER_RESTOCK_SPOT
        # but right now, it's better to check for adjacency to the dispenser and entirely
        # refactor E.*_RESTOCK_SPOT variables out of the codebase.
        assert self.can_act_on(dispenser), \
            "Too far away to restock. Please only use the Player.use_dispenser function after following the dispenser."
        assert option is None or option is Dispenser.DEFAULT_STOCK or self.access_letter == "h", \
            "Only the healer can specify options when using the dispenser."

    @abstractmethod
    def use_dispenser(self, dispenser: Dispenser, option: Optional[int] = None) -> None:
        # Option is the various things you can do by right clicking the dispenser.
        # Option only makes sense for healer, as no other role has a reason to right click a dispenser.
        raise NotImplementedError(f"{self.__class__.__name__} needs to implement Player.click_use_dispenser.")

    @property
    def required_call(self) -> int:
        # Required to SEND!
        return self.game.wave.correct_calls[self.calls_with.access_letter()]

    @property
    def sent_call(self) -> int:
        return self.game.wave.calls[self.calls_with.access_letter()]

    @sent_call.setter
    def sent_call(self, value: int) -> None:
        self.game.wave.calls[self.calls_with.access_letter()] = value

    @property
    def received_call(self):
        return self.game.wave.calls[self.access_letter()]

    @property
    def correct_call(self):
        # Required to USE!
        return self.game.wave.correct_calls[self.access_letter()]

    # TODO: BUILD Inspect Functions [THREAD]
    #       Make the interfaces only able to interact with the class through click and inspect.
    #       No longer should it read (or even be allowed access to) any other class properties.
    #       As for interacting with the game, a toggle option "Disable Fog of War" should allow
    #       you to observe actions outside your render distances.

    # Click functions return False if the player cannot do the action.

    def click_use_dispenser(self, option: Optional[int] = None) -> bool:
        dispenser = self.game.wave.dispensers[self.access_letter()]
        if not self.location.renders_game_object(dispenser):
            return False
        self.follow(dispenser, (self.use_dispenser, (dispenser, option), {}))
        self.move(self.destination)
        return True

    def click_destroy_items(self, inventory_slots: List[int]) -> bool:
        for slot in inventory_slots:
            if self.inventory[slot] != "_" and self.inventory[slot] != "X":
                self.inventory[slot] = "_"
        return True

    def click_move(self, destination: C) -> bool:
        # Clicking to move cancels any current actions.
        # Please use this to move the players on player action, and not the move function.
        if not self.location.renders_tile(destination):
            return False

        self.post_move_action_queue.clear()
        self.move(destination)
        return True

    # noinspection PyMethodMayBeStatic
    def click_idle(self) -> bool:
        return True

    def click_call(self, mess_up_probability: float = 0) -> bool:
        # Mess up probability is a number between 0 and 1
        assert self.calls_with is not None, "This player has to calls_with someone in order to click_call."
        correct_call = self.required_call
        my_call = correct_call
        if random() < mess_up_probability:  # We messed up!
            my_call = int(random() * (self.CALL_COUNT - 1))
            if my_call >= correct_call:
                my_call += 1
        self.sent_call = my_call
        return my_call == correct_call

    def click_select_call(self, call: float = 0) -> bool:
        # Mess up probability is a number between 0 and 1
        assert self.calls_with is not None, "This player has to calls_with someone in order to click_call."
        self.sent_call = call
        return call == self.required_call
