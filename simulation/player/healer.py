from typing import List, Optional

from log import debug
from simulation.base.dispenser import Dispenser
from simulation.base.terrain import E, Inspectable, Y, Locatable
from simulation.base.player import Player
from simulation.base.unit import Unit
from simulation import penance


class Healer(Player):
    INVENTORY_SPACE: int = 26  # Horn, vial.
    FOOD_PER_OVERSTOCK: int = 5

    TOFU, WORMS, MEAT = 0, 1, 2
    CALLS = ["tofu", "worms", "meat"]

    POISON_BUSY_WAIT: int = 1

    def __init__(self, game: Inspectable):
        super().__init__(E.HEALER_SPAWN, game)
        self.actions.extend([
            (penance.Healer, self.use_poison_food, Unit.POST),
        ])

        # This array persists healers even after they die.
        self.healers: List[penance.Healer] = []

    @staticmethod
    def access_letter() -> str:
        return "h"

    @property
    def choice_arg(self) -> List[Locatable]:
        rv = super().choice_arg
        rv.extend(self.game.wave.penance.healers)
        return rv

    def use_dispenser(self, option: Optional[int] = None) -> None:
        self._use_dispenser(option)

        alternator_i = 0
        alternator = [Y.POISON_TOFU, Y.POISON_WORMS, Y.POISON_MEAT]

        if option is not None and option != Dispenser.DEFAULT_STOCK and option in alternator:
            overstock_i = 0
            for key, slot in enumerate(self.inventory):
                if slot == Y.EMPTY:
                    self.inventory[key] = alternator[option]
                    overstock_i += 1
                    if overstock_i == Healer.FOOD_PER_OVERSTOCK:
                        break
        else:
            for key, slot in enumerate(self.inventory):
                if slot == Y.EMPTY:
                    if Y.VIAL not in self.inventory:
                        self.inventory[key] = Y.VIAL
                        continue
                    self.inventory[key] = alternator[alternator_i]
                    alternator_i = (alternator_i + 1) % len(alternator)

        self.busy_i = Player.DISPENSER_BUSY_WAIT

    def pick_item(self) -> None:
        raise AssertionError("Healers cannot pick items.")

    def use_poison_food(self, which: int) -> None:
        assert isinstance(self.followee, penance.Healer), "Cannot poison something that isn't a healer."
        assert self.followee.is_alive(), "Cannot poison a dead healer."

        assert str(which) in self.inventory, "We cannot use poison food we do not have."
        assert which < self.CALL_COUNT, "We cannot use things that aren't poison food."
        if which == self.correct_call:
            debug("Healer.use_poison_food", f"{self} successfully poisoned {self.followee}.")
            self.followee.apply_poison()
        else:
            self.print("Incorrect poison food.")
        self.inventory[self.inventory.index(str(which))] = Y.EMPTY
        self.busy_i = Healer.POISON_BUSY_WAIT

    def click_use_poison_food(self, which: int, healer: penance.Healer) -> bool:
        if not self.location.renders_unit(healer):
            return False
        self.action_args = (which,)
        self.follow(healer)
        self.move(self.destination)
        return True
