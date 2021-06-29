from typing import Tuple, Dict

import torch
import torch.nn as nn

from .constants import State, BATCH_SIZE, EXPECTED_SIZES, LSTM_INPUT, LSTM_OUTPUT


class Policy(nn.Module):
    def __init__(self):
        super(Policy, self).__init__()

        # Trap, Wave, Tick
        # BSx2, BSx2, BSx4

        # Players
        # BSx5x7 -> BSx5x13 -> BSx65
        self.s_players = nn.Sequential(
            nn.Linear(EXPECTED_SIZES["players"][1], 32),
            nn.LeakyReLU(),
            nn.Linear(32, 13),
            nn.Flatten(),
        )

        # Foods
        # BSx20x5 -> BSx20x3 -> BSx60
        self.s_foods = nn.Sequential(
            nn.Linear(EXPECTED_SIZES["foods"][1], 32),
            nn.LeakyReLU(),
            nn.Linear(32, 3),
            nn.Flatten(),
        )

        # Runners
        # BSx9x3 -> BSx9x7 -> BSx63
        self.s_runners = nn.Sequential(
            nn.Linear(EXPECTED_SIZES["runners"][1], 32),
            nn.LeakyReLU(),
            nn.Linear(32, 7),
            nn.Flatten(),
        )

        # Healers
        # BSx8x11 -> BSx8x8 -> BSx64
        self.s_healers = nn.Sequential(
            nn.Linear(EXPECTED_SIZES["healers"][1], 32),
            nn.LeakyReLU(),
            nn.Linear(32, 8),
            nn.Flatten(),
        )

        # Inventory
        # BSx28x6 -> BSx28x3 -> BSx84
        self.s_inventory = nn.Sequential(
            nn.Linear(EXPECTED_SIZES["inventory"][1], 32),
            nn.LeakyReLU(),
            nn.Linear(32, 3),
            nn.Flatten(),
        )

        # Self
        # BSx1x(5 + 84) -> BSx1x64 -> BSx64
        self.s_self = nn.Sequential(
            nn.Linear(89, 108),
            nn.LeakyReLU(),
            nn.Linear(108, 64),
            nn.Flatten(),
        )

        # Map
        # BSx6x15x15 -> BSx32x7x7 -> BSx7x6x6 -> BSx252
        self.s_map = nn.Sequential(
            nn.Conv2d(EXPECTED_SIZES["map"][0], 32, kernel_size=(2, 2)),
            nn.LeakyReLU(),
            nn.MaxPool2d((2, 2)),
            nn.Conv2d(32, 7, kernel_size=(2, 2)),
            nn.LeakyReLU(),
            nn.Flatten(),
        )

        # The input size should be BSx576 or BSxSx576, where S is the sequence length.
        # The output is BSx512.
        # self.lstm = nn.LSTMCell(input_size=LSTM_INPUT, hidden_size=LSTM_OUTPUT)
        self.lstm = nn.Linear(LSTM_INPUT, LSTM_OUTPUT)

        # Action, count is 10 so far.
        # click_pick_hammer and click_pick_logs are new, separate actions.
        # BSx1x10
        self.o_action = nn.Sequential(
            nn.Linear(LSTM_OUTPUT, 10),
            nn.Softmax(dim=1)
        )

        # Target, 20 foods, only the first 8 are used as healers.
        # Unlike the options with explicit for zero, because I can drop/destroy while doing other things.
        # Target does not have a "zero" option.
        self.o_target = nn.Sequential(
            nn.Linear(LSTM_OUTPUT, 20),
            nn.Softmax(dim=1),
        )

        # Move X, count is 15, where e0 is -7 and e14 is 7.
        # BSx1x14
        self.o_move_x = nn.Sequential(
            nn.Linear(LSTM_OUTPUT, 14),
            nn.Softmax(dim=1),
        )

        # Move Y, count is 15, where e0 is -7 and e14 is 7.
        # BSx1x14
        self.o_move_y = nn.Sequential(
            nn.Linear(LSTM_OUTPUT, 14),
            nn.Softmax(dim=1),
        )

        # Destroy Slots, count is 28, destroying slots with probability above DESTROY_PROBABILITY.
        # Sigmoid because I can destroy multiple slots.
        # BSx1x28
        self.o_destroy_slots = nn.Sequential(
            nn.Linear(LSTM_OUTPUT, 28),
            nn.Sigmoid(),
        )

        # Drop Count, from e0 to e8 is 9 slots.
        # BSx1x9
        self.o_drop_count = nn.Sequential(
            nn.Linear(LSTM_OUTPUT, 9),
            nn.Softmax(dim=1),
        )

        # Dispenser Option, from e0 (using 0), e1, e2, and e3 (using all).
        # Using dispenser doesn't need a zero option but still has it for some reason.
        # BSx1x6
        self.o_dispenser_option = nn.Sequential(
            nn.Linear(LSTM_OUTPUT, 4),
            nn.Softmax(dim=1),
        )

        # Egg Target, Either none, runner or healer.
        # Using cannon doesn't need a zero option but still has it for some reason.
        # BSx1x3
        self.o_egg_target = nn.Sequential(
            nn.Linear(LSTM_OUTPUT, 3),
            nn.Softmax(dim=1),
        )

        self.value_linear = nn.Linear(LSTM_OUTPUT, 1)

    def forward(self, state: State, lstm_inputs: Tuple) -> Tuple[Dict, torch.Tensor, Tuple]:

        # lstm_inputs are (hn, cn).
        # We first pass the inventory to flatten it for appending to self.
        state["inventory"] = self.s_inventory(state["inventory"])

        # We append it to self, and forward pass everything to the point where they're ready for LSTM input.
        state["self"] = self.s_self(torch.cat((
            state["self"],
            torch.reshape(state["inventory"], (BATCH_SIZE, 1, -1))
        ), dim=-1))
        state["players"] = self.s_players(state["players"])
        state["foods"] = self.s_foods(state["foods"])
        state["runners"] = self.s_runners(state["runners"])
        state["healers"] = self.s_healers(state["healers"])
        state["map"] = self.s_map(state["map"])

        # We concatenate then pass to the LSTM.
        x = torch.cat((
            state["wave"], state["tick"], state["trap"], state["self"], state["players"], state["foods"],
            state["runners"],  state["healers"], state["map"]
        ), dim=1)

        # hn, cn = self.lstm(x, lstm_inputs)
        hn = self.lstm(x)
        cn = hn
        x = hn

        # The original plan was to matmul for target, but I'm not decided on the details.
        action_prediction = {
            "action": self.o_action(x),  # Softmax.
            "target": self.o_target(x),  # Softmax.
            "move_x": self.o_move_x(x),  # Softmax.
            "move_y": self.o_move_y(x),  # Softmax.
            "destroy_slots": self.o_destroy_slots(x),  # Sigmoid (multiple probabilities).
            "drop_count": self.o_drop_count(x),  # Softmax.
            "dispenser_option": self.o_dispenser_option(x),  # Softmax.
            "egg_target": self.o_egg_target(x),  # Softmax.
        }

        # We make a prediction for the value of the state as affected by this action on this state.
        value_prediction = self.value_linear(x)

        return action_prediction, value_prediction, (hn, cn)
