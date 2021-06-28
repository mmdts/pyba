from __future__ import annotations

from abc import abstractmethod
from typing import Optional, List, Deque, Tuple, Type, Callable
from collections import deque

from log import debug, J, C as LOG_C
from .terrain import Terrain, C, D, Locatable, Inspectable


class Unit(Locatable):
    # Action distance is checked to be anywhere between SAFE_ACTION_DISTANCE squares south / west,
    # and ACTION_DISTANCE squares north / east.
    # Therefore, instead of complex checks, if I want to keep out, I'll check for SAFE_ACTION_DISTANCE,
    # and if I want to be in, I'll check for ACTION_DISTANCE (guarantees being in regardless of orientation).
    # Action distance is inclusive (compared with <= or >=)
    ACTION_DISTANCE: int = 15
    SAFE_ACTION_DISTANCE: int = 16
    PRE: bool = False
    POST: bool = True

    # ONLY click_ AND inspect_ METHODS AND __init__ AND __call__ SHOULD USE THE self.game VARIABLE!!
    # All other methods should be passed the parameters they need explicitly!
    def __init__(self, location: C, game: Inspectable):
        super().__init__(location, game)
        self.followee: Optional[Locatable] = None
        self.followee_last_found: Optional[C] = None
        self.game: Inspectable = game
        self.destination: C = self.location.copy()  # It changes, it needs to be a copy.
        self.pathing_queue: Deque[C] = deque()
        # Using poison, using GameObjects, picking items, attacking.
        self.is_running: bool = False

        self.action_args: Tuple = ()
        self.actions: List[Tuple[Type[Locatable], Callable, bool]] = []
        assert self.location is not None, "Cannot create a unit without a location."

    @abstractmethod
    def __call__(self) -> bool:
        # Process the game tick for this entity. Returns false on death.
        raise NotImplementedError(f"{self.__class__.__name__} needs to implement Unit.call.")

    def str_info(self) -> str:
        return f"{LOG_C}{'Unnamed':<11}({self.game.tick:0>3}, _, _)@{self.location}{J}"

    def __str__(self) -> str:
        return self.str_info()

    @property
    @abstractmethod
    def choice_arg(self) -> List[Locatable]:
        raise NotImplementedError("Specific Npc species/Players should override this function "
                                  "to specify what they follow.")

    def can_single_step(self, destination: C) -> bool:
        return self.location.can_single_step(destination)

    def can_act_on(self, target: Optional[Locatable], action_range: Optional[int] = None) -> bool:
        # Specify action_range as a parameter when doing a long range action (attacking).
        # This causes action distance and sight mechanics to be used.
        # Otherwise, follow mechanics and sight mechanics are used.

        # Target is None, we can't act on it.
        if target is None:
            return False

        # We're ranged, so we can act from afar.
        if action_range is not None and action_range > 1:
            return 0 < self.location.chebyshev_to(self.followee.location) <= action_range and self.can_see(target)

        # The target can be acted upon from any adjacent square, including the square under.
        if target.follow_type == D.B and target.follow_allow_under:
            return self.location.taxicab_to(target.location) <= 1 and self.can_see(target)

        # The target can be acted upon from any adjacent square, excluding the square under.
        if target.follow_type == D.B:
            return self.location.taxicab_to(target.location) == 1 and self.can_see(target)

        # The target needs to be acted upon from a specific square.
        # This is the only condition that doesn't require sight.
        return target.location + target.follow_type == self.location

    def act(self, act_mode: bool = POST) -> bool:
        if self.followee is None or not self.can_act_on(self.followee):
            return False

        for locatable_type, action, action_mode in self.actions:
            if not isinstance(self.followee, locatable_type) or action_mode != act_mode:
                continue

            try:
                rv = action(*self.action_args)
            except AssertionError as e:
                rv = False
                debug("Unit.act", f"{self} returned False due to the assertion: {str(e)}")

            self.action_args = ()
            self.stop_movement()
            return rv

    def is_within_action_distance_of(self, target) -> bool:  # target: Penance
        return target.is_alive() and target.location - self.location <= Unit.ACTION_DISTANCE

    def is_outside_action_distance_of(self, target) -> bool:  # target: Penance
        return not target.is_alive() or target.location - self.location > Unit.SAFE_ACTION_DISTANCE

    def can_see(self, target: Locatable) -> bool:
        return self.location.can_see(target.location)

    def get_closest_adjacent_square_to(self, target: Locatable) -> C:
        # Both Player and Npc override this. This is just a fallback implementation that
        # does not respect target.follow_allow_under mechanics.
        return target.location + (self.location - target.location).single_step_taxicab()

    # Npcs and Players move differently.
    # For Npcs, simply set self.target then call Npc.step.
    # For players, simply call Player.move with a destination argument.

    @abstractmethod
    def path(self, destination: C = None, start: C = None) -> C:
        # Pathing for a default unit does not exist. Npcs use Npc.path (dumb pathfinding) and Players use
        # Player.path (smart pathfinding). You can check those instead for more details.
        raise NotImplementedError(f"{self.__class__.__name__} needs to implement Unit.path.")

    def follow(self, followee: Locatable) -> bool:
        # Default follow behavior is persistent. Manually set followee to None to stop following.
        # Follow doesn't move you. It requires an explicit call to Player.move or Npc.step to move you.
        if not followee.is_followable():
            # Runners are not followable, outside of red-clicking them with something that causes you to run into
            # melee range of them. There is no other way in Runescape to reliably land beside a runner.
            # Since no reasons exist to try to reliably land beside a runner in Barbarian Assault,
            # following them simply returns.
            #
            # In contrast, all of eggs, hammer, logs, traps, cannon, hopper, dispensers, fighters, rangers, healers,
            # players (all 5) are followable, and have very valid reasons for being followed.
            return False

        if followee.follow_type == D.B:
            destination = self.get_closest_adjacent_square_to(followee)
        else:
            destination = followee.location + followee.follow_type

        self.followee = followee
        self.followee_last_found = followee.location

        if self.location == destination and self.can_act_on(followee):
            return False

        self.destination = destination
        return True

    def refollow(self) -> bool:
        if self.followee is None:
            return False

        if len(self.choice_arg) > 0 and self.followee not in self.choice_arg:
            debug("Unit.refollow", f"{self} was following {self.followee} but it can't anymore.")
            self.stop_movement()
            return False

        debug("Unit.refollow", f"{self} is following {self.followee} and decided to refollow it.")
        self.follow(self.followee)  # Re-follow a followee that might move.
        return True

    def stop_movement(self, clear_destination: bool = False, clear_follow: bool = False) -> None:
        if not clear_destination and not clear_follow:
            # A stop movement command called without any arguments should clear both.
            clear_destination = True
            clear_follow = True

        if clear_destination:
            self.pathing_queue.clear()
            self.destination = self.location.copy()
        if clear_follow:
            self.followee = None
            self.followee_last_found = None

    @abstractmethod
    def cant_single_step_callback(self, tile: C) -> None:
        raise NotImplementedError(f"{self.__class__.__name__} needs to implement Unit.cant_single_step_callback.")

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

    def view_last_path(self) -> str:
        # Print the return value of this method after issuing a move command to figure out what's going on.
        tmp = Terrain.new()
        for tile in self.pathing_queue:
            Terrain.set_letter(tile, "@", tmp)
        rv = "\n".join(tmp)
        del tmp
        return rv
