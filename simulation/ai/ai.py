from abc import abstractmethod
from typing import Optional

from log import debug
from simulation.base.player import Player
from simulation.base.terrain import Inspectable, C


# AI Actions, mainly for rule based usage.
# Defender.click_drop_food, Player.click_destroy_item, Collector.click_empty_bag, Player.click_call,
# Attacker.click_change_weapon, Attacker.click_change_Style, Attacker.click_spec do not consume ticks.
# They therefore do not have actions in this class, as this class is mainly made to assist with idling through
# Player.click_idle while waiting for the action to finish.
class A:
    WAITING_FOR_TICK = 1
    RUNNING_IDLE = 2
    IDLE = 3
    USING_DISPENSER = 4
    PICKING_ITEM = 5
    LOADING_CANNON = 6
    FIRING_CANNON = 7
    ATTACKING = 8
    USING_POISON = 9
    REPAIRING_TRAP = 10
    STALLING = 11
    # More for staying beside ranger spawn area.


# AI States, mainly for rule based usage.
# This differs from actions in that it represents what the AI is currently trying to do strategy-wise.
# The next action is not based on the AI action (like waiting for an action to finish is), but rather,
# on the AI state.
class S:
    IDLE = 1
    PATHING = 2
    STOCKING = 3
    FOLLOWING_CODE = 4
    SPAMMING_DOWN = 5


# A general purpose AI.
# Both the rule based AI and the deep learning based AI should implement this.
class Ai:
    def __init__(self, game: Inspectable):
        self.game: Inspectable = game

        # AI can only interact with the game through self.player.click_*
        # TODO: BUILD Player.inspect_* and remove usage of game in AI. ||| and self.player.inspect_*.
        self.player: Optional[Player] = None

        self.wave_started = False

    @abstractmethod
    def __call__(self) -> None:
        # The game calls this method. This method should call self.player.click_* once at some point,
        # then return.
        raise NotImplementedError(f"{self.__class__.__name__} needs to implement Ai.__call__.")

    def start_wave(self) -> None:
        # The room calls this method to signal the AI to start acting..
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

        # Target location is used for forced movements like sliding and running west.
        self.target_location: Optional[C] = None

    def __call__(self) -> None:
        # Never override this method. Put all actions by implementing Player.do_new_action, Player.smart_wait_for_tick,
        # or overriding Player.wait_current_action.
        if not self.wave_started:
            # AI does not act if no wave is started.
            return

        if self.player.game.wave.relative_tick <= 1:
            # AI does not have superhuman speed.
            return

        self.call = self.player.correct_call

        if self.player.sent_call != self.player.required_call and self.player.game.wave.relative_tick % 2 == 0:
            # AI calls on even ticks if it hasn't sent a call. It realizes it messed up on even ticks too.
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
        if self.current_action == A.RUNNING_IDLE:
            return self.player.location == self.target_location

        if self.current_action == A.WAITING_FOR_TICK:
            condition = self.player.game.wave.relative_tick == self.target_tick

            self.smart_wait_for_tick()

            if condition:
                self.target_tick = -1

            return condition

        if self.player.is_idle():
            debug("Ai.wait_current_action", f"{self.player} waiting for the current action, "
                                            f"{self.current_action}, finished.")
        return self.player.is_idle()
