from typing import List

from simulation.base.terrain import E, Inspectable, Locatable
from simulation.base.player import Player


class Collector(Player):
    INVENTORY_SPACE: int = 26  # Horn, bag.
    BAG_SPACE: int = 8

    RED, GREEN, BLUE = 0, 1, 2
    CALLS = ["red", "green", "blue"]

    def __init__(self, game: Inspectable):
        super().__init__(E.COLLECTOR_SPAWN, game)

    @staticmethod
    def access_letter() -> str:
        return "c"

    @property
    def choice_arg(self) -> List[Locatable]:
        rv = super().choice_arg
        rv.extend(self.game.wave.dropped_eggs)
        rv.extend(self.game.wave.game_objects.hoppers)
        return rv
