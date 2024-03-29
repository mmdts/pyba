from random import random
from typing import List, Dict, Type, Union, Optional

from log import debug, game_print
from simulation.ai import Ai
from simulation.base.dispenser import AttackerDispenser, DefenderDispenser, HealerDispenser, CollectorDispenser
from simulation.base.game_object import GameObjects
from simulation.base.dropped_item import Food, Egg, Logs, Hammer
from simulation.base.terrain import Inspectable, Terrain, F, C
from simulation.base.player import Player
from simulation.player.attacker import Attacker
from .penance import Penance
from .players import Players


class Wave:
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
        self.game.wave_number = self.number
        self.penance: Penance = Penance(self.game)
        self.dispensers = {
            "a": AttackerDispenser(self.game),
            "d": DefenderDispenser(self.game),
            "h": HealerDispenser(self.game),
            "c": CollectorDispenser(self.game),
        }

        # Currently, these are three different lists instead of a list of type List[DroppedItem] to ease processing.
        self.dropped_food: List[Food] = []
        self.dropped_eggs: List[Egg] = []
        self.dropped_hnls: List[Union[Hammer, Logs]] = [  # The term hnl will be used to indicate hammer and logs.
            Hammer(self.game), Logs(Logs.NEAR, self.game), Logs(Logs.FAR, self.game)
        ]
        self.hnl_flags = 0b000

        self.game_objects: GameObjects = GameObjects(self.game)
        self.start_tick: int = tick
        self.correct_calls: Dict[str, Optional[int]] = {
            "a": None, "c": None, "d": None, "h": None,
        }
        self.calls: Dict[str, Optional[int]] = {  # The keys are accessed in Player.inspect_call,
            "a": None, "c": None, "d": None, "h": None,  # be careful when changing.
        }

    def __call__(self) -> bool:
        # Wave starts on tick 0.
        # All ticks after this point, including the ones passed to the penance are normalized
        # with respect to the wave start through the use of self.relative_tick.
        #
        # Player code also relies on self.game.wave.relative_tick when making decisions.
        if self.relative_tick == Inspectable.WAVE and not self.end_flag:
            debug("Wave.__call__", "The wave ended unexpectedly due to a timeout.")
            return False

        # Handle wave end.
        if self.end_flag:
            return False

        # Call changes.
        if self.relative_tick % Inspectable.CALL == 1:
            self.game.stall((self.change_call, (), {}))

        # If all the penance are dead and we're on a penance cycle.
        if not self.penance():
            self.game.stall((self.end, (), {}))

        if self.relative_tick % Inspectable.CYCLE == 0:
            # If we need to spawn hammer or logs, we do.
            if self.hnl_flags & Wave.SPAWN_HAMMER:
                self.dropped_hnls.append(Hammer(self.game))
            if self.hnl_flags & Wave.SPAWN_NEAR_LOGS:
                self.dropped_hnls.append(Logs(Logs.NEAR, self.game))
            if self.hnl_flags & Wave.SPAWN_FAR_LOGS:
                self.dropped_hnls.append(Logs(Logs.FAR, self.game))

            self.hnl_flags = 0b000

        return True

    @property
    def relative_tick(self) -> int:
        return self.game.tick - self.start_tick

    def print(self, *args, **kwargs) -> None:
        game_print("Wave.print", f"Wave {self.number}:", *args, **kwargs)
        self.game.text_payload.append(
            " ".join([str(arg) for arg in (f"WAVE {self.number}::", *args)])
        )

    def change_call(self) -> None:
        self.calls = {
            "a": None, "c": None, "d": None, "h": None,
        }

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
        self.print(f"Call {self.relative_tick // Inspectable.CALL} ({Terrain.tick_to_string(self.relative_tick)}).")

    def end(self) -> None:
        self.end_flag = True
        self.print(f"Wave ended ({Terrain.tick_to_string(self.relative_tick)}).")


class Game:
    def __init__(self):
        self.inspectable: Inspectable = Inspectable(self)
        self.players: Optional[Players] = None
        self.original_ai: Dict[str, Type[Ai]] = {}
        self.ai: Dict[str, Union[Type[Ai], Ai]] = {}
        self.tick: int = -1
        self.wave: Optional[Wave] = None

        self.runner_movements: List[List[C]] = []

        self.block_map: List[str] = Terrain.new()

    def start_new_wave(self, wave_number: int, runner_movements: List[List[C]]) -> None:
        self.set_new_players(self.original_ai)  # Keeps AI dictionary unmodified, resets players.
        assert 0 <= wave_number < 10, "The wave (0-indexed) should be between 0 and 9."
        assert wave_number != 9, "Wave 10 is not implemented yet in this project."
        self.tick = -1  # Tick 0 of wave is tick 0 of game is the tick at the first call of wave and game.
        self.wave = Wave(wave_number, self.tick + 1, self.inspectable)  # self.wave.start_tick is 0.

        self.runner_movements = runner_movements

        self.wave.penance.set_runner_movements(runner_movements.copy())

        for role in self.ai:
            ai = self.ai[role]
            if isinstance(ai, Ai):
                ai.start_wave()

    def set_new_players(self, ai: Dict[str, Type[Ai]]) -> None:
        # Garbage collect the old locatables.
        self.inspectable.uuids = []
        self.inspectable.locatables = []
        self.original_ai = ai
        self.block_map: List[str] = Terrain.new()

        # Create new players.
        self.players: Players = Players(self.inspectable)
        for role in ai:
            self.ai[role] = ai[role](self.inspectable)

        # Reset wave. This method is usually called by Game.start_new_wave, which then creates a new wave too.
        self.wave = None

    def __call__(self) -> bool:
        assert self.wave is not None, "Please call start_new_wave before processing the game loop."
        assert self.players is not None, "Please call set_new_players before processing the game loop."

        # Process actions related to the the AI actions.
        for role in self.ai:
            if self.ai[role] is not None:
                self.ai[role].__call__()

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
        if not self.wave():
            return False

        # Process actions related to the players, and return if a player died (currently impossible).
        # Player actions NEED to be done after Npc actions. The order is important! This matters for things like
        # manual Healer poisoning (which is a Player action) causing reserve healers to spawn a tick later than
        # automatic Healer poisoning (which is an Npc action).
        if not self.players():
            return False

        return True

    def render_map(self, _print: bool = False, players_only: bool = False) -> List[str]:
        tmp = Terrain.new()

        if self.players is not None:
            for key, player in self.players:
                Terrain.set_letter(player.location, F[key.upper()], tmp)

        # Npcs render above Players to allow for interacting with said Npc. Never does a player need to interact
        # with another under the current assumptions (no wave 10, no healing).
        if self.wave is not None and not players_only:
            for key, species in self.wave.penance:
                for npc in species:
                    Terrain.set_letter(npc.location, F[key.lower()], tmp)

        if _print:
            Terrain.print(tmp)
            game_print("Game.render_map", self.wave.relative_tick)

        return tmp

    def print_runners(self) -> None:
        game_print("Game.print_runners", *(f"    {runner}\n" for runner in self.wave.penance.runners))
