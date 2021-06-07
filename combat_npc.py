from typing import List, Tuple

from terrain import C, E, Inspectable
from npc import Npc


class CombatNpc(Npc):
    DEFENCE: List[int] = None

    def __init__(self, wave_number: int, location: C, game: Inspectable, name: str = None):
        super().__init__(wave_number, location, game, name)
        if self.DEFENCE is None:
            raise NotImplementedError("self.DEFENCE")
        self.defence: int = self.DEFENCE[wave_number]


class Fighter(CombatNpc):
    HITPOINTS: List[int] = [28, 29, 32, 37, 38, 49, 50, 55, 56, 50]
    SPAWNS: List[Tuple[int, int]] = [(2, 2), (2, 3), (5, 0), (5, 1), (3, 3), (5, 1), (5, 2), (7, 0), (6, 2), (5, 2)]
    DEFENCE: List[int] = [25, 27, 34, 37, 44, 48, 52, 62, 66, 52]

    def __init__(self, wave_number: int, game: Inspectable):
        super().__init__(wave_number, E.FIGHTER_SPAWN, game)


class Ranger(CombatNpc):
    HITPOINTS: List[int] = [20, 28, 29, 34, 41, 50, 50, 54, 58, 50]
    SPAWNS: List[Tuple[int, int]] = [(2, 2), (3, 1), (3, 3), (3, 3), (5, 1), (5, 2), (6, 1), (5, 3), (7, 1), (6, 1)]
    DEFENCE: List[int] = [21, 29, 33, 42, 46, 54, 61, 68, 80, 61]

    def __init__(self, wave_number: int, game: Inspectable):
        super().__init__(wave_number, E.RANGER_SPAWN, game)
