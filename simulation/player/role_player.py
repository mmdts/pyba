from typing import List, Tuple, Optional

from dispenser import Dispenser
from dropped_item import Food, DroppedItem, Logs, Hammer
from game_object import Trap, WEGameObject
from log import debug, M, J
from terrain import C, E, Inspectable, Y, Terrain, Action, Locatable
from player import Player
from healer import Healer as PenanceHealer

# Gear bonuses are on the form of (accuracy, damage, set bonus, attack speed, range)
from unit import POST, PRE

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
        self.calls_with = Collector
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


class Defender(Player):
    CALLS = ["tofu", "crackers", "worms"]
    TRAP_BUSY_WAIT: int = 5

    def __init__(self, game: Inspectable):
        super().__init__(E.DEFENDER_SPAWN, game)
        self.calls_with = Healer
        self.trap: Optional[Trap] = None
        self.actions.extend([
            (Trap, self.repair_trap, PRE),
        ])

    def __call__(self) -> bool:
        if self.trap is not None and self.busy_i == 0:
            self.trap.charges = 2
            self.inventory[self.inventory.index(Y.LOGS)] = Y.EMPTY
            self.trap = None
        debug("Defender.repair_trap", f"Defender successfully repaired the trap.")

        return super().__call__()

    @staticmethod
    def access_letter() -> str:
        return "d"

    @property
    def choice_arg(self) -> List[Locatable]:
        rv = super().choice_arg
        rv.extend(self.game.wave.dropped_hnls)
        rv.extend(self.game.wave.dropped_food)
        rv.extend(self.game.wave.game_objects.traps)
        return rv

    def use_dispenser(self, option: Optional[int] = None) -> None:
        self._use_dispenser(option)

        alternator_i = 0
        alternator = [Y.CRACKERS, Y.TOFU, Y.WORMS]

        for key, slot in enumerate(self.inventory):
            if slot == Y.EMPTY:
                self.inventory[key] = alternator[alternator_i]
                alternator_i = (alternator_i + 1) % len(alternator)

        self.busy_i = Player.DISPENSER_BUSY_WAIT

    def drop_food(self, food_type: int, count: int) -> None:
        assert str(food_type) in self.inventory, "We cannot drop food we do not have."
        assert food_type < self.CALL_COUNT, "We cannot drop things that aren't food."
        for i in range(count):
            self.game.wave.dropped_food.append(Food(
                self.location,
                food_type,
                food_type == self.correct_call,
                self.game
            ))
            self.inventory[self.inventory.index(str(food_type))] = Y.EMPTY

    def drop_select_food(self, inventory_slots: List[int]) -> None:
        for slot in inventory_slots:
            if self.inventory[slot] not in [Y.CRACKERS, Y.TOFU, Y.WORMS]:
                continue
            self.game.wave.dropped_food.append(Food(
                self.location,
                int(self.inventory[slot]),
                int(self.inventory[slot]) == self.correct_call,
                self.game
            ))
            self.inventory[slot] = Y.EMPTY

    def repair_trap(self) -> bool:
        assert self.followee.charges < 2, "Cannot repair a trap that's already repaired."

        debug("Defender.repair_trap", f"Defender successfully reached the trap and will attempt to repair it.")

        if Y.LOGS in self.inventory and Y.HAMMER in self.inventory:
            self.busy_i = Defender.TRAP_BUSY_WAIT  # Repairing trap is a 5 tick action.
            self.trap = self.followee
            debug("Defender.repair_trap", f"Defender successfully queued the trap repair action.")
            return True
        debug(f"Defender.repair_trap", f"Defender failed to repair trap with inventory: {self.inventory}.")
        return False

    def pick_item(self) -> bool:
        try:
            assert isinstance(self.followee, (Hammer, Logs, Food)), \
                "The defender can only pick up items that are one of a hammer, logs, or dropped food."
            assert self.followee in self.game.wave.dropped_hnls or self.followee in self.game.wave.dropped_food, \
                "The defender can only pick up items that are dropped."
        except AssertionError as e:
            debug("Defender.pick_item", f"{self} returned False due to the assertion: {str(e)}")
            return False

        if Y.EMPTY not in self.inventory:
            return False
        if isinstance(self.followee, Hammer):
            self.inventory[self.inventory.index(Y.EMPTY)] = Y.HAMMER
            self.game.wave.dropped_hnls.pop(self.game.wave.dropped_hnls.index(self.followee))
            self.game.wave.hnl_flags |= self.game.wave.SPAWN_HAMMER
        if isinstance(self.followee, Logs):
            self.inventory[self.inventory.index(Y.EMPTY)] = Y.LOGS
            self.game.wave.dropped_hnls.pop(self.game.wave.dropped_hnls.index(self.followee))
            if self.followee.location == E.LOGS_SPAWN:
                self.game.wave.hnl_flags |= self.game.wave.SPAWN_NEAR_LOGS
            if self.followee.location == E.FAR_LOGS_SPAWN:
                self.game.wave.hnl_flags |= self.game.wave.SPAWN_FAR_LOGS
        if isinstance(self.followee, Food):
            self.inventory[self.inventory.index(Y.EMPTY)] = str(self.followee.which)
            self.game.wave.dropped_food.pop(self.game.wave.dropped_food.index(self.followee))

        self.followee = None

    def click_drop_food(self, which: int, count: int = 1) -> bool:
        # This function is for usage by the Ai. For human usage, see click_drop_select_food.
        # We queue action because, afaik, dropping food drops it on the next tick rather than instantly.
        if str(which) not in self.inventory:
            return False
        self.drop_food(which, count)
        return True

    def click_drop_select_food(self, inventory_slots: List[int]) -> bool:
        # We queue action because, afaik, dropping food drops it on the next tick rather than instantly.
        self.drop_select_food(inventory_slots)
        return True

    def click_repair_trap(self, which: int = WEGameObject.EAST) -> bool:
        trap = self.game.wave.game_objects.traps[which]
        debug("Defender.click_repair_trap", f"Click repair trap on trap {which} -> {trap}.")
        if not self.location.renders_game_object(trap):
            debug("Defender.click_repair_trap", f"{self} cannot render the trap {trap}.")
            return False
        self.follow(trap)
        self.move(self.destination)
        debug("Defender.click_repair_trap",
              f"{self} followed the trap {trap}and has pathing queue: {Terrain.queue_info(self.pathing_queue)}.")
        return True

    def click_pick_item(self, item: DroppedItem) -> bool:
        if not self.location.renders_dropped_item(item):
            return False
        self.follow(item)
        self.move(self.destination)
        return True


class Healer(Player):
    INVENTORY_SPACE: int = 26  # Horn, vial.
    FOOD_PER_OVERSTOCK: int = 5

    TOFU, WORMS, MEAT = 0, 1, 2
    CALLS = ["tofu", "worms", "meat"]

    POISON_BUSY_WAIT: int = 1

    def __init__(self, game: Inspectable):
        super().__init__(E.HEALER_SPAWN, game)
        self.calls_with = Defender
        self.actions.extend([
            (PenanceHealer, self.use_poison_food, POST),
        ])

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
        assert isinstance(self.followee, PenanceHealer), "Cannot poison something that isn't a healer."
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

    def click_use_poison_food(self, which: int, healer: PenanceHealer) -> bool:
        if not self.location.renders_unit(healer):
            return False
        self.action_args = (which,)
        self.follow(healer)
        self.move(self.destination)
        return True


class Collector(Player):
    INVENTORY_SPACE: int = 26  # Horn, bag.
    BAG_SPACE: int = 8

    RED, GREEN, BLUE = 0, 1, 2
    CALLS = ["red", "green", "blue"]

    def __init__(self, game: Inspectable):
        super().__init__(E.COLLECTOR_SPAWN, game)
        self.calls_with = Attacker

    @staticmethod
    def access_letter() -> str:
        return "c"

    @property
    def choice_arg(self) -> List[Locatable]:
        rv = super().choice_arg
        rv.extend(self.game.wave.dropped_eggs)
        rv.extend(self.game.wave.game_objects.hoppers)
        return rv


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
