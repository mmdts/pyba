from typing import List, Tuple, Union, Optional

from player import Player
from runner import Runner
from terrain import E, Inspectable
from npc import Npc

class Healer(Npc):
    HITPOINTS: List[int] = [27, 32, 37, 43, 49, 55, 60, 67, 76, 60]
    SPAWNS: List[Tuple[int, int]] = [(2, 0), (3, 0), (2, 1), (3, 1), (4, 1), (4, 2), (4, 3), (5, 2), (6, 2), (4, 3)]

    TARGET_STATE_COUNT: int = 2
    TARGETING_PLAYER: int = 0
    TARGETING_RUNNER: int = 1

    DUE_TO_SPAWN_TICKS: int = 2

    def __init__(self, wave_number: int, game: Inspectable, name: str = None):
        super().__init__(wave_number, E.PENANCE_HEALER_SPAWN, game, name)
        self.target_state: int = Healer.TARGETING_PLAYER

        self.followee: Optional[Union[Player, Runner]] = None
        self.poison_i: int = 0
        self.poison_start_tick: int = 0
        self.poison_start_tick_synced: bool = True

    def str_info(self):
        return f"{self.name}({self.game.tick}, {self.cycle}, {self.target_state})" \
               f"@{str(self.location)} -> HP: {self.hitpoints}"

    # """Tick Functions"""
    # def do_cycle(self):
    #     if self.game.wave.relative_tick % 5 == 0:
    #         pass  # Poison
    #     if self.game.wave.relative_tick % Wave.CYCLE == 0:
    #         self.poison_start_tick_synced = False
    #
    #
    #     self.unit_call()
    #
    # def apply_poison(self):
    #     if self.poison_start_tick_synced:
    #         self.poison_start_tick =