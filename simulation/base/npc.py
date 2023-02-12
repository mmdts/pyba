from random import randrange, choice, randint
from abc import abstractmethod
from typing import List, Tuple

from log import game_print, J, LC
from .terrain import Locatable, C, Inspectable, Targeting, D
from .unit import Unit


class Npc(Unit):
    HITPOINTS: List[int] = None

    DESPAWN_TICKS: int = 2

    # This variable decides how many ticks a new penance would be able to spawn after the last one has taken
    # lethal damage.
    #
    # Healers spawn instantly after lethal damage, and thus have DUE_TO_SPAWN_TICKS = 2
    # Runners spawn 1 tick after taking lethal damage, and thus have DUE_TO_SPAWN_TICKS = 1
    # CombatNpcs spawn 2 ticks after taking lethal damage, and thus have DUE_TO_SPAWN_TICKS = 0
    #
    # The condition for CombatNpcs isn't tick accurate (it depends on how they died), but
    # is good enough for our purposes.
    DUE_TO_SPAWN_TICKS: int

    CYCLE_COUNT: int = 10  # Penance do actions in cycles of CYCLE_COUNT ticks.

    DEAD, ALIVE = 0, 1  # They're binary, but we're leaving them as int for legacy.

    RANDOM_WALK_ROLL: Tuple[int] = (1, 8)  # Represents a 1/8 chance.
    RANDOM_WALK_RADIUS: int = 5

    def __init__(self, location: C, game: Inspectable):
        super().__init__(location, game)
        self.name = self.default_name

        self.cycle: int = 0
        self.despawn_i: int = self.DESPAWN_TICKS
        self.state: int = Npc.ALIVE
        self.hitpoints: int = self.game.arg is not None and self.HITPOINTS[self.game.wave.number] or 1
        self.is_still_static: bool = True
        self.no_random_walk_i: int = 0  # The time it would've taken to reach the destination.

    def __call__(self) -> bool:
        self.cycle += 1  # Cycle starts at 1 and ends at 0 after 9.
        self.cycle %= self.CYCLE_COUNT

        if self.is_alive():
            self.refollow()
            self.do_cycle()
            if self.hitpoints <= 0:
                self.hitpoints = 0
                self.state = Npc.DEAD

        if self.tick_despawn():
            return False  # Our return False (the condition for Npc removal in Penance.__call__).

        return True

    @property
    def default_name(self) -> str:
        return self.__class__.__name__

    @abstractmethod
    def str_info(self) -> str:
        return f"{LC}{self.name:<11}({self.game.tick:0>3}, {self.cycle}, _)@{self.location}{J}"

    def print(self, *args, **kwargs) -> None:
        game_print("Penance.print", f"{self}", *args, **kwargs)
        self.game.text_payload.append(
            " ".join([str(arg) for arg in (
                f"{self.uuid}|", *args
            )])
        )

    @abstractmethod
    def do_cycle(self) -> None:
        # All Npcs call do_cycle during their usual call procedure if they're alive.
        # All Npcs return what do_cycle returns, but since no action despawns non-runner Npcs other than dying and
        # despawning naturally, only runners should ever return False in their do_cycle (as part of the escape
        # procedure).

        # Non-runner Npcs should attempt to all return super().__call__(tick) as part of their usual do_cycle procedure.
        raise NotImplementedError(f"{self.__class__.__name__} needs to implement Npc.do_cycle.")

    def tick_despawn(self) -> bool:
        # Reduces despawn countdown and returns true if it hits -1.
        # To be used inside if conditions.
        #
        # Basically, the Npc starts with despawn_i = 2, and decrements once the same tick it dies.
        # This means that an Npc with despawn_i = 1 is a dead Npc.
        # Healers spawn instantly once dispawn_i hits 1, Runners spawn when despawn_i hits 0, and CombatNpcs
        # when despawn_i hits -1.
        if self.is_alive():
            return False
        self.despawn_i -= 1
        return self.despawn_i == -1

    def is_alive(self) -> bool:
        return self.state == Npc.ALIVE

    def is_followable(self) -> bool:
        return self.is_alive() and super().is_followable()

    def get_closest_adjacent_square_to(self, target: Locatable) -> C:
        if not target.follow_allow_under and self.location == target.location:
            # Npcs will path randomly to get out from under a player.
            return target.location + choice([D.W, D.E, D.S, D.N])
        return target.location + (self.location - target.location).single_step_taxicab()

    def path(self, destination: C = None, start: C = None) -> C:
        # Dumb pathfinding (referred to as Npc.path) tries to only calculate and add one tile per call.
        #
        # A move that relies on Npc.path will only ever move one tile. Maker of the move function is responsible
        # for the repetitive per-tick calling of this function that is going to make the Npc move seamlessly.
        if start is None:
            start = self.location.copy()

        if destination is None:
            destination = self.destination.copy()

        relative = destination - start

        # Always try stepping in x, then always try stepping in y.
        # Legacy note: Diagonal checks are very processor intensive.
        #
        # Keep in mind we can only do this because Npcs won't try to run up cannon, and therefore,
        # the wall processing part (which is why recursion was introduced into diagonal can_single_step)
        # won't be necessary.
        single_step_x = relative.single_step_x()
        single_step_y = relative.single_step_y()

        if start.can_npc_single_step(start + single_step_y + single_step_x, self.game.block_map):
            # If we can step diagonally, or the tile is horizontal, we will.
            return start + single_step_x + single_step_y

        # If we can't step to the tile directly, let's try to step in x alone.
        if start.can_npc_single_step(start + single_step_x, self.game.block_map):
            # Unlike with the diagonal case this taxicab can_npc_single_step will never recurse.
            return start + single_step_x

        # Then in y alone.
        if start.can_npc_single_step(start + single_step_y, self.game.block_map):
            # Unlike with the diagonal case this taxicab can_npc_single_step will never recurse.
            return start + single_step_y

        # We're stuck.
        return start

    def set_random_walk_destination(self) -> None:
        if self.no_random_walk_i > 0:
            return

        self.destination = self.location

        # Using self instead of Npc because maybe overridable.
        if not self.is_still_static or randrange(0, self.RANDOM_WALK_ROLL[1]) < self.RANDOM_WALK_ROLL[0]:
            self.destination = self.location + C(
                randint(-self.RANDOM_WALK_RADIUS, self.RANDOM_WALK_RADIUS),
                randint(-self.RANDOM_WALK_RADIUS, self.RANDOM_WALK_RADIUS))
            self.is_still_static = False
            self.no_random_walk_i = self.location.chebyshev_to(self.destination)
            if self.no_random_walk_i < 2:
                self.no_random_walk_i = 2  # For if we path right under ourselves / right beside ourselves.

    def switch_followee(self) -> bool:
        self.followee = Targeting.choice(self.choice_arg, self.location, Unit.ACTION_DISTANCE)
        if self.followee is not None:
            self.follow(self.followee)
            return True
        self.set_random_walk_destination()
        return False

    def follow(self, followee: Locatable) -> bool:
        assert self.can_see(followee) or self.followee == followee, \
            "Npcs can only follow targets they can see or are already following."

        self.is_still_static = True
        return super().follow(followee)

    def step(self) -> None:
        # We get a new tile using Npc.path (which gives only one tile) with no parents.
        self.pathing_queue.clear()  # Is this really necessary?
        self.pathing_queue.appendleft(self.path())

        if self.no_random_walk_i > 0:
            self.no_random_walk_i -= 1

        return super().step()

    def can_single_step(self, destination: C) -> bool:
        return self.location.can_npc_single_step(destination, self.game.block_map)

    def cant_single_step_callback(self, tile: C) -> None:
        # This method is called if the single step fails.
        # Tile argument is present even though it's never used because the calling function
        # provides it, and we need to receive it.
        return
