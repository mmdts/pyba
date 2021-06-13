from __future__ import annotations

from abc import abstractmethod
from typing import Optional, List, Deque, Callable, Tuple, Dict
from collections import deque

from terrain import Terrain, C, D, Locatable, Inspectable
from log import debug, J, C as LOG_C


class Unit(Locatable):
    # Action distance is checked to be anywhere between SAFE_ACTION_DISTANCE squares south / west,
    # and ACTION_DISTANCE squares north / east.
    # Therefore, instead of complex checks, if I want to keep out, I'll check for SAFE_ACTION_DISTANCE,
    # and if I want to be in, I'll check for ACTION_DISTANCE (guarantees being in regardless of orientation).
    # Action distance is inclusive (compared with <= or >=)
    ACTION_DISTANCE = 15
    SAFE_ACTION_DISTANCE = 16

    """Basic Functions"""

    # ONLY click_ AND inspect_ METHODS AND __init__ AND __call__ SHOULD USE THE self.game VARIABLE!!
    # All other methods should be passed the parameters they need explicitly!
    def __init__(self, location: C, game: Inspectable):
        super().__init__(location)
        self.followee: Optional[Locatable] = None
        self.followee_last_found: Optional[C] = None
        self.game: Inspectable = game
        # self.target is not used for any reason other than debugging anyway.
        self.target: C = self.location.copy()  # It changes, it needs to be a copy.
        self.pathing_queue: Deque[C] = deque()
        # Using poison, using GameObjects, picking items, attacking.
        self.post_move_action_queue: List[Tuple[Callable, Tuple, Dict]] = []  # A callable, its args, and its kwargs.
        self.post_wait_action_queue: List[Tuple[Callable, Tuple, Dict]] = []
        self.is_running: bool = False
        assert self.location is not None, "Cannot create a unit without a location."

    def __call__(self) -> bool:
        return self.unit_call()

    def str_info(self) -> str:
        return f"{LOG_C}{'Unnamed':<11}({self.game.tick:0>3}, _, _)@{str(self.location)}{J}"

    def __str__(self):
        return self.str_info()
    def unit_call(self) -> bool:
        # Process the game tick for this entity. Returns false on death.

        # If there are still tiles left in the pathing queue, we only exhaust the wait queue, otherwise, we exhaust
        # the move queue as well.
        self.exhaust_pmac(len(self.pathing_queue) != 0)

        # Process movement.
        self.step()
        pass  # TODO: BUILD Attack with a ranged/melee weapon
        pass  # TODO: BUILD Handle attack delay (Attacker / Penance Fighter / Penance Ranger)
        pass  # TODO: BUILD Other Npc-only stuff, check Npc page and fill

        return True  # By default, units don't do anything that kills them.

    def exhaust_pmac(self, wait_only: bool):
        # To prevent actions that queue more actions from forming an infinite loop.
        # Also prevents actions queued by other actions from being performed on the same tick, rather than a tick later.
        r = len(self.post_move_action_queue)
        rf = len(self.post_wait_action_queue)

        if not wait_only:
            for i in range(r):
                debug("Unit.exhaust_pmac", f"{str(self)} exhausting a pmac entity.")
                action, args, kwargs = self.post_move_action_queue.pop(0)
                action(*args, **kwargs)

        # Wait action queue is never reset by anything.
        for i in range(rf):
            debug("Unit.exhaust_pmac", f"{str(self)} exhausting a forced pmac entity.")
            action, args, kwargs = self.post_wait_action_queue.pop(0)
            action(*args, **kwargs)

    def queue_action(self, action: Tuple[Callable, Tuple, Dict], forced: bool = False):
        if forced:
            self.post_wait_action_queue.append(action)
        else:
            self.post_move_action_queue.append(action)

    """Boolean Functions"""

    def can_single_step(self, destination: C) -> bool:
        return self.location.can_single_step(destination)

    def can_act_on(self, target: Locatable, action_range: Optional[int] = None) -> bool:
        # Specify action_range as a parameter when doing a long range action (attacking).
        # This causes action distance and sight mechanics to be used.
        # Otherwise, follow mechanics are used.
        if action_range is not None and action_range > 1:
            return self.location - target.location <= action_range and self.can_see(target)

        # The target can be acted upon from any adjacent square.
        if target.follow_type == D.B:
            return self.location.taxicab_to(target.location) <= 1

        # The target needs to be acted upon from a specific square.
        return target.location + target.follow_type == self.location

    def is_within_action_distance_of(self, target) -> bool:  # target: Penance
        return target.is_alive() and target.location - self.location <= Unit.ACTION_DISTANCE

    def is_outside_action_distance_of(self, target) -> bool:  # target: Penance
        return not target.is_alive() or target.location - self.location > Unit.SAFE_ACTION_DISTANCE

    def can_see(self, target: Locatable):
        return self.location.can_see(target.location)

    """Get Functions"""

    def get_closest_adjacent_square_to(self, destination: C) -> C:  # TODO: CHECK that this has NS preference.
        return destination + (self.location - destination).single_step_taxicab()

    """Movement Functions"""
    # Npcs and Players move differently.
    # For Npcs, simply set self.target then call Npc.step.
    # For players, simply call Player.move with a destination argument.

    @abstractmethod
    def path(self, destination: C = None, start: C = None) -> C:
        # Pathing for a default unit does not exist. Npcs use Npc.path (dumb pathfinding) and Players use
        # Player.path (smart pathfinding). You can check those instead for more details.
        raise NotImplementedError(f"{self.__class__.__name__} needs to implement Unit.path.")

    def follow(self, target: Locatable, on_reach: Tuple[Callable, Tuple, Dict] = None) -> bool:
        # Default follow behavior is persistent. Manually set followee to None to stop following.
        # Follow doesn't move you. It requires an explicit call to Player.move or Npc.step to move you.
        if not target.is_followable():
            # Runners are not followable, outside of red-clicking them with something that causes you to run into
            # melee range of them. There is no other way in Runescape to reliably land beside a runner.
            # Since no reasons exist to try to reliably land beside a runner in Barbarian Assault,
            # following them simply returns.
            #
            # In contrast, all of eggs, hammer, logs, traps, cannon, hopper, dispensers, fighters, rangers, healers,
            # players (all 5) are followable, and have very valid reasons for being followed.
            return False

        if target.follow_type == D.B:
            destination = self.get_closest_adjacent_square_to(target.location)
        else:
            destination = target.location + target.follow_type

        if destination is not None and on_reach is not None:
            self.queue_action(on_reach)

        self.followee = target
        self.followee_last_found = target.location

        if destination == self.target:
            return False

        self.target = destination
        return True

    def stop_movement(self):
        self.pathing_queue.clear()
        self.target = self.location.copy()
        self.followee = None
        self.followee_last_found = None

    """Stepping Functions"""

    def cant_single_step_callback(self, tile: C) -> None:
        # This method is called if the single step fails.
        self.post_move_action_queue.clear()

    def single_step(self) -> bool:
        # Returns True if unit has moved indeed, False if failed to move.
        if len(self.pathing_queue) == 0:
            return False

        tile = self.pathing_queue.popleft()

        if not self.can_single_step(tile):
            self.cant_single_step_callback(tile)
            return False

        # This style saves reallocation and gc over self.location = tile.copy(). It also allows the location update to
        # propagate to things that use self.location as a read-only value, since self.location changes instead of take
        # on a completely new value. There is currently no part in the code that makes use of this though.
        self.location.x = tile.x
        self.location.y = tile.y

        return True

    def step(self) -> None:
        if not self.single_step():
            return
        if self.is_running:
            self.single_step()

    """Misc Functions"""

    def view_last_path(self) -> str:
        # Print the return value of this method after issuing a move command to figure out what's going on.
        tmp = Terrain.new()
        for tile in self.pathing_queue:
            Terrain.set_letter(tile, "@", tmp)
        rv = "\n".join(tmp)
        del tmp
        return rv
