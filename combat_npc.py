from typing import List, Tuple, Optional

from log import LM, J
from player import Player
from terrain import C, E, Inspectable
from npc import Npc
from unit import PRE


class CombatNpc(Npc):
    DEFENCE: List[int] = None

    DUE_TO_SPAWN_TICKS: int = 0
    ATTACK_RANGE: int = 1

    def __init__(self, location: C, game: Inspectable):
        super().__init__(location, game)
        if self.DEFENCE is None:
            raise NotImplementedError("self.DEFENCE")
        self.defence: int = self.DEFENCE[self.game.wave.number]
        self.followee: Optional[Player] = None  # Followee is already defined, but we're overriding the type check.
        self.tagger: Optional[Player] = None  # Attacker sets himself as tagger if attacking in the first cycle.
        self.actions.extend([
            (Player, self.do_nothing, PRE),
        ])

    def str_info(self) -> str:
        letter = "_"

        if isinstance(self.followee, Player):
            letter = self.followee.access_letter()

        return f"{LM}{self.name:<11}({self.game.tick:0>3}, {self.cycle}, {letter})" \
               f"@{self.location} -> HP: {self.hitpoints}{J}"

    # Damage is taken in the player attack call.
    def do_cycle(self) -> None:
        tick = self.game.wave.relative_tick

        # Retaliate (change followee and follow) if not "reached" player and got attacked.
        if self.followee is None:
            if self.tagger is not None:
                self.follow(self.tagger)
                self.tagger = None
            else:
                self.set_random_walk_destination()
                self.no_random_walk_i = 10  # Special value to prevent it from random walking again.

        if tick % Inspectable.CYCLE == 0:
            self.switch_followee()

        if self.can_act_on(self.followee, self.ATTACK_RANGE):
            self.stop_movement(clear_destination=True)  # Npc reached and is now attacking.

        self.step()
        self.act()

    @property
    def choice_arg(self) -> List[Player]:
        return self.game.players.get_iterable()

    def do_nothing(self):
        return


class Fighter(CombatNpc):
    HITPOINTS: List[int] = [28, 29, 32, 37, 38, 49, 50, 55, 56, 50]
    SPAWNS: List[Tuple[int, int]] = [(2, 2), (2, 3), (5, 0), (5, 1), (3, 3), (5, 1), (5, 2), (7, 0), (6, 2), (5, 2)]
    DEFENCE: List[int] = [25, 27, 34, 37, 44, 48, 52, 62, 66, 52]

    ATTACK_RANGE: int = 1

    def __init__(self, game: Inspectable):
        super().__init__(E.FIGHTER_SPAWN, game)


class Ranger(CombatNpc):
    HITPOINTS: List[int] = [20, 28, 29, 34, 41, 50, 50, 54, 58, 50]
    SPAWNS: List[Tuple[int, int]] = [(2, 2), (3, 1), (3, 3), (3, 3), (5, 1), (5, 2), (6, 1), (5, 3), (7, 1), (6, 1)]
    DEFENCE: List[int] = [21, 29, 33, 42, 46, 54, 61, 68, 80, 61]

    ATTACK_RANGE: int = 6

    def __init__(self, game: Inspectable):
        super().__init__(E.RANGER_SPAWN, game)
