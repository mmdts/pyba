import math
from typing import List, Tuple, Union, Optional

from log import debug, J, LG
from player import Player
from runner import Runner
from terrain import E, Inspectable, Targeting
from npc import Npc
from unit import Unit, POST


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
    NO_FOLLOW_DELAYS: Tuple[int] = (2, 4)  # 2 between runner and player, 4 between player and runner.

    DUE_TO_SPAWN_TICKS: int = 2

    MAX_POISON_DAMAGE: int = 4
    POISON_TICKS_PER_HITSPLAT: int = 5
    MAX_POISON_I: int = POISON_TICKS_PER_HITSPLAT * MAX_POISON_DAMAGE + 1

    POISON_RANGE: int = 1

    def __init__(self, game: Inspectable):
        super().__init__(E.PENANCE_HEALER_SPAWN, game)
        self.target_state: int = Healer.TARGETING_PLAYER  # It swaps on call of Healer.switch_target.

        self.in_initial_state: bool = True
        self.followee: Optional[Union[Player, Runner]] = None
        self.poison_i = 1
        self.poison_start_tick = 0
        self.no_follow_i: int = 0
        self.actions.extend([
            (Player, self.switch_followee_state, POST),
            (Runner, self.switch_followee_state, POST),
        ])

        if "h" in self.game.ai and self.game.ai["h"] is not None:
            self.game.ai["h"].healers.append(self)

    def str_info(self) -> str:
        letter = self.target_state == Healer.TARGETING_RUNNER and 'R' or 'P'
        if isinstance(self.followee, Runner):
            letter = "r"

        if isinstance(self.followee, Player):
            letter = self.followee.access_letter()

        return f"{LG}{self.name:<11}({self.game.tick:0>3}, {self.cycle}, {letter})" \
               f"@{self.location} -> HP: {self.hitpoints}{J}"

    def do_cycle(self) -> None:
        if (self.game.wave.relative_tick - self.poison_start_tick) % 5 == 0 and self.is_poisoned():
            self.poison_i -= 1
            debug("Healer.do_cycle.poison", f"{self} ticking {self.poison_damage} poison damage to reach "
                                            f"{self.hitpoints - self.poison_damage} HP.")
            self.hitpoints -= self.poison_damage

        # This entire condition is debug.
        if self.followee is None:
            debug("Healer.do_cycle.followee",
                  f"{self} checking condition with "
                  f"self.is_still_static = {self.is_still_static} and self.destination = {self.destination} and "
                  f"self.no_follow_i = {self.no_follow_i} and self.no_random_walk_i = {self.no_random_walk_i}.")

        # START: THIS PART IS ALMOST TICK PERFECT.
        # Keep following -> reaching forever.

        # We first check that we aren't following anything. We don't take any action if we are.
        # self.followee gets cleared by switch_followee_state_and_heal_if_runner,
        # which happens as the on_reach of Healer.switch_target
        #
        # We then check that we're allowed to follow through the self.no_follow_i condition.
        # If we aren't allowed to follow, then we try to random walk.
        #
        # We finally use the lazy "or" to follow if we found something to follow.
        # If we either aren't allowed to follow or haven't found something to follow when we tried to,
        # we try to random walk.
        # If we're not following anything and,
        # either we're not allowed to follow or we can't find anything to follow.
        if self.followee is None and \
                (self.no_follow_i != 0 or not self.switch_followee()) and \
                not self.in_initial_state:
            debug("Healer.do_cycle.random", f"{self} will attempt to random walk because condition is true.")
            self.set_random_walk_destination()
            if self.no_follow_i > 0:
                self.no_follow_i -= 1
        # END

        self.step()
        self.act()
        debug("Healer.do_cycle", f"{self}")

    def switch_followee(self) -> bool:
        # On action is completely ignored here, as it is decided within the function to be
        # self.switch_target_state_and_heal_if_runner
        self.followee = Targeting.choice(
            self.choice_arg,
            self.location,
            self.target_state == Healer.TARGETING_RUNNER and Healer.RUNNER_ACTION_DISTANCE or Unit.ACTION_DISTANCE
        )
        if self.followee is not None:
            debug("Healer.switch_followee", f"{self} decided to follow {self.followee}.")
            self.follow(self.followee)
            self.in_initial_state = False
            return True

        return False

    def switch_followee_state(self) -> None:
        # To be used as the on_reach function.
        # The argument "followee" gets special handling in Healer.switch_followee, and does not need to be provided in
        # the Action's middle Tuple.
        self.target_state = (self.target_state + 1) % Healer.TARGET_STATE_COUNT
        debug("Healer.on_reach", f"{self} reached {self.followee} "
                                 f"and switched target state to {self.target_state}.")
        if isinstance(self.followee, Runner):
            self.followee.hitpoints = Runner.HITPOINTS[self.game.wave.number]

        self.stop_movement(clear_follow=True)
        self.no_follow_i = Healer.NO_FOLLOW_DELAYS[self.target_state]

    @property
    def choice_arg(self) -> Union[List[Player], List[Runner]]:
        return self.target_state == Healer.TARGETING_PLAYER and \
               self.game.players.get_iterable() or self.game.wave.penance.runners

    def apply_poison(self) -> None:
        # Player Healer calls this function.
        if not self.is_poisoned():
            self.poison_start_tick = self.game.wave.relative_tick

        # We reset the poison damage if it's already poisoned.
        self.poison_i = Healer.MAX_POISON_I

        debug("Healer.apply_poison", f"{self} got manually poisoned to reach "
                                     f"{self.hitpoints - Healer.MAX_POISON_DAMAGE} HP.")
        # The forced poison damage.
        self.hitpoints -= Healer.MAX_POISON_DAMAGE

    def is_poisoned(self) -> bool:
        return self.poison_i > 0

    @property
    def poison_damage(self) -> int:
        return math.ceil(self.poison_i / Healer.POISON_TICKS_PER_HITSPLAT)
