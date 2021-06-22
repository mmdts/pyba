from typing import List, Tuple, Union, Type, Dict

from terrain import Terrain, Inspectable, C
from npc import Npc
from runner import Runner
from healer import Healer
from combat_npc import Fighter, Ranger


class Penance:
    def __init__(self, wave_number, game: Inspectable):
        self.wave_number = wave_number
        self.game = game
        self.fighters: List[Fighter] = []
        self.rangers: List[Ranger] = []
        self.runners: List[Runner] = []
        self.healers: List[Healer] = []

        # A dictionary of lists with two items each, the first for spawns and the second for reserves.
        self.spawns: Dict[str, List[int]] = {
            "a": [*Fighter.SPAWNS[wave_number]],
            "s": [*Ranger.SPAWNS[wave_number]],
            "d": [*Runner.SPAWNS[wave_number]],
            "h": [*Healer.SPAWNS[wave_number]],
        }

        # Penance monsters are due to spawn at different times.
        # Runners spawn after first urgh tick interval.
        # Healers spawn on last poison tick (or one tick later if manually poisoned).
        self._due_to_spawn: Dict[str, bool] = {"a": False, "s": False, "d": False, "h": False}

        self.total_counts: Dict[str, int] = {}

        self.runner_movements: List[List[C]] = []

        # Before they initially spawn, the early spawners are also "reserves".
        # After this point, self.spawns[key][1] is to be treated as a decremental variable.
        # Meanwhile self.spawns[key][0] should be used for saturation comparison.
        for key in self.spawns:
            self.spawns[key][1] += self.spawns[key][0]
            self.total_counts[key] = self.spawns[key][1]

    def __getitem__(self, key: Union[Type, int, str]) -> List[Npc]:
        return self._get_list(key)

    def __iter__(self) -> Tuple[str, List[Npc]]:
        yield "a", self.fighters
        yield "s", self.rangers
        yield "d", self.runners
        yield "h", self.healers

    def __call__(self, tick: int) -> bool:
        # Handle penance tick actions by calling them.
        for key, species in self:
            for i, npc in enumerate(species):
                npc_still_spawned = npc()
                if not npc.is_alive() and npc.despawn_i == npc.DUE_TO_SPAWN_TICKS:
                    self.game.wave.penance.set_due_to_spawn(npc.__class__, True)
                if not npc_still_spawned:
                    # Handle penance death part 1.
                    species.pop(i)
                    if not isinstance(npc, Runner) or not npc.has_escaped:
                        self.game.wave.print(f"{npc.name} has been killed "
                                             f"({Terrain.tick_to_string(self.game.wave.relative_tick)}).")

                    # Spawn eggs
                    # TODO: BUILD Spawn eggs

                    # Handle penance extinction.
                    if len(species) == 0 and self.spawns[key][1] == 0:
                        # In the real game, this message, along with the check for it, is stalled.
                        # Here, we want accurate statistics regardless of stall, so this message is always instant.
                        self.game.wave.print(f"All penance {npc.default_name.lower()}s have been killed "
                                             f"({Terrain.tick_to_string(self.game.wave.relative_tick)}).")

                    # Handle penance death part 2.
                    del npc

        # Handle penance spawns every penance cycle (6s)
        # Spawning has to be handled after penance death, since a penance can die and another spawn in the same tick.
        if tick % self.game.wave.CYCLE == 0 and tick > 0:
            for key, species in self:
                # Spawning can be stalled, and is added through Game.stall.
                # If there are still reserves and the current penance are less than the maximum available at a time.
                if self.spawns[key][1] > 0 and self.can_spawn(key):
                    self.spawns[key][1] -= 1  # Decrease the reserve count.
                    self.game.stall(self.spawn, species, tick)  # Spawn a new penance.

        return self.count_alive() != 0 or self.count_reserves() != 0

    # Key is the one letter yield string that represents the penance species.
    def can_spawn(self, key: Union[Type, list, int, str]) -> bool:
        key = self._get_letter(key)
        if self.get_due_to_spawn(key):
            return True

        if len(self[key]) < self.spawns[key][0]:
            return True

        return False

    def spawn(self, key: Union[Type, list, int, str], tick: int = None) -> Npc:
        key = self._get_letter(key)
        new_species = self._get_type(key)(self.wave_number, self.game)
        self.set_due_to_spawn(key, False)
        self[key].append(new_species)
        self.game.wave.print(f"A new {new_species.default_name.lower()} has spawned "
                             f"({Terrain.tick_to_string(self.game.wave.relative_tick)}).")
        if tick is not None:
            new_species.name = f"{Terrain.tick_to_string(tick):0>3}" + " " + new_species.default_name

        if isinstance(new_species, Runner):
            # Runner forced movements can be set using the set_runner_movements function.
            if len(self.runner_movements) > 0:
                new_species.forced_movements = self.runner_movements.pop(0)

        return new_species

    def get_due_to_spawn(self, key: Union[Type, list, int, str]) -> bool:
        return self._due_to_spawn[self._get_letter(key)]

    def set_due_to_spawn(self, key: Union[Type, list, int, str], value: bool) -> None:
        self._due_to_spawn[self._get_letter(key)] = value

    def _get_type(self, key: Union[Type, list, int, str]) -> Type:
        if isinstance(key, str):
            key = key.lower()
        if key in [Fighter, self.fighters, "fighters", "fighter", "a", 0]:
            return Fighter
        if key in [Ranger, self.rangers, "rangers", "ranger", "s", 1]:
            return Ranger
        if key in [Runner, self.runners, "runners", "runner", "d", 2]:
            return Runner
        if key in [Healer, self.healers, "healers", "healer", "h", 3]:
            return Healer
        raise KeyError(f"Penance[{key}] does not exist.")

    def _get_letter(self, key: Union[Type, list, int, str]) -> str:
        if isinstance(key, str):
            key = key.lower()
        if key in [Fighter, self.fighters, "fighters", "fighter", "a", 0]:
            return "a"
        if key in [Ranger, self.rangers, "rangers", "ranger", "s", 1]:
            return "s"
        if key in [Runner, self.runners, "runners", "runner", "d", 2]:
            return "d"
        if key in [Healer, self.healers, "healers", "healer", "h", 3]:
            return "h"
        raise KeyError(f"Penance[{key}] does not exist.")

    def _get_list(self, key: Union[Type, list, int, str]) -> List[Npc]:
        if isinstance(key, str):
            key = key.lower()
        if key in [Fighter, self.fighters, "fighters", "fighter", "a", 0]:
            return self.fighters
        if key in [Ranger, self.rangers, "rangers", "ranger", "s", 1]:
            return self.rangers
        if key in [Runner, self.runners, "runners", "runner", "d", 2]:
            return self.runners
        if key in [Healer, self.healers, "healers", "healer", "h", 3]:
            return self.healers
        raise KeyError(f"Penance[{key}] does not exist.")

    def count_alive(self) -> int:
        rv = 0
        for k, species in self:
            rv += len(list(npc for npc in species))
        return rv

    def count_reserves(self) -> int:
        rv = 0
        for key in self.spawns:
            rv += self.spawns[key][1]
        return rv

    def set_runner_movements(self, movements: List[List[C]]) -> None:
        for i, runner in enumerate(movements):
            self.runner_movements.append([])
            for movement in runner:
                self.runner_movements[i].append(movement.copy())  # It changes, it needs to be a copy.
