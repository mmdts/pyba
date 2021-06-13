from random import random
from typing import List, Dict, Type, Union, Optional

from dispenser import AttackerDispenser, DefenderDispenser, HealerDispenser, CollectorDispenser
from game_object import GameObjects
from log import debug, game_print
from dropped_item import Food, Egg, Logs, Hammer
from penance import Penance
from player import Player
from players import Players
from role_player import Attacker
from terrain import Inspectable, Terrain, F, C


class Wave:
    POISON_CYCLE: int = 5  # The poison cycle.
    CYCLE: int = 10  # The penance cycle
    CALL: int = 5 * CYCLE  # A call is 5 cycles
    WAVE: int = 6 * CALL  # We force a wave to end on 6 calls to prevent an infinite loop if the players just idle.

    SPAWN_HAMMER = 0b001  # For hnl_flags comparison of what we need to spawn.
    SPAWN_NEAR_LOGS = 0b010
    SPAWN_FAR_LOGS = 0b100

    # Only click_ methods AND inspect_ methods AND methods used exclusively by them (helpers)
    # AND __init__ AND __call__ should use the self.game property!!
    # All other methods should be passed the parameters they need explicitly!
    def __init__(self, wave_number: int, tick: int, game: Inspectable):
        self.end_flag = False
        self.game: Inspectable = game
        self.number: int = wave_number
        self.penance: Penance = Penance(wave_number, self.game)
        self.dispensers = {
            "a": AttackerDispenser(),
            "d": DefenderDispenser(),
            "h": HealerDispenser(),
            "c": CollectorDispenser(),
        }

        # Currently, these are three different lists instead of a list of type List[DroppedItem] to ease processing.
        self.dropped_food: List[Food] = []
        self.dropped_eggs: List[Egg] = []
        self.dropped_hnls: List[Union[Hammer, Logs]] = [  # The term hnl will be used to indicate hammer and logs.
            # TODO: BUILD handle logs and hammer respawns.
            Hammer(), Logs(Logs.NEAR), Logs(Logs.FAR)
        ]
        self.hnl_flags = 0b000

        self.game_objects: GameObjects = GameObjects()
        self.start_tick: int = tick
        self.correct_calls: Dict[str, Optional[int]] = {
            "a": None, "c": None, "d": None, "h": None,
        }
        self.calls: Dict[str, Optional[int]] = {  # The keys are accessed in Player.inspect_call,
            "a": None, "c": None, "d": None, "h": None,  # be careful when changing.
        }

    def __call__(self, tick: int) -> bool:
        # Wave starts on tick 0.
        tick -= self.start_tick  # All ticks after this point, including the ones passed to the penance are normalized
        if tick == Wave.WAVE and not self.end_flag:  # with respect to the wave start. The ones passed to Players,
            debug("Wave.__call__", "The wave ended unexpectedly due to a timeout.")  # however, are not.
            return False

        # Handle wave end.
        if self.end_flag:
            return False

        # Call changes.
        if tick % Wave.CALL == 1:
            self.game.stall(self.change_call)

        # If all the penance are dead and we're on a penance cycle.
        if not self.penance(tick):
            self.game.stall(self.end)

        if tick % Wave.CYCLE == 0:
            # If we need to spawn hammer or logs, we do.
            if self.hnl_flags & Wave.SPAWN_HAMMER:
                self.dropped_hnls.append(Hammer())
            if self.hnl_flags & Wave.SPAWN_NEAR_LOGS:
                self.dropped_hnls.append(Logs(Logs.NEAR))
            if self.hnl_flags & Wave.SPAWN_FAR_LOGS:
                self.dropped_hnls.append(Logs(Logs.FAR))

            self.hnl_flags = 0b000

        return True

    @property
    def relative_tick(self) -> int:
        return self.game.tick - self.start_tick

    def print(self, *args, **kwargs):
        game_print("Wave.print", f"Wave {self.number}:", *args, **kwargs)
        self.game.text_payload.append(
            " ".join([str(arg) for arg in (f"WAVE {self.number}::", *args)])
        )

    def change_call(self):
        for key in self.correct_calls:
            if self.correct_calls[key] is None:
                if key == "a":
                    call = int(random() * Attacker.CALL_COUNT)
                else:
                    call = int(random() * Player.CALL_COUNT)
            else:
                if key == "a":
                    call = int(random() * (Attacker.CALL_COUNT - 1))
                else:
                    call = int(random() * (Player.CALL_COUNT - 1))
                if call >= self.correct_calls[key]:
                    call += 1
            self.correct_calls[key] = call
        self.print(f"Call {self.relative_tick // Wave.CALL} ({Terrain.tick_to_string(self.relative_tick)}).")

    def end(self):
        self.end_flag = True
        self.print(f"Wave ended ({Terrain.tick_to_string(self.relative_tick)}).")


class Game:
    def __init__(self):
        self.inspectable: Inspectable = Inspectable(self)
        self.players: Optional[Players] = None
        self.ai: Dict[str, Optional[Type]] = {"a": None, "s": None, "d": None, "h": None, "c": None}
        self.tick: int = -1
        self.wave: Optional[Wave] = None

        self.wave_number: int = -1
        self.runner_movements: List[List[C]] = []

    def start_new_wave(self, wave_number: int, runner_movements: List[List[C]]) -> None:
        self.set_new_players({})  # Keeps AI dictionary unmodified, resets players.
        assert 0 <= wave_number < 10, "The wave (0-indexed) should be between 0 and 9."
        assert wave_number != 9, "Wave 10 is not implemented yet in this project."
        self.tick = -1  # Tick 0 of wave is tick 0 of game is the tick at the first call of wave and game.
        self.wave = Wave(wave_number, self.tick + 1, self.inspectable)  # self.wave.start_tick is 0.

        self.runner_movements = runner_movements
        self.wave_number = wave_number

        self.wave.penance.set_runner_movements(runner_movements.copy())

    def set_new_players(self, ai: Dict[str, Type]) -> None:
        self.players: Players = Players(self.inspectable)
        for role in ai:
            self.ai[role] = ai[role].__init__(self.inspectable)

        self.wave = None

    def __call__(self) -> bool:
        assert self.wave is not None, "Please call start_new_wave before processing the game loop."
        assert self.players is not None, "Please call set_new_players before processing the game loop."

        # Call this in main as: while game(): pass;
        # Increment tick.
        self.tick += 1

        # Process actions related to the wave, and return if the wave ended.
        # While it is generally understood that in the original Runescape, wave actions are not a "separate" process
        # to be run in game cycle, but rather an extension on scroller, and if we were to adhere to original Runescape
        # coding structure, should be part of the `if not self.players(self.tick):` part for MainAttacker, here, our
        # purpose is not to be consistent with the original Runescape coding decisions, which make sense for the
        # original Runescape coding circumstances (weak server machines, hundreds of players per server, lots of
        # minigames / other content, individual checking is infeasible), but instead, to implement coding structure
        # that is coherent, and *logically* consistent with how the original Runescape acts, yet works fine on our
        # circumstances (strong machines, just five players and one minigame, very fast execution required).
        if not self.wave(self.tick):
            return False

        # Process actions related to the the AI actions.
        for role in self.ai:
            if self.ai[role] is not None:
                if not self.ai[role].__call__(self.tick):
                    return False

        # Process actions related to the players, and return if a player died (currently impossible).
        # Player actions NEED to be done after Npc actions. The order is important! This matters for things like
        # manual Healer poisoning (which is a Player action) causing reserve healers to spawn a tick later than
        # automatic Healer poisoning (which is an Npc action).
        if not self.players(self.tick):
            return False

        return True

    def print_map(self, ret: bool = False) -> Optional[List[str]]:
        tmp = Terrain.new()
        for key, player in self.players:
            Terrain.set_letter(player.location, F[key.upper()], tmp)

        # Npcs render above Players to allow for interacting with said Npc. Never does a player need to interact
        # with another under the current assumptions (no wave 10, no healing).
        for key, species in self.wave.penance:
            for npc in species:
                Terrain.set_letter(npc.location, F[key.lower()], tmp)

        if ret:
            return tmp
        Terrain.print(tmp)
        game_print("Game.print_map", self.wave.relative_tick)

    @property
    def original_map(self) -> List[str]:
        return Terrain.new()

    def print_runners(self):
        game_print("Game.print_runners", *(f"    {str(runner)}\n" for runner in self.wave.penance.runners))

    def bass(self):
        # The one true pass that rules them all.
        pass
