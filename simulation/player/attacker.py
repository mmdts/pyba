from typing import List, Tuple, Optional

from log import M, J
from simulation.base.terrain import C, E, Inspectable, Action, Locatable
from simulation.base.player import Player

# Gear bonuses are on the form of (accuracy, damage, set bonus, attack speed, range)
Stats = Tuple[int, int, int, int]


class Attacker(Player):
    INVENTORY_SPACE: int = 0  # Accounting for that the assumed attacker cannot carry items.

    CALL_COUNT: int = 4

    MAX_SPEC: int = 100
    SPEC_RESTORE_AMOUNT: int = 10
    SPEC_RESTORE_TIME: int = 50

    # TODO: Attacker.click_change_weapon should account for changing combat gear from ranged to melee,
    #       and should provide that as a function argument, for example, gear_bonus: Tuple[int, int, int] = (37, 5, 0)
    #       for +37 accuracy, +5 damage, and 0% set bonus.
    MSB: Stats = (0, 0, 10, 3, 6)  # TODO: CHECK and get stats.
    TAB: Stats = (0, 0, 10, 3, 7)
    COMPB: Stats = ()
    DBOW: Stats = ()
    DCLAWS: Stats = ()
    CHALLY: Stats = ()
    BULWARK: Stats = ()
    DHALLY: Stats = ()

    # Arrows are referred to as "controlled arrows", etc. since naming makes no difference in code.
    # For reference, their order is:
    # * Wind / Water / Earth / Fire
    # * White / Blue / Green / Red
    # * Bullet / Field / Blunt / Barbed
    CONTROLLED, ACCURATE, AGGRESSIVE, DEFENSIVE = 0, 1, 2, 3
    CALLS = ["controlled", "accurate", "aggressive", "defensive"]

    def __init__(self, location: C, game: Inspectable):
        super().__init__(location, game)
        self.spec_restore_i: int = 0
        self.spec: int = Attacker.MAX_SPEC

        self.gear_bonus: Stats = Attacker.MSB
        self.actions.extend([
            # Attack CombatNpc POST
        ])

    def __call__(self) -> bool:
        # Increase the special attack bar.
        if self.spec < 90:
            self.spec_restore_i += 1

        if self.spec < 100 and self.spec_restore_i > Attacker.SPEC_RESTORE_TIME:
            self.spec_restore_i = 0
            self.spec = min(Attacker.MAX_SPEC, self.spec + Attacker.SPEC_RESTORE_AMOUNT)

        # TODO: BUILD Do the rest of attacker processing.
        # TODO: BUILD Attack with a ranged/melee weapon
        # TODO: BUILD Handle attack delay (Attacker)

        # Do the rest of player processing.
        return super().__call__()

    @staticmethod
    def access_letter() -> str:
        return "a"

    @property
    def choice_arg(self) -> List[Locatable]:
        rv = super().choice_arg
        rv.extend(self.game.wave.penance.fighters)
        rv.extend(self.game.wave.penance.rangers)
        return rv

    def use_dispenser(self, option: Optional[int] = None) -> None:
        pass  # TODO: Implement attacker dispenser.

    def pick_item(self) -> None:
        raise AssertionError("Attackers cannot pick items.")


class MainAttacker(Attacker):
    def __init__(self, game: Inspectable):
        super().__init__(E.MAIN_ATTACKER_SPAWN, game)
        self.is_stalling: bool = False  # Extending, duping, or forcing.
        self.stall_queue: List[Action] = []  # A callable, its args, and its kwargs.

    def __call__(self) -> bool:
        # If the player stops stalling, we empty the queue.  # TODO: BUILD all actions that stop stalling to do so.
        if not self.is_stalling:
            r = len(self.stall_queue)
            for i in range(r):
                action, args, kwargs = self.stall_queue.pop(0)
                action(*args, **kwargs)

        return super().__call__()

    def str_info(self) -> str:
        return f"{M}{'MAttacker':<11}({self.game.tick:0>3}, _, _)@{self.location}{J}"


class SecondAttacker(Attacker):
    def __init__(self, game: Inspectable):
        super().__init__(E.SECOND_ATTACKER_SPAWN, game)

    def str_info(self) -> str:
        return f"{M}{'SAttacker':<11}({self.game.tick:0>3}, _, _)@{self.location}{J}"
