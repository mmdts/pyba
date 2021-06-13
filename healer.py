from typing import List, Tuple, Union, Optional

from log import debug, J, LG
from player import Player
from runner import Runner
from terrain import E, Inspectable, Targeting, Action
from npc import Npc
from unit import Unit


class Healer(Npc):
    HITPOINTS: List[int] = [27, 32, 37, 43, 49, 55, 60, 67, 76, 60]
    SPAWNS: List[Tuple[int, int]] = [(2, 0), (3, 0), (2, 1), (3, 1), (4, 1), (4, 2), (4, 3), (5, 2), (6, 2), (4, 3)]

    RUNNER_ACTION_DISTANCE: int = 5

    TARGET_STATE_COUNT: int = 2
    TARGETING_PLAYER: int = 0
    TARGETING_RUNNER: int = 1

    DUE_TO_SPAWN_TICKS: int = 2

    MAX_POISON: int = 4

    def __init__(self, wave_number: int, game: Inspectable, name: str = None):
        super().__init__(wave_number, E.PENANCE_HEALER_SPAWN, game, name)
        self.target_state: int = Healer.TARGETING_PLAYER  # It swaps on call of Healer.switch_target.

        self.followee: Optional[Union[Player, Runner]] = None
        self.poison_i: int = -1  # When poisoned, the 4s are 0, 1, 2, 3, 4, and then 3s...
        self.poison_start_tick: int = -1
        self.poison_start_tick_synced: bool = True  # When poisoned late, the poison ticks aren't synced.

    def str_info(self) -> str:
        letter = self.target_state == Healer.TARGETING_RUNNER and 'R' or 'P'
        if isinstance(self.followee, Runner):
            letter = "r"

        if isinstance(self.followee, Player):
            letter = self.followee.access_letter()

        return f"{LG}{self.name:<11}({self.game.tick:0>3}, {self.cycle}, {letter})" \
               f"@{str(self.location)} -> HP: {self.hitpoints}{J}"

    def do_cycle(self):
        tick = self.game.wave.relative_tick
        if self.poison_damage == 0:
            self.poison_start_tick = -1

        if (tick - self.poison_start_tick) % 5 == 0:
            self.tick_poison(tick)
        if tick > 0 and tick % self.game.wave.CYCLE == 0:  # Using Wave.CYCLE causes cyclic dependencies.
            self.poison_start_tick_synced = False

        # START: THIS PART IS NOT TICK PERFECT.
        # Keep targeting -> reaching forever.
        if self.followee is None:
            # It gets cleared by switch_target_state_and_heal_if_runner,
            # which happens as the on_reach of Healer.switch_target
            self.switch_target()
        # END

        self.unit_call()

    def single_step(self) -> bool:
        # TODO: REMOVE this. The whole overload is here for debug.
        if len(self.pathing_queue) > 0 and self.pathing_queue[0] != self.location:
            debug("Healer.single_step", f"{str(self)} decided to single step with target {str(self.target)}.")
        return super().single_step()

    def switch_target(self, on_reach: Action = None) -> bool:
        # On action is completely ignored here, as it is decided within the function to be
        # self.switch_target_state_and_heal_if_runner
        self.followee = Targeting.choice(
            self.choice_arg,
            self.location,
            self.target_state == Healer.TARGETING_RUNNER and Healer.RUNNER_ACTION_DISTANCE or Unit.ACTION_DISTANCE
        )
        if self.followee is not None:
            debug("Healer.switch_target", f"{str(self)} decided to follow {str(self.followee)}.")
            self.follow(self.followee, (self.switch_target_state_and_heal_if_runner, (self.followee,), {}))
            return True
        if self.target_state == Healer.TARGETING_RUNNER:  # Healers do not random walk when targeting players.
            self.set_random_walk_target()
            return False

    def switch_target_state_and_heal_if_runner(self, followee):
        # To be used as the on_reach function.
        # The argument "followee" gets special handling in Npc.switch_target, and does not need to be provided in
        # the Action's middle Tuple.
        self.target_state = (self.target_state + 1) % Healer.TARGET_STATE_COUNT
        debug("Healer.on_reach", f"{str(self)} reached {str(followee)} "
                                 f"and switched target state to {self.target_state}.")
        if isinstance(followee, Runner):
            followee.hitpoints = Runner.HITPOINTS[self.wave_number]

        self.stop_movement(clear_follow=True)

    @property
    def choice_arg(self):
        return self.target_state == Healer.TARGETING_PLAYER and \
               self.game.players.get_iterable() or self.game.wave.penance.runners

    def apply_poison(self, tick):
        # We only check for synced / unsynced poison on an unpoisoned healer.
        if not self.is_poisoned():
            if self.poison_start_tick_synced:
                # Setting self.poison_start_tick is the condition for self.is_poisoned to start returning true,
                # and therefore for self.tick_poison to deal damage.
                self.poison_start_tick = ((tick // 5) + 1) * 5
            else:
                self.poison_start_tick = tick + 5

        # We reset the poison damage if it's already poisoned.
        self.poison_i = -1

        # The forced poison damage.
        self.hitpoints -= Healer.MAX_POISON

    def tick_poison(self, tick):
        if self.is_poisoned():
            self.poison_i += 1  # This has to be before self.poison_damage to make sure self.poison_i is >= 0.
            self.hitpoints -= self.poison_damage

    def is_poisoned(self) -> bool:
        return self.poison_start_tick > -1

    def heal(self, runner: Runner) -> None:
        runner.hitpoints = Runner.HITPOINTS[self.wave_number]

    @property
    def poison_damage(self) -> int:
        if self.poison_i == -1:
            return 0
        return Healer.MAX_POISON - (self.poison_i // 5)