from random import random
from typing import List, Tuple, Optional

from game_object import Trap
from log import debug
from terrain import Terrain, C, D, E, Inspectable
from npc import Npc
from dropped_item import Food


class Runner(Npc):
    HITPOINTS: List[int] = [5, 5, 5, 5, 5, 5, 5, 5, 5, 5]
    SPAWNS: List[Tuple[int, int]] = [(2, 0), (2, 1), (2, 2), (3, 1), (4, 1), (4, 2), (5, 1), (5, 2), (6, 2), (5, 1)]

    SNIFF_DISTANCE: int = 5  # Hardcoded, because I'm assuming everyone is level 5.
    TILES_PER_RANDOM_WALK = 5
    TARGET_STATE_COUNT: int = 3
    INITIAL_TARGET_STATE: int = -1

    DEATH_MESSAGE: str = "Urghhh!"
    ESCAPE_MESSAGE: str = "Raaa!"
    CORRECT_EAT_MESSAGE: str = "Chomp, chomp."
    INCORRECT_EAT_MESSAGE: str = "Blughhhh."

    DUE_TO_SPAWN_TICKS: int = 1
    URGH_RAA_DELAY: int = 2  # For the two-tick delay between chomping and urghing, or reaching cave and raaing.

    # Maps a cycle to the target state at which the runner tries to target on that cycle.
    CYCLE_MAP: List[int] = [None, None, 2, 3, 1, 2, 3]

    """Basic Functions"""

    def __init__(self, wave_number: int, game: Inspectable):
        super().__init__(wave_number, E.RUNNER_SPAWN, game)
        self.target_state: int = Runner.INITIAL_TARGET_STATE

        self.is_inherently_followable: bool = False
        self.forced_movements: List[C] = []
        self.blugh_i: int = 0
        self.has_chomped: bool = False
        self.has_escaped: bool = False
        self.urgh_raa_i: int = self.URGH_RAA_DELAY

        self.followee: Optional[Food] = None

    def str_info(self):
        return f"{self.name}({self.game.tick}, {self.cycle}, {self.target_state})@{str(self.location)}"

    """Tick Functions"""
    def do_cycle(self):
        # Runner do_cycle does not call self.unit_call because runners do not path normally or attack.
        if self.has_chomped:
            self.urgh_raa_i -= 1
            if self.urgh_raa_i == 0:
                self.state = self.DEAD
                self.print(self.DEATH_MESSAGE)
            return

        if self.has_escaped:
            # Escape takes 1 tick to set dead here, then 2 ticks to despawn in Npc.tick_despawn.
            # TODO: CHECK escape duration.
            #
            # Since Penance decrements the amount of reserve runners when spawning them,
            # we need to re-add this escaped runner back to reserves by incrementing that count.
            self.game.wave.penance.spawns["d"][1] += 1
            self.state = self.DEAD
            return

        if self.cycle == 1:
            self.tick_1(self.game.wave.dropped_food, self.game.wave.game_objects.traps)

        if self.cycle in [2, 3, 4, 5]:
            self.tick_target(self.game.wave.dropped_food)

        if self.cycle == 6:
            self.tick_6(self.game.wave.dropped_food, self.game.wave.game_objects.traps)

        # The runner will never retarget on 7, 8, 9, 0.
        if self.cycle in [2, 3, 4, 5, 7, 8, 9, 0]:
            self.tick_eat(self.game.wave.dropped_food, self.game.wave.game_objects.traps)

        # TODO: DEBUG Confirm blughing is working as expected.

        # TODO: SESSION 1 WITH AKRAELT.
        # TODO: BUILD Right click examine mobs
        # TODO: FIX runner hard crashing on e-s movement gets stuck.
        # TODO: FIX runner eating then walking 1 step south dies a tick later.
        # TODO: FIX food that remains over after reclicking wave start right after dropping so next tick is in a new wave.
        # TODO: FIX when runners want to path diagonally and its blocked, they dont move east/west like they're supposed to.

        return

    def tick_despawn(self) -> bool:
        # Runner tick_despawn breaks traps if Npc tick_despawn returns True.
        rv = super().tick_despawn()
        if rv:
            for trap in self.game.wave.game_objects.traps:
                if self.location.chebyshev_to(trap.location) <= 1 and trap.charges > 0:
                    trap.charges -= 1  # We don't need to check for chomp because cannoning a runner beside
        return rv                      # a trap reduces charges.

    def tick_1(self, food: List[Food], traps: List[Trap]) -> None:
        self.tick_escape()
        if self.blugh_i == 0:
            self.target_state += 1
            if self.target_state > Runner.TARGET_STATE_COUNT:
                self.target_state = 1
        else:
            self.blugh_i -= 1

        self.tick_eat(food, traps)

        if self.blugh_i == 0 and self.followee is None:
            self.stop_movement()

    def tick_6(self, food: List[Food], traps: List[Trap]) -> None:
        self.tick_escape()
        if self.blugh_i > 0:
            self.blugh_i -= 1

        self.tick_target(food)
        self.tick_eat(food, traps)

        if self.followee is None and self.blugh_i == 0:
            # Start a special move or a random move.
            self.target = self.walk()

    def tick_target(self, food: List[Food]) -> None:
        if self.target_state == self.CYCLE_MAP[self.cycle]:
            zone = self.location.get_runner_zone()
            # The runner scans the map zones in order, preferring east size over west size, then north over south.
            # Map zones are 8x8 areas of the map starting at a certain offset.
            scan_order = [D.NE, D.E, D.SE, D.N, D.X, D.S, D.NW, D.W, D.SW]
            first_food = None
            for zone_delta in scan_order:
                scan_zone = zone + zone_delta
                if scan_zone != scan_zone.clamp(D.X, E.RUNNER_ZONE_CLAMP_SQ):
                    continue

                # Within the first zone (in order of preference) in which food it has a line-of-sight over is found,
                # the runner eats the newest-placed food  it has a line-of-sight over.
                for o in reversed(Terrain.filter_food_by_zone(food, scan_zone)):  # Reversed so newest first.
                    if not self.can_see(o):
                        continue
                    if first_food is None:
                        first_food = o
                    if self.location.chebyshev_to(o.location) <= self.SNIFF_DISTANCE:
                        debug("Runner.tick_target",
                              f"{self.str_info()} switched target from {self.followee} to {first_food}.")

                        self.target_state = 0
                        self.follow(first_food)
                        return

    def step(self) -> None:
        # TODO: REFACTOR. Remove his entire overload is here only to debug.
        debug("Runner.step",
              f"{self.str_info()} stepping with queue: {Terrain.queue_info(self.pathing_queue)}.")

        return super().step()

    def tick_eat(self, food: List[Food], traps: List[Trap]) -> bool:
        # Returns False if no action concerning the food has been made: We are still following or random-walking.
        # Returns True if an action concerning the food has been made: We just ate it or it has been picked up.
        # Currently, the return value has no use.
        if self.followee is None:
            # Not targeting any food. Probably will random-walk.
            debug("Runner.tick_eat",
                  f"{self.str_info()} has no target. It is random walking.")
            return False

        if self.followee not in Terrain.filter_food_by_zone(food, self.followee.location.get_runner_zone()):
            # The food got picked up.
            self.stop_movement()
            self.target_state = 0
            debug("Runner.tick_eat",
                  f"{self.str_info()} tried to eat {self.followee} but it got picked/eaten.")
            return True

        if self.location != self.followee.location:
            # Hasn't reached the food yet, or stuck.. Will continue following.
            # It checks for this BEFORE stepping, which means it eats one tick after the final step,
            # and not on the final step tick?
            debug("Runner.tick_eat",
                  f"{self.str_info()} tried to eat {self.followee} but it hasn't reached it yet.")
            return False

        # At this point, we're on top of our target food that still exists.
        if self.followee.is_correct:
            self.print(Runner.CORRECT_EAT_MESSAGE)

            # If it ate beside a trap, set it to dead so that Runner.__call__ can take care of the rest of the
            # death sequence (passing False to Penance.__call__ at the very end).
            for trap in traps:
                if self.location.chebyshev_to(trap.location) <= 1 and trap.charges > 0:
                    self.state = self.DEAD
        else:
            # We ate a wrong food.
            self.print(Runner.INCORRECT_EAT_MESSAGE)

            self.blugh_i = 3
            self.target_state = 0
            self.cycle -= (self.cycle > 5 or self.cycle == 0) and 5 or 0  # Reduce the higher cycles by 5.

            # Blugh moves have special logic for wave 10, be careful when implementing.
            self.target = C(self.location.x, (E.TRAP + 4 * D.N).y)

        debug("Runner.tick_eat",
              f"{self.str_info()} ate {self.followee}, which was {self.followee.is_correct and 'correct' or 'wrong'}.")

        # Remove the food.
        food.pop(food.index(self.followee))
        self.stop_movement()

        return True

    def tick_escape(self) -> None:
        if self.location.y == E.RAA_TILE.y:
            self.has_escaped = True
            self.print(self.ESCAPE_MESSAGE)

    """Get Functions"""

    def get_random_walk(self) -> C:
        # Forced movement can be set to simulate a wave when runners move the specified movement.
        # It can be used by appending to the forced movement array the number of specified moves you want.
        # For example: some_newly_created_runner.forced_movements.append(D.W) will make that runner a westie.
        if len(self.forced_movements) > 0:
            return self.forced_movements.pop(0)

        # Runners have a 1/6 chance for east movement, 1/6 for west movement, and 4/6 for south movement.
        # Runners do not automatically random-walk north ever.
        roll = int(random() * 6)
        if roll == 0:
            return D.E
        if roll == 1:
            return D.W
        return D.S

    """Movement Functions"""

    def walk(self) -> C:
        if self.location == E.RUNNER_REDIRECT_1:
            return E.RUNNER_DESTINATION_1
        if self.location.is_southwest_of(E.RUNNER_REDIRECT_2) and \
                not self.location.is_southwest_of(E.RUNNER_REDIRECT_1):
            return E.RUNNER_DESTINATION_2
        if self.location.is_southwest_of(E.RUNNER_REDIRECT_3):
            return E.RAA_TILE
        if self.location.is_southwest_of(E.RUNNER_REDIRECT_4):
            return E.RUNNER_DESTINATION_4

        destination = self.location + self.TILES_PER_RANDOM_WALK * self.get_random_walk()

        # We clamp the destination to be between both traps.
        # This has a different rule for wave 10 so be careful when implementing.
        destination.x = max(min(destination.x, E.TRAP.x), (E.WEST_TRAP + D.W).x)

        debug("Runner.walk",
              f"{self.str_info()} decided to walk to {destination}.")

        return destination
