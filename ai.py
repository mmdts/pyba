from abc import abstractmethod
from typing import Optional

from player import Player
from terrain import Inspectable, E


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


class Ai:
    def __init__(self, game: Inspectable):
        self.game: Inspectable = game
        # AI can only interact with the game through self.player.click_*
        # TODO: BUILD Player.inspect_* and remove usage of game in AI. ||| and self.player.inspect_*.
        self.player: Optional[Player] = None

    def __call__(self, tick: int) -> bool:
        pass


# Actions are processed as follows:
# TODO: REFACTOR Finish this comment.
class RuleBasedAi(Ai):
    def __init__(self, game: Inspectable):
        super().__init__(game)
        self.current_action: int = A.IDLE

    def __call__(self, tick: int) -> bool:
        # AI calls on even ticks if it hasn't sent a call. It realizes it messed up on even ticks too.
        if self.player.sent_call != self.player.required_call and tick % 2 == 0:
            self.player.click_call()

        if self.current_action == A.IDLE:
            # Conditionally fires a Player.click_ action based on logic checks.
            self.current_action = self.do_new_action()
        else:
            # Conditionally waits out an Ai.current_action based on logic waits.
            # Returns the same action, the next action (in a 0-tick idle action sequence), or A.IDLE
            self.current_action = self.wait_current_action()

    @abstractmethod
    def do_new_action(self) -> int:
        raise NotImplementedError("Generic RuleBasedAi do not understand what action they're supposed to do."
                                  "Please make a role-specific Ai that inherits from RuleBasedAi and implement"
                                  "do_new_action on it.")

    def on(self, condition: bool) -> int:
        # Idles on the specified condition, otherwise continues doing current action.
        # For use in methods that return actions.
        return condition and A.IDLE or self.current_action

    def wait_current_action(self) -> int:
        # Please override this in the various roles of the RuleBasedAi, and call super().wait_current_action
        # at the very start.
        if self.current_action == A.RUNNING_WEST:
            return self.on(self.player.location.x < E.RUN_WEST_THRESHOLD.x)

        if self.current_action == A.RUNNING_FAR_WEST:
            return self.on(self.player.location.x < E.STAY_WEST_THRESHOLD.x)

        if self.current_action == A.USING_DISPENSER:
            return self.on(self.player.inventory + " TODO: FINISH THIS ")
            # TODO: CHECK how many ticks it takes to use dispenser from vid.


class RuleBasedCollector(RuleBasedAi):
    def __init__(self, game: Inspectable):
        super().__init__(game)
        self.player = self.game.players.collector
        self.current_action = A.RUNNING_WEST

# TODO: BUILD implement defender stepping recovery (advanced).
