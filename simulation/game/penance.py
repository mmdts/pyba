from typing import List, Tuple, Union, Type, Dict

from simulation.base.terrain import Terrain, Inspectable, C
from simulation.base.npc import Npc
from simulation import penance


class Penance:
    def __init__(self, game: Inspectable):
        self.game = game
        self.fighters: List[penance.Fighter] = []
        self.rangers: List[penance.Ranger] = []
        self.runners: List[penance.Runner] = []
        self.healers: List[penance.Healer] = []

        # A dictionary of lists with two items each, the first for spawns and the second for reserves.
        self.spawns: Dict[str, List[int]] = {
            "a": [*penance.Fighter.SPAWNS[self.game.wave.number]],
            "s": [*penance.Ranger.SPAWNS[self.game.wave.number]],
            "d": [*penance.Runner.SPAWNS[self.game.wave.number]],
            "h": [*penance.Healer.SPAWNS[self.game.wave.number]],
        }

        # Penance monsters are due to spawn at different times.
        # Runners spawn after first urgh tick interval.
        # Healers spawn on last poison tick (or one tick later if manually poisoned).
        self._due_to_spawn: Dict[str, bool] = {"a": False, "s": False, "d": False, "h": False}

        self.total_counts: Dict[str, int] = {}

        # The following 4 counters are for deep learning reward purposes.
        self.species_extinct = 0
        self.runner_escapes = 0
        self.runner_random_moves = 0
        self.healer_static_ticks = 0

        self.runner_movements: List[List[C]] = []

        # Before they initially spawn, the early spawners are also "reserves".
        # After this point, self.spawns[key][1] is to be treated as a decremental variable.
        # Meanwhile self.spawns[key][0] should be used for saturation comparison.
        for key in self.spawns:
            self.spawns[key][1] += self.spawns[key][0]
            self.total_counts[key] = self.spawns[key][1]

    def __getitem__(self, key: Union[Type[Npc], int, str]) -> List[Npc]:
        return self._get_list(key)

    def __iter__(self) -> Tuple[str, List[Npc]]:
        yield "a", self.fighters
        yield "s", self.rangers
        yield "d", self.runners
        yield "h", self.healers

    def __call__(self) -> bool:
        # Handle penance tick actions by calling them.
        for key, species in self:
            for i, npc in enumerate(species):
                npc_still_spawned = npc()
                if not npc.is_alive() and npc.despawn_i < npc.DUE_TO_SPAWN_TICKS:
                    self.game.wave.penance.set_due_to_spawn(npc.__class__, True)
                    # Handle penance extinction.
                    none_alive = [n.is_alive() for n in species].count(True) == 0
                    if none_alive and self.spawns[key][1] == 0:
                        # In the real game, this message, along with the check for it, is stalled.
                        # Here, we want accurate statistics regardless of stall, so this message is always instant.
                        self.game.wave.print(f"All penance {npc.default_name.lower()}s have been killed "
                                             f"({Terrain.tick_to_string(self.game.wave.relative_tick)}).")
                        self.species_extinct += 1
                        species.pop()  # Destroy the species completely.

                if not npc_still_spawned:
                    # Handle penance death.
                    if len(species) > 0:
                        species.pop(i)
                    if not isinstance(npc, penance.Runner) or not npc.has_escaped:
                        self.game.wave.print(f"{npc.name} death animation finished "
                                             f"({Terrain.tick_to_string(self.game.wave.relative_tick)}).")
                    # Spawn eggs
                    # TODO: BUILD Spawn eggs
                    del npc

        # Handle penance spawns every penance cycle (6s)
        # Spawning has to be handled after penance death, since a penance can die and another spawn in the same tick.
        if self.game.wave.relative_tick % Inspectable.CYCLE == 0 and self.game.wave.relative_tick > 0:
            for key, species in self:
                # Spawning can be stalled, and is added through Game.stall.
                # If there are still reserves and the current penance are less than the maximum available at a time.
                if self.spawns[key][1] > 0 and self.can_spawn(key):
                    self.spawns[key][1] -= 1  # Decrease the reserve count.
                    self.game.stall((self.spawn, (species, self.game.wave.relative_tick), {}))  # Spawn a new penance.

        return self.count_alive() != 0 or self.count_reserves() != 0

    # Key is the one letter yield string that represents the penance species.
    def can_spawn(self, key: Union[Type[Npc], list, int, str]) -> bool:
        key = self._get_letter(key)
        if self.get_due_to_spawn(key):
            return True

        if len(self[key]) < self.spawns[key][0]:
            return True

        return False

    def spawn(self, key: Union[Type[Npc], list, int, str], tick: int = None) -> Npc:
        key = self._get_letter(key)
        new_species = self._get_type(key)(self.game)
        self.set_due_to_spawn(key, False)
        self[key].append(new_species)
        self.game.wave.print(f"A new {new_species.default_name.lower()} has spawned "
                             f"({Terrain.tick_to_string(self.game.wave.relative_tick)}).")
        if tick is not None:
            new_species.name = f"{Terrain.tick_to_string(tick):0>3}" + " " + new_species.default_name

        if isinstance(new_species, penance.Runner):
            # Runner forced movements can be set using the set_runner_movements function.
            if len(self.runner_movements) > 0:
                new_species.forced_movements = self.runner_movements.pop(0)

        return new_species

    def get_due_to_spawn(self, key: Union[Type[Npc], list, int, str]) -> bool:
        return self._due_to_spawn[self._get_letter(key)]

    def set_due_to_spawn(self, key: Union[Type[Npc], list, int, str], value: bool) -> None:
        self._due_to_spawn[self._get_letter(key)] = value

    def _get(self, key: Union[Type[Npc], list, int, str], choices: List):
        if isinstance(key, str):
            key = key.lower()
        if isinstance(key, list):
            key = id(key)
        if key in [penance.Fighter, id(self.fighters), "fighters", "fighter", "a", 0]:
            return choices[0]
        if key in [penance.Ranger, id(self.rangers), "rangers", "ranger", "s", 1]:
            return choices[1]
        if key in [penance.Runner, id(self.runners), "runners", "runner", "d", 2]:
            return choices[2]
        if key in [penance.Healer, id(self.healers), "healers", "healer", "h", 3]:
            return choices[3]
        raise KeyError(f"Penance[{key}] does not exist.")

    def _get_type(self, key: Union[Type[Npc], list, int, str]) -> Type:
        return self._get(key, [penance.Fighter, penance.Ranger, penance.Runner, penance.Healer])

    def _get_letter(self, key: Union[Type[Npc], list, int, str]) -> str:
        return self._get(key, ["a", "s", "d", "h"])

    def _get_list(self, key: Union[Type[Npc], list, int, str]) -> List[Npc]:
        return self._get(key, [self.fighters, self.rangers, self.runners, self.healers])

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
