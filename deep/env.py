from typing import Dict, List, Tuple, Optional

import torch

from log import debug
from simulation.base.dropped_item import Hammer, Logs
from simulation.base.player import Player
from simulation.base.terrain import Inspectable, E
from simulation.penance import Healer
from simulation import Room, EventHandler, player
from .constants import State, DESTROY_PROBABILITY, EXPECTED_SIZES, Masks
from .emit import make_build_emittable_function_for_device


class Env:
    # click_destroy_items and click_drop_food are instant.
    # click_select_call is not handled here.
    ACTIONS: List[str] = [
        "click_move",
        "click_use_dispenser",
        "click_pick_item",
        "click_repair_trap",
        "click_use_poison_food",
        "click_use_cannon",
        "click_fire_egg",
        "special_pick_hammer",
        "special_pick_logs",
    ]

    DISPENSER_OPTIONS: List[int] = [0, 1, 2, 5]

    # The following constants are used for state worth and reward calculation.

    CYCLE_LATENESS_FACTOR = 0.2
    WAVE_LATENESS_FACTOR = 0.05
    WAVE_LATENESS_RATIO = 1.007

    SUPPOSED_END_TICKS: List[int] = [50, 70, 80, 80, 90, 100, 120, 130, 150]

    SUPPOSED_HEALER_RESERVES_PER_CYCLE: List[List[int]] = [
        [2, 1, 0],
        [3, 2, 1, 0],
        [3, 2, 1, 1, 0],
        [4, 3, 2, 1, 0],
        [5, 4, 3, 2, 1, 0],
        [6, 5, 4, 3, 2, 2, 2, 1, 0],
        [7, 6, 5, 4, 3, 3, 3, 2, 1, 0],
        [7, 6, 5, 4, 3, 2, 2, 1, 0],
        [8, 7, 6, 5, 4, 3, 2, 2, 1, 0],
    ]

    # This is an environment similar to OpenAI's Gym environments.
    # It has a reset and a step function.
    # It replaces the "interface" file that was previously present.
    def __init__(self, role, device):
        self.role = role
        self.device = device
        self.room = Room(mode=Room.PAUSE)
        self.room.accept_player_connection(role, role)
        self.room.extra = self
        self.last_worth: Optional[torch.Tensor] = None

        setattr(self.room, "emit_state",
                make_build_emittable_function_for_device(game=self.room.game, role=self.role, device=self.device))

    @property
    def player(self) -> Player:
        return self.room.game.players[self.role]

    def preprocess(self, state: State, masks: State) -> Tuple[State, State]:
        if state is None:
            return None, None

        for key in state:
            if len(EXPECTED_SIZES[key]) < 2:  # Wave, tick, trap, inventory.
                continue
            if state[key].size().numel() == 0:
                # No elements exist, we make them.
                state[key] = torch.zeros(EXPECTED_SIZES[key], device=self.device)
            if state[key].size()[0] < EXPECTED_SIZES[key][0]:
                # Less elements are observed than the required amount, we make the rest.
                padding = torch.zeros(
                    (EXPECTED_SIZES[key][0] - state[key].size()[0], EXPECTED_SIZES[key][1]), device=self.device)
                state[key] = torch.cat((state[key], padding))

        for key in state:
            state[key] = torch.unsqueeze(state[key], 0)

        return state, masks

    def calculate_state_worth(self) -> torch.Tensor:
        # TODO: Give actor points for dropping food in runner's sight if there is food at trap.
        #
        # For now, we just want it to know how to defend.
        # Later, we'll give it less points for placing food at trap, etc.,
        # and bigger penalty for later end times,
        # to encourage learning new defender strategies and helping healer more.
        is_defender = self.role == "d"
        distance_factor = is_defender and 0.25 or 0.75
        wave = self.room.game.wave
        distance_target = is_defender and wave.penance.runners or wave.penance.healers

        state_worth = torch.zeros((1, 1), device=self.device)

        if self.role == "d":
            # Gain points for food beside trap.
            for food in wave.dropped_food:
                if food.location.chebyshev_to(E.TRAP) <= 1:
                    state_worth += 1
                if food.location.chebyshev_to(E.RUNNER_SPAWN) <= 6:
                    state_worth += 0.5

            # Gain points when a runner dies.
            state_worth -= 10 * len(wave.penance.runners)

            # Gain points when a reserve spawns (only 3 points since you lose 10 on the runner spawning).
            state_worth -= 13 * wave.penance.spawns["d"][1]

            # Lose points for every runner that's late to spawn.
            state_worth -= 2 * (wave.penance.spawns["d"][1] + wave.relative_tick // Inspectable.CYCLE)

            # Lose points for when a runner random moves.
            state_worth -= 4 * wave.penance.runner_random_moves

        # Gain points for being surrounded by runners/healers.
        average_of_distances = torch.zeros((1, 1), device=self.device)
        average_of_distances += E.TRAP.chebyshev_to(self.player.location)
        for runner in distance_target:
            average_of_distances += runner.location.chebyshev_to(self.player.location)

        average_of_distances /= len(distance_target) + 1
        state_worth += distance_factor * average_of_distances

        # Gain points when a healer dies (lose unconditionally on spawn).
        state_worth -= 10 * len(wave.penance.healers)

        # Gain points when a reserve spawns (only 3 points since you lose 10 on the healer spawning).
        state_worth -= 13 * wave.penance.spawns["h"][1]

        # Gain points when a healer takes damage.
        for healer in wave.penance.healers:
            if healer.hitpoints > 0 and healer.is_alive():
                state_worth -= 0.25 * healer.hitpoints

        # Add reserve healers to the state's worth to normalize healer hp sum increasing when healers spawn.
        state_worth -= wave.penance.spawns["h"][1] * Healer.HITPOINTS[wave.number] / 4

        # Gain points when finishing off species.
        state_worth += 10 * wave.penance.species_extinct

        # Lose points when runners escape.
        # Actor perceives this as not gaining any points when that runner "dies",
        # then suddenly losing a lot of points when it spawns again.
        state_worth -= 10 * wave.penance.runner_escapes

        # Gain points for when a healer is not moving.
        state_worth += wave.penance.healer_static_ticks

        # Lose points exponentially for every tick after the supposed end tick.
        # Since the sole purpose of this is to finish fast.
        state_worth -= 0.1 * 1.007 ** max(wave.relative_tick - Env.SUPPOSED_END_TICKS[wave.number], 0)

        # Lose points for every healer that's late to spawn.
        supposed_spawns = 0
        if wave.relative_tick // Inspectable.CYCLE in Env.SUPPOSED_HEALER_RESERVES_PER_CYCLE[wave.number]:
            supposed_spawns = \
                Env.SUPPOSED_HEALER_RESERVES_PER_CYCLE[wave.number][wave.relative_tick // Inspectable.CYCLE]
        state_worth -= 2 * max(wave.penance.spawns["h"][1] - supposed_spawns, 0)

        return state_worth

    def reset(self) -> Tuple[State, Masks]:
        EventHandler.handle("new_wave", [torch.randint(low=1, high=10, size=(1,)).item(), ""], self.room, self.role)
        room_rv = self.room()
        if room_rv is not None:
            rv = self.preprocess(*room_rv)
        else:
            rv = None, None
        self.last_worth = self.calculate_state_worth()
        return rv

    def step(self, p_actor_multinomial: Dict, picked_action_multinomial: torch.Tensor) \
            -> Tuple[State, State, torch.Tensor, bool, int]:
        # This will raise errors if something goes wrong during masking, as checking that keys exist
        # inside the final p_actor_multinomial does not happen for anything but drop_count and destroy_slots.
        #
        # This is an intended effect and is therefore left as is.
        assert self.last_worth is not None, "You need to reset the environment once after initializing it."
        assert self.player is not None, "The game needs to be initialized properly before the environment steps."

        action = Env.ACTIONS[picked_action_multinomial.cpu().item()]
        initial_action = action
        args = []

        # Loss/gain on reward based on action, and not on state worth.
        reward_delta = 0

        # Calculate the action that gets passed to the EventHandler.
        if action == "click_move":
            movement = p_actor_multinomial["move"].cpu().item()
            args = [
                self.player.location.x + movement // Player.ACTION_DISTANCE - Player.ACTION_DISTANCE // 2,
                self.player.location.y + (movement % Player.ACTION_DISTANCE) - Player.ACTION_DISTANCE // 2,
            ]

        if action == "click_use_dispenser" and isinstance(self.player, player.Healer):
            args = [Env.DISPENSER_OPTIONS[p_actor_multinomial["dispenser_option"].cpu().item()]]

        if action == "click_repair_trap" and (
            not isinstance(self.player, player.Defender)
            or self.room.game.wave.game_objects.trap.charges > 1
        ):
            action = "click_idle"

        if action == "click_pick_item":
            arg = p_actor_multinomial["target"].cpu().item()
            if not isinstance(self.player, player.Defender) or \
                    arg >= len(self.player.food) or self.player.food[arg] not in self.room.game.wave.dropped_food:
                action = "click_idle"
            else:
                args = [self.player.food[arg].uuid]
                # We lose 2 points every time we decide to pick up food.
                reward_delta -= 2

        if action == "click_use_poison_food":
            arg = p_actor_multinomial["target"].cpu().item()
            if not isinstance(self.player, player.Healer) or arg >= len(self.player.healers):
                action = "click_idle"
            else:
                args = [self.player.healers[arg].uuid]

        if action == "click_use_cannon":
            action = "click_idle"  # TODO: BUILD click_use_cannon handling.

        if action == "click_fire_egg":
            action = "click_idle"  # TODO: BUILD click_fire_egg handling.

        if action in ["special_pick_hammer", "special_pick_logs"]:
            pickable = action == "special_pick_hammer" and Hammer or Logs
            action = "click_pick_item"
            if not isinstance(self.player, player.Defender) or \
                    not any(isinstance(hnl, pickable) for hnl in self.room.game.wave.dropped_hnls):
                action = "click_idle"
            else:
                args = [next(hnl.uuid for hnl in self.room.game.wave.dropped_hnls if isinstance(hnl, pickable))]

        debug_string = f"action = {initial_action} -> {action}, args = {args}, "
        EventHandler.handle(action, args, self.room, self.role)

        # Handle instant actions.
        if "destroy_slots" in p_actor_multinomial:  # TODO: Debug, check that torch.max is what we need here.
            if torch.max(p_actor_multinomial["destroy_slots"]).cpu().item() > DESTROY_PROBABILITY:
                probability_list = p_actor_multinomial["destroy_slots"].cpu().tolist()[0]
                args = [[i for i in range(len(probability_list)) if probability_list[i] > DESTROY_PROBABILITY]]
                debug("Env.step", f"Destroying items. args = {args}.")
                EventHandler.handle("click_destroy_items", args, self.room, self.role)
                # We lose 2 points every time we decide to destroy n foods.
                reward_delta -= 2

        if "drop_count" in p_actor_multinomial:
            if p_actor_multinomial["drop_count"].cpu().item() > 0 and \
                    self.player.correct_call is not None:  # TODO: Received
                args = [self.player.correct_call, p_actor_multinomial["drop_count"].cpu().item()]  # TODO: Received
                debug("Env.step", f"Dropping food. args = {args}.")
                EventHandler.handle("click_drop_food", args, self.room, self.role)

        # Calculate the new state.
        last_tick = self.room.game.wave.relative_tick
        room_rv = self.room()
        if room_rv is not None:
            state, masks = self.preprocess(*room_rv)
        else:
            state, masks = None, None

        # Calculate the reward. If new_worth is less, the reward is positive. If more, negative.
        done = state is None
        new_worth = done and (self.last_worth + 100) or self.calculate_state_worth()
        reward = new_worth - self.last_worth + reward_delta
        debug_string += f"reward = {new_worth.item():.3f} - {self.last_worth.item():.3f} = {reward.item():.3f}."
        self.last_worth = not done and new_worth or None

        self.room.game.render_map(_print=True)

        debug("Env.step", f"{last_tick}:: " + debug_string)
        return state, masks, reward, done, last_tick
