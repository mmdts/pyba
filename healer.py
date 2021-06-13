import math
from typing import List, Tuple, Union, Optional

from log import debug, J, LG
from player import Player
from runner import Runner
from terrain import E, Inspectable, Targeting, Action
from npc import Npc
from unit import Unit


# This is VERY SIMPLE CODE that reproduces the "0 hitsplat" and "poison syncing" effects. It has to do with
# the initial values of healer variables.
#
# I have 100% confidence this is the way healer code in-game is actually written. There's no way the developers
# wrote more complex code to intentionally reproduce such a side-effect result. I deduce they must have
# been lazy.
class Healer(Npc):
    HITPOINTS: List[int] = [27, 32, 37, 43, 49, 55, 60, 67, 76, 60]
    SPAWNS: List[Tuple[int, int]] = [(2, 0), (3, 0), (2, 1), (3, 1), (4, 1), (4, 2), (4, 3), (5, 2), (6, 2), (4, 3)]

    RUNNER_ACTION_DISTANCE: int = 5

    TARGET_STATE_COUNT: int = 2
    TARGETING_PLAYER: int = 0
    TARGETING_RUNNER: int = 1

    DUE_TO_SPAWN_TICKS: int = 2

    MAX_POISON_DAMAGE: int = 4
    POISON_TICKS_PER_HITSPLAT: int = 5
    MAX_POISON_I: int = POISON_TICKS_PER_HITSPLAT * MAX_POISON_DAMAGE + 1

    POISON_RANGE: int = 1

    def __init__(self, wave_number: int, game: Inspectable, name: str = None):
        super().__init__(wave_number, E.PENANCE_HEALER_SPAWN, game, name)
        self.target_state: int = Healer.TARGETING_PLAYER  # It swaps on call of Healer.switch_target.

        self.followee: Optional[Union[Player, Runner]] = None
        self.poison_i = 1
        self.poison_start_tick = 0

    def str_info(self) -> str:
        letter = self.target_state == Healer.TARGETING_RUNNER and 'R' or 'P'
        if isinstance(self.followee, Runner):
            letter = "r"

        if isinstance(self.followee, Player):
            letter = self.followee.access_letter()

        return f"{LG}{self.name:<11}({self.game.tick:0>3}, {self.cycle}, {letter})" \
               f"@{self.location} -> HP: {self.hitpoints}{J}"

    def do_cycle(self):
        if (self.game.wave.relative_tick - self.poison_start_tick) % 5 == 0 and self.is_poisoned():
            self.poison_i -= 1
            self.hitpoints -= self.poison_damage

        # START: THIS PART IS NOT TICK PERFECT.
        # Keep following -> reaching forever.
        if self.followee is None:
            # It gets cleared by switch_followee_state_and_heal_if_runner,
            # which happens as the on_reach of Healer.switch_target
            self.switch_followee()
        # END

        self.unit_call()

    def switch_followee(self, on_reach: Action = None) -> bool:
        # On action is completely ignored here, as it is decided within the function to be
        # self.switch_target_state_and_heal_if_runner
        self.followee = Targeting.choice(
            self.choice_arg,
            self.location,
            self.target_state == Healer.TARGETING_RUNNER and Healer.RUNNER_ACTION_DISTANCE or Unit.ACTION_DISTANCE
        )
        if self.followee is not None:
            debug("Healer.switch_followee", f"{self} decided to follow {self.followee}.")
            self.follow(self.followee, (self.switch_followee_state_and_heal_if_runner, (self.followee,), {}))
            return True
        if self.target_state == Healer.TARGETING_RUNNER:  # Healers do not random walk when targeting players.
            self.set_random_walk_destination()
            return False

    def switch_followee_state_and_heal_if_runner(self, followee):
        # To be used as the on_reach function.
        # The argument "followee" gets special handling in Healer.switch_followee, and does not need to be provided in
        # the Action's middle Tuple.
        self.target_state = (self.target_state + 1) % Healer.TARGET_STATE_COUNT
        debug("Healer.on_reach", f"{self} reached {followee} "
                                 f"and switched target state to {self.target_state}.")
        if isinstance(followee, Runner):
            followee.hitpoints = Runner.HITPOINTS[self.wave_number]

        self.stop_movement(clear_follow=True)

    @property
    def choice_arg(self):
        return self.target_state == Healer.TARGETING_PLAYER and \
               self.game.players.get_iterable() or self.game.wave.penance.runners

    def apply_poison(self):
        # Player Healer calls this function.
        if not self.is_poisoned():
            self.poison_start_tick = self.game.wave.relative_tick

        # We reset the poison damage if it's already poisoned.
        self.poison_i = Healer.MAX_POISON_I

        # The forced poison damage.
        self.hitpoints -= Healer.MAX_POISON_DAMAGE

    def is_poisoned(self) -> bool:
        return self.poison_i > 0

    @property
    def poison_damage(self) -> int:
        return math.ceil(self.poison_i / Healer.POISON_TICKS_PER_HITSPLAT)
