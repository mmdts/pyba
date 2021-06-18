from __future__ import annotations

from random import choice
import re
from typing import Union, Optional, List, Callable, Deque, Tuple, Dict

# Note that blocking and sight calculations here are inaccurate, but are intentionally left this way to simplify
# writing code. Right now, I prefer code legibility and ease over code rigour and speed.
# When converting this project to C++ (for optimization) at some point, however, I will resort to using masks
# and making it proper. I will also unassume some of the other assumptions at that point.
#
# Tiles:
# $ - Wall that blocks movement but not sight.
# # - Wall that blocks movement and sight.
# · - Normal tile with height of 0. Every tile mentioned has this height level unless otherwise explicitly mentioned.
# . - Normal tile with height of 1 that serves as an entrance to high ground.
# ^ - High ground tile with height of 2. Blocks Npc movement but not player movement.
#
# O - Normal tile. Indicator tile for healer lure range.
# o - Normal tile. Indicator tile for attacker recommended area.
# M - Normal tile. Indicator tile for main stack.
#
# A, S, H, D - Normal tiles. Penance spawn areas.
# a, s, h, c, d - Normal tiles. Player spawn areas.
# L, l - Normal tiles. Log spawn areas.
# m - Normal tile. Hammer spawn area.
#
# B - Normal tile. Runner escape area indicator. Set to be this specific tile because it's also a special destination.
# 1, 2, 3, 4 - Normal tiles. Runner special movement zone identifiers.
# 5, 6, 7 - Normal tiles. Runner special movement destinations.
#
# q, w, e, y - Dispensers. Block movement and sight.
# R, r - Hoppers. Block movement and sight and have a height level of 2.
# K, k - Cannons. Block movement but not sight and have a height level of 2.
# X - Ladder. Blocks movement but not sight.
# P - Pool. Four tiles, blocks movement but not sight.
# T, t - Traps. Blocks neither movement nor sight.
#
# Note: Sight and movement are only allowed if the height difference is less than 2.
# Check out the implementations of C.can_single_step and C.can_single_see for more details.
from log import game_print, X, K

Action = Tuple[Callable, Tuple, Dict]

MAP: List[str] = [
    "#################$$$$$#################",
    "###########$###$$$···$$$###$###########",
    "#####$###$$$·A···l·······D·$$$###$#####",
    "####$$············L··············$$####",
    "####$··S·······················H··$$###",
    "###$$······························$###",
    "##$$····················M··········$###",
    "##$··················m·············$$##",
    "##$·······o·························$$#",
    "##$··································$#",
    "#$$··································$#",
    "$$··································$$#",
    "$···································$##",
    "$···································$##",
    "$$······#^^^#··············#^^^#····$$#",
    "#$$·····^^kr^··············^^KR^··T··$$",
    "##$·t···^^^^^··············^^^^^······$",
    "#$$·····#^^^#··············#^^^#······$",
    "#$·······^^^················^^^·······$",
    "#$·······^^^····O···········^^^z······$",
    "#$·······...················...·······$",
    "#$····································$",
    "#$····································$",
    "#$····································$",
    "#$····································$",
    "#$$···································$",
    "##$$·································#$",
    "###$································##$",
    "###$·······························##$#",  # <-- There's an intentional inaccuracy in the last tile of this line.
    "###$$·····························.^^^#",
    "####$$····························.^^^#",  # <-- The rest of the map in the horn area is intentionally clipped
    "#####$··············a·············.^^^#",  # <-- and replaced with walls.
    "#####$$·········2··s·h············.^^^#",
    "######$$$$X····5··c673d···········4####",
    "#########$$$$·1PP··········$$$$$$$$$$$#",
    "############$$·PP··B··qwey$$###########",
    "#############$$$$$####$$$$$############",
]

# Free Letter Set
F = {
    # Penance
    "h": "@",
    "d": "%",
    "s": "&",
    "a": "?",
    # Players
    "H": "E",
    "A": "Q",
    "S": "Z",
    "D": "W",
    "C": "Y",
}

# A copy of map to set tiles on which players are standing as blocked, and check for them later.
# Like the map above, do not interact with this directly, and use the Terrain functions provided:
# Terrain.block, Terrain.unblock, Terrain.is_blocked
BLOCK_MAP = MAP.copy()


class C:  # Tile, Location, Displacement
    def __init__(self, x: Union[C, int], y: Optional[int] = None):
        self.parent: Optional[C] = None  # For BFS
        self.is_difference: bool = False  # To prevent errors.

        if isinstance(x, self.__class__) and y is None:
            # This form is possible for copying: C(my_var) but it's more recommended to use my_var + D.X instead.
            self.x: int = x.x
            self.y: int = x.y
            self.parent = x.parent
            self.is_difference = x.is_difference
            return

        if isinstance(x, int) and isinstance(y, int):
            self.x = x
            self.y = y
            return

        assert True, "None of the conditions required for the formation of C from the given arguments were met."

    def __getitem__(self, key: Union[int, str]) -> int:
        if key == 0 or key == "x":
            return self.x
        if key == 1 or key == "y":
            return self.y
        raise KeyError(f"C[{key}] does not exist.")

    def __setitem__(self, key: Union[int, str], value: int) -> None:
        if key == 0 or key == "x":
            self.x = value
            return
        if key == 1 or key == "y":
            self.y = value
            return
        raise KeyError(f"C[{key}] cannot be set because it does not exist.")

    def __str__(self) -> str:
        return f"{X}({self.x:>2}, {self.y:>2}, {Terrain.letter_at(self)}){K}"

    def __hash__(self) -> int:
        return hash((self.x, self.y))

    def __eq__(self, other: C) -> bool:
        assert isinstance(other, self.__class__) or other is None, \
            "Cannot compare equality to something that isn't of type C."
        if other is None:
            return False  # We are definitely of type C here and are not None!
        return self.x == other.x and self.y == other.y

    def __add__(self, other: C) -> C:
        assert isinstance(other, self.__class__), "Cannot add something that isn't of type C."
        return self.__class__(self.x + other.x, self.y + other.y)

    def __sub__(self, other: C) -> C:
        assert isinstance(other, self.__class__), "Cannot subtract something that isn't of type C."
        difference = self.__class__(self.x - other.x, self.y - other.y)
        difference.is_difference = True
        return difference

    def __mul__(self, other: int) -> C:
        assert isinstance(other, int), "Cannot multiply by something that isn't an int."
        return self.__class__(self.x * other, self.y * other)

    def __floordiv__(self, other: int) -> C:
        assert isinstance(other, int), "Cannot divide by something that isn't an int."
        return self.__class__(self.x // other, self.y // other)

    def __rmul__(self, other):
        return self.__mul__(other)

    def compare_assert(self, other: int):
        assert self.is_difference, "Only length intervals and not actual tiles can be compared."
        assert isinstance(other, int), "Type C can only be compared to an int."

    def step_assert(self):
        assert self.is_difference, "Steps can only be taken from a difference."

    def __lt__(self,  other: int) -> bool:
        self.compare_assert(other)
        return abs(self.x) < other and abs(self.y) < other

    def __gt__(self,  other: int) -> bool:
        self.compare_assert(other)
        return abs(self.x) > other and abs(self.y) > other

    def __le__(self,  other: int) -> bool:
        self.compare_assert(other)
        return abs(self.x) <= other and abs(self.y) <= other

    def __ge__(self,  other: int) -> bool:
        self.compare_assert(other)
        return abs(self.x) >= other and abs(self.y) >= other

    def copy(self):
        # Copy is great because it doesn't copy over parent and is_difference, unlike
        # initializing a C from this C.
        return self + D.X

    def single_step_x(self) -> C:
        self.step_assert()
        return self.x > 0 and D.E or self.x < 0 and D.W or D.X

    def single_step_y(self) -> C:
        self.step_assert()
        return self.y < 0 and D.N or self.y > 0 and D.S or D.X

    def single_step(self) -> C:
        self.step_assert()
        return self.single_step_x() + self.single_step_y()

    def single_step_taxicab(self) -> C:
        if abs(self.x) <= abs(self.y):
            return self.single_step_y()  # Equal is with Y
        return self.single_step_x()

    def taxicab_to(self, other: C) -> int:
        # Look up Taxicab Distance to understand why this is named this way and how it functions.
        # A quick analogy to chess would be the shortest distance traversed by a rook to reach a tile.
        d = self - other
        return abs(d.x) + abs(d.y)

    def chebyshev_to(self, other: C) -> int:
        # Look up Chebyshev Distance to understand why this is named this way and how it functions.
        # A quick analogy to chess would be the shortest distance traversed by a king / queen to reach a tile.
        d = self - other
        return max(abs(d.x), abs(d.y))

    def is_aligned_with(self, other: C):
        assert isinstance(other, self.__class__), "Cannot check alignment to something that isn't of type C."
        return self.x == other.x or self.y == other.y

    def is_southwest_of(self, other: C):
        # Returns true on equality as well.
        return self.x <= other.x and self.y >= other.y

    def get_closest_of(self, others: List[C]) -> C:
        rv = others[0]
        dist = E.MAP_MAX_DIST
        for c in others:
            tmp_dist = c.chebyshev_to(self)
            if tmp_dist < dist:
                rv = c
                dist = tmp_dist
        return rv

    def get_adjacent_tiles(self) -> List[C]:
        rv = []

        # For BFS related reasons, this should return the tiles in a specific order.
        # Game tends for x movement (east/west) before y movement (north/south).
        # Game tends for negative x movement (west), and positive y movement (south) before their direction opposites.
        # Game tends for rook movement before bishop movement.
        for i in [D.W, D.E, D.S, D.N, D.SW, D.SE, D.NW, D.NE]:
            rv.append(self + i)

        return rv

    def can_single_step(self, destination: C, call_npc_function: bool = False) -> bool:
        # We can only single step to a square that's king-movable (one of the eight squares around us).
        if self.chebyshev_to(destination) > 1:
            return False

        # We cannot cross cannon walls.
        if abs(Terrain.level_at(self) - Terrain.level_at(destination)) > 1:
            return False

        # We can only step on tiles that are not blocked by default. Note that Player blocking is not handled here,
        # as this is only about the tile itself, and is shared by both Player pathing and Npc pathing, while only
        # Npcs can't single step on a player blocked tile.
        #
        # For Player blocking of Npcs, check out Npc.can_single_step
        if not Terrain.is_occupiable(destination):
            return False

        # We can always single step horizontally.
        if self.taxicab_to(destination) == 1 and Terrain.is_occupiable(destination):
            return True

        # We can only single step diagonally if both horizontal king moves beside the diagonal tile are free.
        # Otherwise, our path is L shaped.

        move = destination - self
        x_tile = C(self.x + move.x, self.y)
        y_tile = C(self.x, self.y + move.y)

        recursion_function: Callable = call_npc_function and self.can_npc_single_step or self.can_single_step

        if self.chebyshev_to(destination) == 1 and \
           recursion_function(x_tile) and \
           recursion_function(y_tile) and \
           x_tile.can_single_step(destination) and \
           y_tile.can_single_step(destination):
            return True

        return False

    def can_npc_single_step(self, destination: C) -> bool:
        if Terrain.level_at(destination) > 1:
            # The penance cannot step on all cannon squares.
            return False

        if Terrain.is_blocked(destination):
            # The penance cannot step on a tile blocked by a player.
            # Note that a player stepping you unblocks the tile (Runescape mechanism).
            return False

        return self.can_single_step(destination, call_npc_function=True)

    def can_single_see(self, destination: C) -> bool:
        # Very similar in mechanics for C.can_single_step, but for seeing.
        # Check C.can_single_step for comments on what the lines below do.
        if self.taxicab_to(destination) > 1:
            return False
        if abs(Terrain.level_at(self) - Terrain.level_at(destination)) > 1:
            return False
        if not Terrain.is_seeable(destination):
            return False
        return True

    # TODO: REMEMBER Sight is required for Player to launch an attack against a CombatNpc
    def can_see(self, destination: C) -> bool:
        # We have an iterator that starts at self, and is supposed to reach destination by traversing in blocks of
        # absolute magnitude of 1 in the long axis and slope in the short axis (with the respective sign for direction).
        iterator = self.copy()
        dist = destination - iterator

        # We can see the square we're standing on.
        if dist == D.X:
            return True

        short_axis = abs(dist.x) > abs(dist.y) and 1 or 0
        long_axis = 1 - short_axis

        # Shifts are done so that "integer decimals" have a precision of 16 bits.
        # Any variable that starts with the decimal_ prefix exists in decimal space.
        # We need to deal with decimals because we have slopes that are always less than 1.
        decimal_short_axis = iterator[short_axis] << E.DECIMAL_SHIFT

        # Our short axis is the smaller distance, so that slope is always less than 1.
        # The slope should always take the sign of the short axis, therefore, the long distance is considered absolute.
        # We add a slope for the short axis each time we add 1 for the long axis.
        decimal_slope = (dist[short_axis] << E.DECIMAL_SHIFT) // abs(dist[long_axis])

        # This is our movement in the long axis is a big number (1 or -1 is bigger than the fractional slope).
        long_axis_increment = dist[long_axis] > 0 and 1 or -1

        # The half add:
        # We add half to start at a corner. This makes it so that starting to "increment up by adding the slope"
        # starts from the "face" of the tile, rather than  its closer-to-map-zero (East/North in my implementation)
        # corner.
        #
        # The conditional add:
        # We want a slope of negative half to actually bring us below the
        # decimal 0xH0000 and bring us to the decimal 0xLFFFF where H and L are number examples with L = H - 1
        # This conditional add only affects situations in which the slope is exactly half.
        decimal_short_axis += E.DECIMAL_HALF + (dist[short_axis] < 0 and -1 or 0)

        # In the loop below, iterator[s] is always linearly incremented, and for each increment of iterator[s],
        # iterator[m] is increased by a fraction of a square (by assigning it a reconverted value from decimal_m).

        # We check for can_single_see once, and a second time if the added decimals form a full square.
        while iterator[long_axis] != destination[long_axis]:
            """ Check one longer distance tile"""

            old_iterator = iterator.copy()

            iterator[long_axis] += long_axis_increment

            # This line does nothing on the first run of the loop, but on subsequent runs, it will update
            # iterator[m] with the new decimal_m made from adding the slope a few lines later.
            iterator[short_axis] = decimal_short_axis >> E.DECIMAL_SHIFT

            if not old_iterator.can_single_see(iterator):
                return False

            """ Check a fraction of a shorter distance tile"""

            # Add the slope and recheck, form the old_iterator and iterator just like above, and recheck if the tile
            # is different, then check for can_single_see a second time if it is.
            decimal_short_axis += decimal_slope

            old_iterator = iterator.copy()

            iterator[short_axis] = decimal_short_axis >> E.DECIMAL_SHIFT

            if old_iterator[short_axis] == iterator[short_axis]:
                # We haven't formed a full square from those decimals (made by adding slope) yet.
                continue

            if not old_iterator.can_single_see(iterator):
                return False

        # If we could see all the tiles in the middle, the loop breaks, and we reach here.
        return True

    def renders_tile(self, destination: C) -> bool:
        return self.chebyshev_to(destination) <= E.TILE_RENDER_DISTANCE

    def renders_unit(self, target: Locatable) -> bool:
        return self.chebyshev_to(target.location) <= E.UNIT_RENDER_DISTANCE

    def renders_game_object(self, target: Locatable) -> bool:
        return self.chebyshev_to(target.location) <= E.GAME_OBJECT_RENDER_DISTANCE

    def renders_dropped_item(self, target: Locatable) -> bool:
        return self.chebyshev_to(target.location) <= E.DROPPED_ITEM_RENDER_DISTANCE

    def get_runner_zone(self) -> C:
        return (self - E.RUNNER_ZONE_EDGE) // E.RUNNER_ZONE_DIM

    def clamp(self, floor: C = None, ceil: C = None) -> C:
        # Clamps a C to only take values between a specified range.
        # Use clamp() to clamp to map.
        # Use clamp(ceil=tile) to set only a ceiling.
        # Use clamp(floor=tile) to set only a floor.
        # Use clamp(t1, t2) to set both.
        if floor is None and ceil is None:
            floor = D.X
            ceil = E.MAP_DIM

        if floor is None:
            return C(min(ceil.x, self.x), min(ceil.y, self.y))

        if ceil is None:
            return C(max(floor.x, self.x), max(floor.y, self.y))

        return C(max(min(ceil.x, self.x), floor.x), max(min(ceil.y, self.y), floor.y))


class D:  # Direction
    B = None  # Beside. Used in follow and can_act_on checks.
    X = C(0, 0)  # Under
    N = C(0, -1)
    S = C(0, 1)
    W = C(-1, 0)
    E = C(1, 0)
    SE = S + E
    SW = S + W
    NE = N + E
    NW = N + W


class Y:  # Inventory
    # 0, 1, 2 = typical cdh items. 3 = hammer/vial/bag, 4 = logs, e = empty.
    # m = msb, a = 3ab, c = compb, d = dbow, w = dclaws, h = chally, b = bulwark, y = dhally.
    EMPTY = "_"
    HORN = "H"
    BLOCKED = "X"  # An unknown item (for example, scroll) is blocking this inventory slot.

    TOFU = "0"
    CRACKERS = "1"
    WORMS = "2"
    HAMMER = "3"
    LOGS = "4"

    POISON_TOFU = "0"
    POISON_WORMS = "1"
    POISON_MEAT = "2"
    VIAL = "3"

    RED = "0"
    GREEN = "1"
    BLUE = "2"
    BAG = "3"

    MSB = "0"
    TAB = "1"
    COMPB = "2"
    DBOW = "3"
    DCLAWS = "4"
    CHALLY = "5"
    BULWARK = "6"
    DHALLY = "7"


class Locatable:  # Used by: [Unit, GameObject, DroppedItem]
    def __init__(self, location: C, game: Inspectable):
        self.follow_type: C = D.B
        self.follow_allow_under: bool = False
        self.location: C = location.copy()  # It changes, it needs to be a copy.

        # I know this looks ugly, but this is how we'll be able to find Locatables
        # from our interface in order to draw them.
        self.uuid: int = id(self)
        self.game = game
        self.game.locatables.append(self)
        self.game.uuids.append(self.uuid)

    def is_followable(self) -> bool:
        # Dead NPCs are not followable.
        return True


class Inspectable:
    # This class is used for accessing the game object on the __call__ function of lower classes in the hierarchy.
    # What basically happens is that every class passes the game inspectable down a level when calling
    # the classes it wraps.
    #
    # This interface also has a nice function for stalling actions.
    def __init__(self, arg):  # arg: Game
        self.arg = arg
        self.locatables: List[Locatable] = []
        self.uuids: List[int] = []

        self.text_payload = []  # An array of things printed by Wave and Npc objects. This is exhausted by an interface.

    def find_by_uuid(self, uuid: int):
        return self.locatables[self.uuids.index(uuid)]

    @property
    def wave(self):
        assert self.arg.wave is not None and self.arg.wave.__class__.__name__ == "Wave", \
            "Wave is not set on this inspectable."
        return self.arg.wave

    def start_new_wave(self, wave_number: int, runner_movements: List[List[C]]):
        return self.arg.start_new_wave(wave_number, runner_movements)

    @property
    def tick(self):
        assert self.arg.tick is not None and isinstance(self.arg.tick, int), \
            "Tick is not set on this inspectable."
        return self.arg.tick

    @property
    def players(self):
        assert self.arg.players is not None and self.arg.players.__class__.__name__ == "Players", \
            "Players is not set on this inspectable."
        return self.arg.players

    def stall(self, action: Callable, *args, **kwargs):
        self.arg.players.main_attacker.stall_queue.append((action, args, kwargs))


class Targeting:
    # All methods and constants of class Targeting should be static.
    @staticmethod
    def filter_by_sight(candidates: List[Locatable], center: C, radius: int = None) -> List[Locatable]:
        return [
            candidate for candidate in candidates
            if center.can_see(candidate.location) and
            (radius is None or center.chebyshev_to(candidate.location) <= radius)
        ]

    @staticmethod
    def choice(candidates: List[Locatable], center: C = None, radius: int = None) -> Optional[Locatable]:
        if center is not None:
            candidates = Targeting.filter_by_sight(candidates, center, radius)

        if len(candidates) == 0:
            return None

        return choice(candidates)


class Terrain:
    # All methods and constants of class Terrain should be static.
    BLOCKED_BY_PLAYER = "p"
    BLOCKED = "#qweyKkRrPX$"
    SIGHT_BLOCKED = "#qweyRr"
    HIGH_LEVEL = "^KkRr"

    @staticmethod
    def new() -> List[str]:
        return MAP.copy()

    @staticmethod
    def print(grid: Optional[List[str]] = None) -> None:
        if grid is None:
            grid = MAP
        rv = "\n".join(grid)
        # from os import system
        # system('clear')
        game_print("Terrain.print", "\n", rv)

    @staticmethod
    def queue_info(queue: Union[Deque, List]):
        # Takes a dequeue / list of something printable (with __str__ defined).
        rv = "["
        for tile in queue:
            rv += f"{tile}, "
        rv += "]"
        return rv.replace(", ]", "]")

    @staticmethod
    def is_occupiable(tile: C) -> bool:
        return MAP[tile.y][tile.x] not in Terrain.BLOCKED

    @staticmethod
    def is_seeable(tile: C) -> bool:
        return MAP[tile.y][tile.x] not in Terrain.SIGHT_BLOCKED

    @staticmethod
    def is_blocked(tile: C) -> bool:
        # Returns true for a tile that is blocked by a player that hasn't been run through.
        return BLOCK_MAP[tile.y][tile.x] == Terrain.BLOCKED_BY_PLAYER

    @staticmethod
    def set_letter(tile: C, letter: str, grid: Optional[List[str]] = None) -> None:
        if grid is None:
            grid = MAP
        grid[tile.y] = grid[tile.y][:tile.x] + letter + grid[tile.y][tile.x + 1:]

    @staticmethod
    def block(tile: C) -> None:
        # Blocking by a player.
        Terrain.set_letter(tile, Terrain.BLOCKED_BY_PLAYER, BLOCK_MAP)

    @staticmethod
    def unblock(tile: C) -> None:
        # Unblocking by a player.
        Terrain.set_letter(tile, Terrain.letter_at(tile), BLOCK_MAP)

    @staticmethod
    def letter_at(tile: C) -> str:
        if 0 < tile.x < E.MAP_DIM.x and 0 < tile.y < E.MAP_DIM.y:
            return MAP[tile.y][tile.x]

        return "#"  # Out of bounds are all #.

    @staticmethod
    def level_at(tile: C) -> int:
        letter = MAP[tile.y][tile.x]
        if letter in Terrain.HIGH_LEVEL:
            return 2
        if letter in ".":
            return 1
        return 0

    @staticmethod
    def find(letter) -> Optional[C]:
        for row, row_string in enumerate(MAP):
            col = row_string.find(letter)
            if col != -1:
                return C(col, row)
        return None

    @staticmethod
    def find_nearest(letter: str, location: C) -> Optional[C]:
        rv = None
        dist = E.MAP_MAX_DIST
        for row, row_string in enumerate(MAP):
            col = row_string.find(letter)
            if col != -1:
                tmp_rv = C(row, col)
                tmp_dist = tmp_rv.chebyshev_to(location)
                if tmp_dist < dist:
                    rv = tmp_rv
                    dist = tmp_dist
        return rv

    @staticmethod
    def find_all(letter) -> List[Optional[C]]:
        matches = []
        for row, row_string in enumerate(MAP):
            col = row_string.find(letter)
            if col != -1:
                matches.append(C(row, col))
        return matches

    @staticmethod
    def tick_to_string(tick: int) -> str:
        seconds = 3 * tick // 5
        remainder = (3 * tick) % 5 * 2
        return str(seconds) + (remainder and "." + str(remainder) or "") + "s"

    @staticmethod
    def filter_food_by_zone(food_list: List[Locatable], zone: C) -> List[Locatable]:
        # This information should be memoized in the C++ version of this project.
        return [food for food in food_list if food.location.get_runner_zone() == zone]

    @staticmethod
    def parse_runner_movements(runner_movements: str) -> List[List[C]]:
        assert re.match("^(([wesWES]+-)+[wesWES]+)?$", runner_movements), \
            f"Invalid runner movements {runner_movements} were given. " \
            f"Please use standard runner movement syntax."
        return [
            [getattr(D, movement.upper()) for movement in list(runner)]
            for runner in runner_movements.split("-") if len(runner) > 0
        ]


class E:  # Element - All constants are of type C unless otherwise stated.
    # Npcs
    FIGHTER_SPAWN = Terrain.find("A")
    RANGER_SPAWN = Terrain.find("S")
    PENANCE_HEALER_SPAWN = Terrain.find("H")
    RUNNER_SPAWN = Terrain.find("D")

    # Players
    MAIN_ATTACKER_SPAWN = Terrain.find("a")
    SECOND_ATTACKER_SPAWN = Terrain.find("s")
    HEALER_SPAWN = Terrain.find("h")
    COLLECTOR_SPAWN = Terrain.find("c")
    DEFENDER_SPAWN = Terrain.find("d")

    # DroppedItems
    HAMMER_SPAWN = Terrain.find("m")
    LOGS_SPAWN = Terrain.find("L")
    FAR_LOGS_SPAWN = Terrain.find("l")

    # GameObjects
    CANNON = Terrain.find("K")
    WEST_CANNON = Terrain.find("k")
    HOPPER = Terrain.find("R")
    WEST_HOPPER = Terrain.find("r")
    TRAP = Terrain.find("T")
    WEST_TRAP = Terrain.find("t")

    # Dispensers
    ATTACKER_DISPENSER = Terrain.find("q")
    DEFENDER_DISPENSER = Terrain.find("w")
    HEALER_DISPENSER = Terrain.find("e")
    COLLECTOR_DISPENSER = Terrain.find("y")

    # Unused GameObjects
    LADDER = Terrain.find("X")
    POOL_TILE = Terrain.find("P")
    POOL_TILES: List[C] = Terrain.find_all("P")

    # Tiles and Thresholds
    MAIN_STACK = Terrain.find("M")
    HENDI_SQ1 = TRAP + 3 * D.NW + D.N
    HENDI_SQ2 = HENDI_SQ1 + 4 * D.E
    HENDI_SQ3 = HENDI_SQ2 + 3 * D.S
    RUN_WEST_THRESHOLD = Terrain.find("O")
    STAY_WEST_THRESHOLD = Terrain.find("o")
    WAIT_TILE = Terrain.find("z")

    # Runner Tiles and Thresholds
    # # Y Comparison
    RAA_TILE = Terrain.find("B")  # South check.
    RUNNER_REDIRECT_1 = Terrain.find("1")  # Equality check.
    # # Full Tile Comparison
    RUNNER_DESTINATION_1 = Terrain.find("5")
    RUNNER_REDIRECT_2 = Terrain.find("2")  # Southwest check.
    RUNNER_DESTINATION_2 = Terrain.find("6")
    RUNNER_REDIRECT_3 = Terrain.find("3")  # Southwest check on this and '1'. Destination is RAA_TILE.
    RUNNER_REDIRECT_4 = Terrain.find("4")  # Southwest check.
    RUNNER_DESTINATION_4 = Terrain.find("7")

    # Complex Tiles
    MAIN_LURE_SPOT = TRAP + 2 * D.E  # Two steps east of east trap.
    # Keep in mind that following the object in question will get you to the given tile without explicitly
    # specifying it. Always follow when possible, and only use these tiles for sanity asserts.
    CANNON_FIRE_SPOT = CANNON + D.S
    WEST_CANNON_FIRE_SPOT = WEST_CANNON + D.S
    HOPPER_LOAD_SPOT = HOPPER + D.S
    WEST_HOPPER_LOAD_SPOT = WEST_HOPPER + D.S
    ATTACKER_RESTOCK_SPOT = ATTACKER_DISPENSER + D.N  # NOT USED
    DEFENDER_RESTOCK_SPOT = DEFENDER_DISPENSER + D.N  # NOT USED
    HEALER_RESTOCK_SPOT = HEALER_DISPENSER + D.N  # NOT USED
    COLLECTOR_RESTOCK_SPOT = COLLECTOR_DISPENSER + D.N  # NOT USED

    # VERY IMPORTANT! This tile sets the start of the first runner zone.
    # Runner zones are 8x8 areas which affect lure mechanics. In the rest of RS, zones/chunks
    # they affect map loading among other things, but they witness this specific meaningful
    # usage in BA, which is why they're referred to as runner zones in this code.
    #
    # Basically what happens is that runners target food based on two rules:
    # 1. The food in the zone with the highest priority (zone priorities can be found in
    #    Runner.tick_target's scan_order variable).
    # 2. The food that has been placed last among all the foods in this zone.
    #
    # Use the the function C.get_runner_zone() to avoid making a mistake.
    RUNNER_ZONE_EDGE = C(-3, -6)
    RUNNER_ZONE_DIM: int = 8
    RUNNER_ZONE_COUNT: int = 6
    RUNNER_ZONE_CLAMP_SQ = C(RUNNER_ZONE_COUNT - 1, RUNNER_ZONE_COUNT - 1)

    # Map Dimensions
    MAP_DIM = C(len(MAP[0]), len(MAP))
    MAP_MAX_DIST: int = max(MAP_DIM.x, MAP_DIM.y)

    # Line of Sight
    DECIMAL_SHIFT: int = 16
    DECIMAL_HALF: int = 1 << (DECIMAL_SHIFT - 1)

    # Render Distances
    TILE_RENDER_DISTANCE: int = 44
    GAME_OBJECT_RENDER_DISTANCE: int = 40  # 30
    UNIT_RENDER_DISTANCE: int = 40  # 15
    DROPPED_ITEM_RENDER_DISTANCE: int = 40  # 20
