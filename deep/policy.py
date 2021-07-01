from typing import Tuple

import torch
import torch.nn as nn

from simulation.base.player import Player
from .constants import State, BATCH_SIZE, EXPECTED_SIZES, LSTM_INPUT, LSTM_OUTPUT, Prediction, Hidden


def weights_init(model: nn.Module) -> None:
    if type(model) in [nn.Linear, nn.Conv2d]:
        nn.init.xavier_uniform_(model.weight)
        nn.init.constant_(model.bias, 0)
    elif type(model) in [nn.LSTMCell]:
        nn.init.constant_(model.bias_ih, 0)
        nn.init.constant_(model.bias_hh, 0)


class Policy(nn.Module):
    def __init__(self):
        super(Policy, self).__init__()

        # Trap, Wave, Tick
        # BSx2, BSx2, BSx4

        # Players
        # BSx5x7 -> BSx5x13 -> BSx65
        self.s_players = nn.Sequential(
            nn.Linear(EXPECTED_SIZES["players"][1], 32),
            nn.ELU(),
            nn.Linear(32, 13),
            nn.Flatten(),
        )

        # Foods
        # BSx20x5 -> BSx20x3 -> BSx60
        self.s_foods = nn.Sequential(
            nn.Linear(EXPECTED_SIZES["foods"][1], 32),
            nn.ELU(),
            nn.Linear(32, 3),
            nn.Flatten(),
        )

        # Runners
        # BSx9x3 -> BSx9x7 -> BSx63
        self.s_runners = nn.Sequential(
            nn.Linear(EXPECTED_SIZES["runners"][1], 32),
            nn.ELU(),
            nn.Linear(32, 7),
            nn.Flatten(),
        )

        # Healers
        # BSx8x11 -> BSx8x8 -> BSx64
        self.s_healers = nn.Sequential(
            nn.Linear(EXPECTED_SIZES["healers"][1], 32),
            nn.ELU(),
            nn.Linear(32, 8),
            nn.Flatten(),
        )

        # Inventory
        # BSx28x6 -> BSx28x3 -> BSx84
        self.s_inventory = nn.Sequential(
            nn.Linear(EXPECTED_SIZES["inventory"][1], 32),
            nn.ELU(),
            nn.Linear(32, 3),
            nn.Flatten(),
        )

        # Self
        # BSx1x(5 + 84) -> BSx1x64 -> BSx64
        self.s_self = nn.Sequential(
            nn.Linear(89, 108),
            nn.ELU(),
            nn.Linear(108, 64),
            nn.Flatten(),
        )

        # Map
        # BSx6x15x15 -> BSx32x7x7 -> BSx7x6x6 -> BSx252
        self.s_map = nn.Sequential(
            nn.Conv2d(EXPECTED_SIZES["map"][0], 32, kernel_size=(2, 2)),
            nn.ELU(),
            nn.MaxPool2d((2, 2)),
            nn.Conv2d(32, 7, kernel_size=(2, 2)),
            nn.ELU(),
            nn.Flatten(),
        )

        # The input size should be BSx576 or BSxSx576, where S is the sequence length.
        # The output is BSx512.
        self.lstm = nn.LSTMCell(input_size=LSTM_INPUT, hidden_size=LSTM_OUTPUT)

        # Action, count is 9 so far.
        # click_pick_hammer and click_pick_logs are new, separate actions.
        # BSx1x9
        self.o_action = nn.Sequential(
            nn.Linear(LSTM_OUTPUT, 9),
            nn.Softmax(dim=1)
        )

        # Target, 20 foods, only the first 8 are used as healers.
        # Unlike the options with explicit for zero, because I can drop/destroy while doing other things.
        # Target does not have a "zero" option.
        self.o_target = nn.Sequential(
            nn.Linear(LSTM_OUTPUT, 20),
            nn.Softmax(dim=1),
        )

        # Move, count is 15x15, where e0,0 is -7, -7 and e14,14 is 7, 7.
        # BSx1x225
        self.o_move = nn.Sequential(
            nn.Linear(LSTM_OUTPUT, Player.ACTION_DISTANCE ** 2),
            nn.ELU(),
            nn.Softmax(dim=1),
        )

        # Destroy Slots, count is 28, destroying slots with probability above DESTROY_PROBABILITY.
        # Sigmoid because I can destroy multiple slots.
        # BSx1x28
        self.o_destroy_slots = nn.Sequential(
            nn.Linear(LSTM_OUTPUT, 28),
            nn.Sigmoid(),
        )

        # Drop Count, from e0 to e8 is upto 8 food on that specific square.
        # BSx1x9
        self.o_drop_count = nn.Sequential(
            nn.Linear(LSTM_OUTPUT, EXPECTED_SIZES["drop_count"][1]),
            nn.Softmax(dim=1),
        )

        # Dispenser Option, from e0 (using 0), e1, e2, and e3 (using all).
        # BSx1x6
        self.o_dispenser_option = nn.Sequential(
            nn.Linear(LSTM_OUTPUT, 4),
            nn.Softmax(dim=1),
        )

        # Egg Target, Either runner or healer.
        # BSx1x3
        self.o_egg_target = nn.Sequential(
            nn.Linear(LSTM_OUTPUT, 2),
            nn.Softmax(dim=1),
        )

        self.critic_linear = nn.Linear(LSTM_OUTPUT, 1)

        self.apply(weights_init)
        self.train()

    def forward(self, state: State, lstm_inputs: Hidden) -> Tuple[Prediction, torch.Tensor, Hidden]:
        # lstm_inputs are (hn, cn).
        # We first pass the inventory to flatten it for appending to self.
        # We append it to self, and forward pass everything to the point where they're ready for LSTM input.
        hn, cn = self.lstm(
            torch.cat((
                state["wave"], state["tick"], state["trap"],
                self.s_self(torch.cat((
                    state["self"],
                    self.s_inventory(state["inventory"]).view(BATCH_SIZE, 1, -1),
                ), dim=-1)),
                self.s_players(state["players"]),
                self.s_foods(state["foods"]),
                self.s_runners(state["runners"]),
                self.s_healers(state["healers"]),
                self.s_map(state["map"]),
            ), dim=1),
            lstm_inputs
        )

        # The original plan was to matmul for target, but I'm not decided on the details.
        p_actor = {
            "action": self.o_action(hn),  # Softmax.
            "target": self.o_target(hn),  # Softmax.
            "move": self.o_move(hn),  # Softmax.
            "destroy_slots": self.o_destroy_slots(hn),  # Sigmoid (multiple probabilities).
            "drop_count": self.o_drop_count(hn),  # Softmax.
            "dispenser_option": self.o_dispenser_option(hn),  # Softmax.
            "egg_target": self.o_egg_target(hn),  # Softmax.
        }

        # We make a prediction for the value of the state as affected by this action on this state.
        p_critic = self.critic_linear(hn)

        return p_actor, p_critic, (hn, cn)
