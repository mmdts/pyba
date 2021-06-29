from typing import List, Optional

from log import debug

from simulation.base.dropped_item import Food, DroppedItem, Logs, Hammer
from simulation.base.game_object import Trap, WEGameObject
from simulation.base.terrain import E, Inspectable, Y, Terrain, Locatable
from simulation.base.player import Player
from simulation.base.unit import Unit


class Defender(Player):
    CALLS = ["tofu", "crackers", "worms"]
    TRAP_BUSY_WAIT: int = 5

    def __init__(self, game: Inspectable):
        super().__init__(E.DEFENDER_SPAWN, game)
        self.trap: Optional[Trap] = None
        self.actions.extend([
            (Trap, self.repair_trap, Unit.PRE),
        ])

        # This array persists food even after it perishes.
        self.food: List[Food] = []

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
            if str(food_type) not in self.inventory:
                break

            new_food = Food(
                self.location,
                food_type,
                food_type == self.correct_call,
                self.game
            )
            self.game.wave.dropped_food.append(new_food)
            self.food.append(new_food)
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
