import random
from typing import Dict, List, Tuple

import torch

from log import debug
from simulation.base.dropped_item import Hammer, Logs
from simulation.base.player import Player
from simulation.base.terrain import Inspectable
from simulation.penance import Healer
from simulation import Room, EventHandler, player
from .constants import State, DESTROY_PROBABILITY, EXPECTED_SIZES
from .emit import make_build_emittable_function_for_device


# click_destroy_items and click_drop_food are instant.
# click_select_call is not handled here.
ACTIONS: List[str] = [
    "click_idle",
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
WAVE_LATENESS_RATIO = 1.01

END_TICKS: List[int] = [50, 70, 80, 80, 90, 100, 120, 130, 150]

SUPPOSED_HEALER_SPAWN_TICKS: List[List[int]] = [
    [10, 20],
    [10, 20, 30],
    [10, 20, 40],
    [10, 20, 30, 40],
    [10, 20, 30, 40, 50],
    [10, 20, 30, 40, 70, 80],
    [10, 20, 30, 40, 70, 80, 90],
    [10, 20, 30, 40, 50, 70, 80],
    [10, 20, 30, 40, 50, 60, 80, 90],
]

SUPPOSED_RUNNER_SPAWN_TICKS: List[List[int]] = [
    [10, 20],
    [10, 20, 30],
    [10, 20, 40, 50],
    [10, 20, 30, 40],
    [10, 20, 30, 40, 50],
    [10, 20, 30, 40, 50, 60],
    [10, 20, 30, 40, 50, 60],
    [10, 20, 30, 40, 50, 60, 70],
    [10, 20, 30, 40, 50, 60, 70, 80],
]


class Env:
    # This is an environment similar to OpenAI's Gym environments.
    # It has a reset and a step function.
    # It replaces the "interface" file that was previously present.
    def __init__(self, role, device):
        self.role = role
        self.device = device
        self.room = Room(mode=Room.PAUSE)
        self.room.accept_player_connection(role, role)
        self.room.extra = self
        self.player = self.room.get_player(self.role)
        self.last_worth = None

        setattr(self.room, "emit_state",
                make_build_emittable_function_for_device(player=self.player, device=self.device))

    def preprocess(self, state: State) -> State:
        if state is None:
            return None

        for key in state:
            if len(EXPECTED_SIZES[key]) < 2:
                continue
            if state[key].size() == 0:
                # No elements exist, we make them.
                state[key] = torch.zeros(EXPECTED_SIZES[key], device=self.device)
            if state[key].size()[0] < EXPECTED_SIZES[key][0]:
                # Less elements are observed than the required amount, we make the rest.
                padding = torch.zeros(
                    (EXPECTED_SIZES[key][0] - state[key].size()[0], EXPECTED_SIZES[key][1]), device=self.device)
                state[key] = torch.cat((state[key], padding))

        for key in state:
            state[key] = torch.unsqueeze(state[key], 0)

        return state

    def calculate_state_worth(self):
        # Higher worth means a worse state.
        max_hp = Healer.HITPOINTS[self.room.game.wave.number]
        tick_component = torch.zeros((1, 1), device=self.device)
        sigma_hp_healer_out = torch.zeros((1, 1), device=self.device)
        sigma_hp_healer_reserve = torch.zeros((1, 1), device=self.device)
        sigma_hp_runner_out = torch.zeros((1, 1), device=self.device)
        sigma_hp_runner_reserve = torch.zeros((1, 1), device=self.device)

        for healer in self.room.game.wave.penance.healers:
            if healer.hitpoints > 0 and healer.is_alive():
                sigma_hp_healer_out += healer.hitpoints / max_hp

        num_spawns = len(SUPPOSED_HEALER_SPAWN_TICKS[self.room.game.wave.number])
        num_reserves = self.room.game.wave.penance.spawns["h"][1]
        for i in reversed(range(num_spawns - num_reserves, num_spawns)):
            healer_factor = 1 + max(
                self.room.game.wave.relative_tick -
                SUPPOSED_HEALER_SPAWN_TICKS[self.room.game.wave.number][i], 0
            ) * CYCLE_LATENESS_FACTOR / Inspectable.CYCLE

            sigma_hp_healer_reserve += healer_factor

        num_spawns = len(SUPPOSED_RUNNER_SPAWN_TICKS[self.room.game.wave.number])
        num_reserves = self.room.game.wave.penance.spawns["d"][1]
        for i in reversed(range(num_spawns - num_reserves, num_spawns)):
            healer_factor = 1 + max(
                self.room.game.wave.relative_tick -
                SUPPOSED_RUNNER_SPAWN_TICKS[self.room.game.wave.number][i], 0
            ) * CYCLE_LATENESS_FACTOR / Inspectable.CYCLE

            sigma_hp_runner_reserve += healer_factor

        for runner in self.room.game.wave.penance.runners:
            if runner.hitpoints > 0 and runner.is_alive():
                sigma_hp_runner_out += 0.5

        hp_component = sigma_hp_healer_out + sigma_hp_healer_reserve + sigma_hp_runner_out + sigma_hp_runner_reserve
        tick_component += WAVE_LATENESS_FACTOR * WAVE_LATENESS_RATIO ** (
                self.room.game.wave.relative_tick - END_TICKS[self.room.game.wave.number]
        )
        return hp_component + tick_component

    def reset(self) -> State:
        EventHandler.handle("new_wave", [random.randint(1, 9), ""], self.room, self.role)
        rv = self.preprocess(self.room())
        self.last_worth = self.calculate_state_worth()
        return rv

    def step(self, action_prediction: Dict) -> Tuple[State, int, bool, str]:
        assert self.last_worth is not None, "You need to reset the environment once after initializing it."

        action = ACTIONS[torch.argmax(action_prediction["action"]).detach().cpu().item()]
        rv_action = action
        args = []

        # Calculate the action that gets passed to the EventHandler.
        if action == "click_move":
            args = [
                self.player.location.x +
                torch.argmax(action_prediction["move_x"]).detach().cpu().item() -
                Player.ACTION_DISTANCE // 2,
                self.player.location.y +
                torch.argmax(action_prediction["move_y"]).detach().cpu().item() -
                Player.ACTION_DISTANCE // 2,
            ]

        if action == "click_use_dispenser" and isinstance(self.player, player.Healer):
            args = [DISPENSER_OPTIONS[torch.argmax(action_prediction["dispenser_option"]).detach().cpu().item()]]

        if action == "click_pick_item":
            arg = torch.argmax(action_prediction["target"]).detach().cpu().item()
            if not isinstance(self.player, player.Defender) or \
                    arg >= len(self.player.food) or self.player.food[arg] not in self.room.game.wave.dropped_food:
                action = "click_idle"
            else:
                args = [self.player.food[arg].uuid]

        if action == "click_use_poison_food":
            arg = torch.argmax(action_prediction["target"]).detach().cpu().item()
            if not isinstance(self.player, player.Healer) or arg >= len(self.player.healers):
                action = "click_idle"
            else:
                args = [self.player.healers[arg].uuid]

        if action == "click_use_cannon":
            action = "click_idle"  # TODO: BUILD click_use_cannon handling.

        if action == "click_fire_egg":
            action = "click_idle"  # TODO: BUILD click_fire_egg handling.

        if action == "special_pick_hammer":
            action = "click_pick_item"
            if not isinstance(self.player, player.Defender) or \
                    not any(isinstance(hnl, Hammer) for hnl in self.room.game.wave.dropped_hnls):
                action = "click_idle"
            else:
                args = [next(hnl.uuid for hnl in self.room.game.wave.dropped_hnls if isinstance(hnl, Hammer))]

        if action == "special_pick_logs":
            action = "click_pick_item"
            if not isinstance(self.player, player.Defender) or \
                    not any(isinstance(hnl, Logs) for hnl in self.room.game.wave.dropped_hnls):
                action = "click_idle"
            else:
                args = [next(hnl.uuid for hnl in self.room.game.wave.dropped_hnls if isinstance(hnl, Logs))]

        debug_string = f"action = {rv_action} -> {action}, args = {args}, "
        EventHandler.handle(action, args, self.room, self.role)

        # Handle instant actions.
        if torch.max(action_prediction["destroy_slots"]).detach().cpu().item() > DESTROY_PROBABILITY:
            probability_list = action_prediction["destroy_slots"].detach().cpu().tolist()
            args = [i for i in range(len(probability_list)) if probability_list[i] > DESTROY_PROBABILITY]
            debug("Env.step", f"Destroying items. args = {args}.")
            EventHandler.handle("click_destroy_items", args, self.room, self.role)

        if torch.argmax(action_prediction["drop_count"]).detach().cpu().item() > 0 and \
                self.player.received_call is not None:
            args = [self.player.received_call, torch.argmax(action_prediction["drop_count"]).detach().cpu().item()]
            debug("Env.step", f"Dropping food. args = {args}.")
            EventHandler.handle("click_drop_food", args, self.room, self.role)

        # Calculate the new state.
        last_tick = self.room.game.wave.relative_tick
        state = self.preprocess(self.room())

        # Calculate the reward. If new_worth is less, the reward is positive. If more, negative.
        done = state is None
        new_worth = done and 100 or self.calculate_state_worth()
        reward = self.last_worth - new_worth
        debug_string += f"reward = {self.last_worth} - {new_worth} = {reward}."
        self.last_worth = not done and new_worth or None

        debug("Env.step", f"{last_tick}:: " + debug_string)
        return state, reward, done, rv_action
