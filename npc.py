from abc import abstractmethod
from random import random
from typing import List, Callable, Tuple, Dict

from log import game_print
from terrain import Locatable, Terrain, C, Inspectable, E, D
from unit import Unit


class Npc(Unit):
    HITPOINTS: List[int] = None

    DESPAWN_TICKS: int = 2
    DUE_TO_SPAWN_TICKS: int  # 2 for Healer, 1 for Runner, 0 for CombatNpc.

    CYCLE_COUNT: int = 10  # Penance do actions in cycles of CYCLE_COUNT ticks.

    DEAD, ALIVE = 0, 1  # They're binary, but we're leaving them as int for legacy.

    """Basic Functions"""

    def __init__(self, wave_number: int, location: C, game: Inspectable, name: str = None):
        super().__init__(location, game)
        self.name: str = name
        if self.name is None:
            self.name = self.default_name

        self.cycle: int = 0
        self.despawn_i: int = self.DESPAWN_TICKS
        self.state: int = self.ALIVE
        self.wave_number: int = wave_number
        self.hitpoints: int = self.HITPOINTS[self.wave_number]

    def __call__(self):
        self.cycle += 1
        self.cycle %= self.CYCLE_COUNT

        if self.hitpoints == 0:  # TODO: BUILD Care for blue eggs here - in the far future.
            self.state = self.DEAD

        if self.is_alive():
            if self.followee is not None:
                self.follow(self.followee)  # Re-follow a target that might move.
            self.do_cycle()  # Can return False only in runners.
            self.step()
            return True

        if self.tick_despawn():
            return False  # Our return False (the condition for Npc removal in Penance.__call__).

        return True

    @property
    def default_name(self) -> str:
        return self.__class__.__name__

    def print(self, *args, **kwargs):
        game_print("Penance.print", f"[{self.name.ljust(11)}]{str(self.location)}"
                   f"({Terrain.tick_to_string(self.game.wave.relative_tick)})::", *args, **kwargs)
        self.game.text_payload.append(
            " ".join([str(arg) for arg in (
                "PENANCE::", f"[{self.name.ljust(11)}]{str(self.location)}"
                             f"({Terrain.tick_to_string(self.game.wave.relative_tick)})::", *args
            )])
        )

    def switch_target(self, targets: List[Locatable], on_reach: Tuple[Callable, Tuple, Dict] = None):
        filtered_targets = [target for target in targets
                            if self.location.chebyshev_to(target.location) <= E.UNIT_RENDER_DISTANCE]

        idx = int(random() * len(filtered_targets))

        target = filtered_targets[idx]
        self.follow(target, on_reach)

    """Tick Functions"""

    @abstractmethod
    def do_cycle(self) -> bool:
        # All Npcs call do_cycle during their usual call procedure if they're alive.
        # All Npcs return what do_cycle returns, but since no action despawns non-runner Npcs other than dying and
        # despawning naturally, only runners should ever return False in their do_cycle (as part of the escape
        # procedure).

        # Non-runner Npcs should attempt to all return super().__call__(tick) as part of their usual do_cycle procedure.
        # raise NotImplementedError(f"{self.__class__.__name__} needs to implement Npc.do_cycle.")
        return True  # TODO: Return this to raise after implementing.

    def tick_despawn(self) -> bool:
        # Reduces despawn countdown and returns true if it hits zero.
        # To be used inside if conditions.
        self.despawn_i -= 1
        return self.despawn_i == 0

    """Boolean Functions"""

    def is_alive(self) -> bool:
        return self.state == self.ALIVE

    def is_followable(self) -> bool:
        return self.is_alive() and super().is_followable()

    """Movement Functions"""

    def path(self, destination: C = None, start: C = None) -> C:
        # Dumb pathfinding (referred to as Npc.path) tries to only calculate and add one tile per call.
        #
        # A move that relies on Npc.path will only ever move one tile. Maker of the move function is responsible
        # for the repetitive per-tick calling of this function that is going to make the Npc move seamlessly.
        #
        # TODO: CHECK https://discord.com/channels/@me/821965940362969129/822317123782836245
        if start is None:
            start = self.location.copy()

        if destination is None:
            destination = self.target.copy()

        relative = destination - start

        # Always try stepping in x, then always try stepping in y.
        # Legacy note: Diagonal checks are very processor intensive.
        #
        # Keep in mind we can only do this because Npcs won't try to run up cannon, and therefore,
        # the wall processing part (which is why recursion was introduced into diagonal can_single_step)
        # won't be necessary
        new_tile = start
        single_step_x = relative.single_step_x()
        single_step_y = relative.single_step_y()

        if start.can_npc_single_step(start + single_step_x):
            # Unlike with the diagonal case this taxicab can_npc_single_step will never recurse.
            new_tile += single_step_x

        if start.can_npc_single_step(start + single_step_y):
            # Unlike with the diagonal case this taxicab can_npc_single_step will never recurse.
            new_tile += single_step_y

        return new_tile

    def follow(self, target: Locatable, on_reach: Tuple[Callable, Tuple, Dict] = None) -> bool:
        assert self.can_see(target) or self.followee == target, \
            "Npcs can only follow targets they can see or are already following."

        return super().follow(target, on_reach)

    """Stepping Functions"""

    def step(self) -> None:
        # We get a new tile using Npc.path (which gives only one tile) with no parents.
        self.pathing_queue.clear()  # Is this really necessary?
        self.pathing_queue.appendleft(self.path())

        return super().step()

    def can_single_step(self, destination: C) -> bool:
        return self.location.can_npc_single_step(destination)

    # TODO: BUILD Implement random walk.
