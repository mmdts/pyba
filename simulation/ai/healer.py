from typing import List, Tuple

from log import debug
from simulation.base.terrain import Inspectable, E, D
from simulation import player
from .ai import A, S, RuleBasedAi


class Healer(RuleBasedAi):
    # -1 means we have to exhaust a stock.
    # -2 means we have to exhaust a stock waiting for call change.
    # Any number above TICK_THRESHOLD means we have to wait till that specific tick.
    CODES: List[List[int]] = [
        # Wave 1
        # 1-1
        [-1] + [0] * 1 + [1] * 1,
        # Wave 2
        # 1-2-4
        [-1] + [0] * 2 + [1] * 2 + [2] * 4,
        # Wave 3
        # 1-6-1/2     -> 0-0-2/3
        [-1] + [0] * 1 + [1] * 6 + [2] * 4 + [0] * 1,
        # Wave 4 (reg stock, no alch)
        # 1-4-3       -> 0-0-0-7
        [-1] + [0] * 1 + [1] * 4 + [2] * 3 + [3] * 7,
        # Wave 5 (reg stock, no alch)
        # 1-5-2-1     -> 0-0-1-7
        [-1] + [0] * 1 + [1] * 5 + [2] * 1 + [3] * 1 + [2] * 1 +
               [4] * 3 + [3] * 1 + [4] * 4 + [3] * 1,
        # Wave 6 (reg stock)
        # 2-4-1-1   -> 0-0-1-1-6-9
        [-1] + [0] * 1 + [1] * 4 + [2] * 1 + [0] * 1 + [3] * 1 +
        [-1] + [2] * 1 + [4] * 2 + [5] * 5 + [3] * 1 + [4] * 4 + [5] * 4,
        # Wave 7 (reg stock)
        # 2-4-1-1   -> 1-1-1-1-3-1
        [-1] + [0] * 1 + [1] * 4 + [2] * 1 + [0] * 1 + [3] * 1 +
               [1] * 1 + [2] * 1 + [0] * 1 + [3] * 1 + [4] * 3 + [5] * 1 +
        [-1] + [6] * 7 + [5] * 3 + [6] * 5,
        # Wave 8
        # 1-5-1-1   -> 1-1-1-1-2-1-1
        [-1] + [0] * 1 + [1] * 4 + [2] * 1 + [1] * 1 + [3] * 1 +
               [4] * 1 + [0] * 1 + [2] * 1 + [3] * 1 + [1] * 2 + [4] * 1 + [5] * 1 +
        [-1] + [6] * 3 + [4] * 3 + [5] * 3 + [6] * 6,
        # Wave 9
        # 2-4-1-1   -> 1-2-1-1-1-1-1
        [-1] + [0] * 1 + [1] * 4 + [2] * 1 + [0] * 1 + [3] * 1 +
               [4] * 1 + [1] * 2 + [5] * 1 + [2] * 1 + [0] * 1 + [3] * 1 + [6] * 1 +
        [-1] + [7] * 3 + [4] * 1 + [5] * 2 + [6] * 3 + [7] * 3,
    ]

    # On 1-4, we don't need to restock anyway.
    # On 5, we don't overstock yet.
    #
    # On 6-9, we don't overstock first call yet.
    # On 6, we quad stock 2nd call.
    # On 7, we triple stock 3rd call.
    # On 8, we double stock 3rd call.
    # On 9, we single stock 3rd call.
    STOCKS: List[List[int]] = [[0]] * 4 + [[0]] + [[0, 4]] + [[0, 3]] + [[0, 2]] + [[0, 1]]

    TICK_THRESHOLD = 20

    def __init__(self, game: Inspectable):
        super().__init__(game)
        self.player: player.Healer = self.game.players.healer

        self.codes_i = -1  # The poison food usage / delay / stock in the code we're currently following.
        self.stock_i = -1  # The number of times we've overstocked in a specific stock session.
        self.stocks_i = -1  # The number of stock sessions we've had.
        self.codes = None
        self.stocks = None

    def start_wave(self) -> None:
        super().start_wave()
        self.codes = Healer.CODES[self.player.game.wave.number]
        self.stocks = Healer.STOCKS[self.player.game.wave.number]

    def smart_wait_for_tick(self) -> None:
        # While waiting, we always try to move close to the next healer we want to poison.
        if self.codes_i + 1 >= len(self.codes):
            return
        if self.codes[self.codes_i + 1] >= len(self.player.healers):
            self.target_location = E.PENANCE_HEALER_SPAWN + D.SE
            self.player.click_move(self.target_location)
            return
        self.target_location = self.player.get_closest_adjacent_square_to(self.player.healers[self.codes[self.codes_i + 1]])
        self.player.click_move(self.target_location)

    def do_new_action(self) -> int:
        if self.current_state == S.IDLE:
            self.current_state = S.FOLLOWING_CODE

        if self.current_state == S.STOCKING:
            self.stock_i += 1
            # If this is the last stock, we don't overstock, and we change state to S.PATHING.
            if self.stock_i == self.stocks[self.stocks_i]:
                debug("Healer.do_new_action", f"{self.player} using dispenser for the last time.")
                if self.stock_i == 0:
                    self.current_state = S.PATHING
                else:
                    self.current_state = S.FOLLOWING_CODE
                self.stock_i = -1
                self.player.click_use_dispenser()
                return A.USING_DISPENSER
            debug("Healer.do_new_action", f"{self.player} using dispenser.")
            self.player.click_use_dispenser(self.call)
            return A.USING_DISPENSER

        if self.current_state == S.PATHING:
            debug("Healer.do_new_action", f"{self.player} sliding.")
            self.target_location = E.SLIDE_TILE
            self.current_state = S.FOLLOWING_CODE
            self.player.click_move(self.target_location)
            return A.RUNNING_IDLE

        if self.current_state == S.FOLLOWING_CODE:
            debug("Healer.do_new_action", f"{self.player} following code.")
            self.current_state, rv = self.follow_code()
            return rv

        if self.current_state == S.SPAMMING_DOWN:
            debug("Healer.do_new_action", f"{self.player} spamming down.")
            healers_alive = [healer for healer in self.player.healers if healer.is_alive()]
            if len(healers_alive) == 0:
                return A.IDLE

            # TODO: BUILD We need to poison them more evenly.
            self.player.click_use_poison_food(self.call, healers_alive[0])
            return A.USING_POISON

        debug("Healer.do_new_action", f"{self.player} is idle. This should never happen.")
        return A.IDLE

    def follow_code(self) -> Tuple[int, int]:
        # Healer.follow_code is an implementation of RuleBasedAi.do_new_action, but returns a Tuple(state, action).
        # It's the caller's job to set self.current_state to state, then re-return the action.
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
        if self.codes[self.codes_i] < Healer.TICK_THRESHOLD:
            # If the healer hasn't spawned yet, we wait.
            if self.codes[self.codes_i] >= len(self.player.healers):
                self.codes_i -= 1  # We repeat this code when it's time.
                self.target_tick = \
                    (
                        (self.player.game.wave.relative_tick // Inspectable.CYCLE) + 1
                    ) * Inspectable.CYCLE + 1
                return S.FOLLOWING_CODE, A.WAITING_FOR_TICK
            # If we have poison left, we poison the healer.
            if str(self.call) in self.player.inventory:
                self.player.click_use_poison_food(self.call, self.player.healers[self.codes[self.codes_i]])
                return S.FOLLOWING_CODE, A.USING_POISON
            # If not, we wait till the call changes.
            self.target_tick = \
                (
                    (
                        (self.player.game.wave.relative_tick - 1) // Inspectable.CALL
                    ) + 1
                ) * Inspectable.CALL + 2
            debug("Healer.follow_code", f"{self.player} decided to wait till next call with "
                                        f"self.target_tick = {self.target_tick}.")
            return S.FOLLOWING_CODE, A.WAITING_FOR_TICK

        # If the code tells us to delay, we delay.
        self.target_tick = self.codes[self.codes_i]
        return S.FOLLOWING_CODE, A.WAITING_FOR_TICK
