from abc import abstractmethod
from typing import Optional, List, Tuple

from log import debug
from player import Player
from role_player import Healer
from terrain import Inspectable, E, D
from healer import Healer as PenanceHealer


# AI Actions, mainly for rule based usage.
# Defender.click_drop_food, Collector.click_destroy_egg, Collector.click_empty_bag, Player.click_call,
# Attacker.click_change_weapon, Attacker.click_change_Style, Attacker.click_spec do not consume ticks.
# They therefore do not have actions in this class, as this class is mainly made to assist with idling through
# Player.click_idle while waiting for the action to finish.
#
# The actions described above also do not reset Player.idle_duration.
class A:
    # Waits till west of a specific threshold.
    # Checks if already west.
    RUNNING_WEST = 1

    # Waits till west of a further threshold.
    # Check if already far west.
    RUNNING_FAR_WEST = 2

    # Waits till dispenser action finishes (inventory fills / eggs convert and player idle again).
    # Checks if dispenser action necessary (inventory lacks food / no red eggs).
    USING_DISPENSER = 3

    # Waits till egg / hammer / logs no longer exists in dropped items.
    # Check if eggs of specified color / hammer / logs are within a specific distance.
    PICKING_ITEM = 4

    # Waits till cannon has eggs inside it.
    # Checks if no eggs to load / cannon already full reds.
    LOADING_CANNON = 5

    # Waits till firing action finishes (cannon fired and player idle again).
    # Checks if cannon empty, and fires on penance in order (healers > runners > rangers > fighters).
    FIRING_CANNON = 6

    # Waits till healer has player targeted.
    # Checks if healers dead, all healers already lured / no runners alive.
    LURING = 7

    # Does not wait.
    # Checks if there are combat npcs alive.
    ATTACKING_PENANCE = 8

    # Waits until player-based poison damage is dealt to the healer.
    # While there are healers alive.
    # Checks if the healer is alive and within range.
    USING_POISON = 9

    # Waits till trap charges restore (after repair animation)
    # Checks if there are runners alive.
    REPAIRING_TRAP = 10

    # Waits till stall finishes.
    # Checks if some penance haven't spawned yet.
    STALLING = 11

    # Does not wait or check.
    IDLE = 12

    # Waits till destination is reached.
    RUNNING_IDLE = 13

    # Waits till at trap tile.
    # Check if already at trap tile.
    RUNNING_TO_TRAP = 14

    # Waits till at slide tile.
    # Check if already at a zone from which we can poison healers.
    RUNNING_TO_SLIDE = 15

    # Waits till call change.
    WAITING_FOR_TICK = 16

    # More for staying beside ranger spawn area.


class S:
    IDLE = 1
    STOCKING = 2
    PATHING = 3
    FOLLOWING_CODE = 4
    SPAMMING_DOWN = 5


class Ai:
    def __init__(self, game: Inspectable):
        self.game: Inspectable = game
        # AI can only interact with the game through self.player.click_*
        # TODO: BUILD Player.inspect_* and remove usage of game in AI. ||| and self.player.inspect_*.
        self.player: Optional[Player] = None
        self.wave_started = False

    @abstractmethod
    def __call__(self):
        raise NotImplementedError(f"{self.__class__.__name__} needs to implement Ai.__call__.")

    def start_wave(self) -> None:
        self.wave_started = True


class RuleBasedAi(Ai):
    def __init__(self, game: Inspectable):
        super().__init__(game)
        self.call: Optional[int] = None

        # Decisions are based on current_state, and are taken when current_action is idle.
        self.current_state: int = S.IDLE  # A state is persistent, and outlasts multiple actions.
        self.current_action: int = A.IDLE  # An action is a click.

        # TODO: BUILD until we implement call guessing / waiting mechanics, we'll use correct_call.
        self.target_tick: int = -1

    def __call__(self) -> None:
        if not self.wave_started:
            return

        self.call = self.player.correct_call
        # AI calls on even ticks if it hasn't sent a call. It realizes it messed up on even ticks too.
        if self.player.sent_call != self.player.required_call and self.player.game.wave.relative_tick % 2 == 0:
            self.player.click_call()

        if self.current_action == A.IDLE or self.wait_current_action():
            # Conditionally fires a Player.click_ action based on logic checks, then returns self.current_action.
            self.current_action = self.do_new_action()

    @abstractmethod
    def do_new_action(self) -> int:
        raise NotImplementedError("Generic RuleBasedAi do not understand what action they're supposed to do."
                                  "Please make a role-specific Ai that inherits from RuleBasedAi and implement"
                                  "do_new_action on it.")

    @abstractmethod
    def smart_wait_for_tick(self) -> int:
        raise NotImplementedError(f"{self.__class__.__name__} needs to implement RuleBasedAi.smart_wait_for_tick.")

    def wait_current_action(self) -> bool:
        # Please override this in the various roles of the RuleBasedAi, and call super().wait_current_action
        # at the very start.
        if self.current_action == A.RUNNING_WEST:
            return self.player.location.x < E.RUN_WEST_THRESHOLD.x

        if self.current_action == A.RUNNING_FAR_WEST:
            return self.player.location.x < E.STAY_WEST_THRESHOLD.x

        if self.current_action == A.RUNNING_TO_SLIDE:
            return self.player.location == E.SLIDE_TILE

        if self.current_action == A.WAITING_FOR_TICK:
            condition = self.player.game.wave.relative_tick == self.target_tick

            self.smart_wait_for_tick()

            if condition:
                self.target_tick = -1

            return condition

        return self.player.is_idle()


class RuleBasedHealer(RuleBasedAi):
    # -1 means we have to exhaust a stock.
    # -2 means we have to exhaust a stock waiting for call change.
    # Any number above TICK_THRESHOLD means we have to wait till that specific tick.
    CODES: List[List[int]] = [
        # 1-1
        [-1] + [0] * 1 + [1] * 1,
        # 1-2-4
        [-1] + [0] * 2 + [1] * 2 + [2] * 4,
        # 1-6-1/2     -> 0-0-2/3
        [-1] + [0] * 1 + [1] * 6 + [2] * 4 + [0] * 1,
        # 1-4-3       -> 0-0-0-7
        [-1] + [0] * 1 + [1] * 4 + [2] * 3 + [3] * 7,
        # 1-5-2-1     -> 0-0-1-7
        [-1] + [0] * 1 + [1] * 5 + [2] * 1 + [3] * 1 + [2] * 1 +
               [4] * 3 + [3] * 1 + [4] * 4 + [3] * 1,
        # 2-4-1/2-1   -> 0-0-1-1-6-9
        [-1] + [0] * 1 + [1] * 4 + [2] * 1 + [0] * 1 + [3] * 1 +
        [-1] + [2] * 1 + [4] * 2 + [5] * 5 + [3] * 1 + [4] * 4 + [5] * 4
    ]

    # On 1-4, we don't need to restock anyway.
    # On 5, we don't overstock yet.
    # On 6-9, we don't overstock first call yet. We triple overstock when restocking.
    STOCKS: List[List[int]] = [[0]] * 4 + [[0]] + [[0, 4]] + [[0, 3]] * 3

    TICK_THRESHOLD = 20

    def __init__(self, game: Inspectable):
        super().__init__(game)
        self.player: Healer = self.game.players.healer

        self.healers: List[PenanceHealer] = []
        self.codes_i = -1  # The poison food usage / delay / stock in the code we're currently following.
        self.stock_i = -1  # The number of times we've overstocked in a specific stock session.
        self.stocks_i = -1  # The number of stock sessions we've had.
        self.codes = None
        self.stocks = None

    def start_wave(self) -> None:
        super().start_wave()
        self.codes = RuleBasedHealer.CODES[self.player.game.wave.number]
        self.stocks = RuleBasedHealer.STOCKS[self.player.game.wave.number]

    def smart_wait_for_tick(self) -> None:
        # While waiting, we always try to move close to the next healer we want to poison.
        if self.codes_i + 1 >= len(self.codes):
            return
        if self.codes[self.codes_i + 1] >= len(self.healers):
            self.player.click_move(E.PENANCE_HEALER_SPAWN + D.SE)
            return
        self.player.click_move(self.healers[self.codes[self.codes_i + 1]].location)

    def do_new_action(self) -> int:
        if self.current_state == S.IDLE:
            self.current_state = S.FOLLOWING_CODE

        if self.current_state == S.STOCKING:
            self.stock_i += 1
            # If this is the last stock, we don't overstock, and we change state to S.PATHING.
            if self.stock_i == self.stocks[self.stocks_i]:
                self.player.click_use_dispenser()
                if self.stock_i == 0:
                    self.current_state = S.PATHING
                else:
                    self.current_state = S.FOLLOWING_CODE
                self.stock_i = -1
            else:
                self.player.click_use_dispenser(self.call)
            return A.USING_DISPENSER

        if self.current_state == S.PATHING:
            self.player.click_move(E.SLIDE_TILE)
            self.current_state = S.FOLLOWING_CODE
            return A.RUNNING_TO_SLIDE

        if self.current_state == S.FOLLOWING_CODE:
            self.current_state, rv = self.follow_code()
            return rv

        if self.current_state == S.SPAMMING_DOWN:
            healers_alive = [healer for healer in self.healers if healer.is_alive()]
            if len(healers_alive) == 0:
                return A.IDLE

            # TODO: BUILD We need to poison them more evenly.
            self.player.click_use_poison_food(self.call, healers_alive[0])
            return A.USING_POISON

        return A.IDLE

    def follow_code(self) -> Tuple[int, int]:
        self.codes_i += 1

        # If we have finished all the codes, we spam down.
        if self.codes_i >= len(self.codes):
            return S.SPAMMING_DOWN, A.IDLE

        # If the code tells us to restock, we restock.
        if self.codes[self.codes_i] == -1:
            self.stocks_i += 1
            self.player.click_destroy_items([25, 26, 27] * 9)
            return S.STOCKING, A.IDLE

        # If the code tells us to poison a healer, we see if we have poison left.
        if self.codes[self.codes_i] < RuleBasedHealer.TICK_THRESHOLD:
            # If the healer hasn't spawned yet, we wait.
            if self.codes[self.codes_i] >= len(self.healers):
                self.codes_i -= 1  # We repeat this code when it's time.
                self.target_tick = \
                    (
                        (self.player.game.wave.relative_tick // Inspectable.CYCLE) + 1
                    ) * Inspectable.CYCLE + 1
                return S.FOLLOWING_CODE, A.WAITING_FOR_TICK
            # If we have poison left, we poison the healer.
            if str(self.call) in self.player.inventory:
                self.player.click_use_poison_food(self.call, self.healers[self.codes[self.codes_i]])
                return S.FOLLOWING_CODE, A.USING_POISON
            # If not, we wait till the call changes.
            self.target_tick = \
                (
                    (
                        (self.player.game.wave.relative_tick - 1) // Inspectable.CALL
                    ) + 1
                ) * Inspectable.CALL + 2
            debug("RuleBasedHealer.follow_code", f"{self.player} decided to wait till next call with "
                                                 f"self.target_tick = {self.target_tick}.")
            return S.FOLLOWING_CODE, A.WAITING_FOR_TICK

        # If the code tells us to delay, we delay.
        self.target_tick = self.codes[self.codes_i]
        return S.FOLLOWING_CODE, A.WAITING_FOR_TICK


class RuleBasedCollector(RuleBasedAi):
    def __init__(self, game: Inspectable):
        super().__init__(game)
        self.player = self.game.players.collector
        self.current_action = A.RUNNING_WEST

# TODO: BUILD implement defender stepping recovery (advanced).
