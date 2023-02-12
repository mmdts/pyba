from typing import Dict, Tuple, Optional

import torch

from log import debug

if not torch.cuda.is_available():
    raise EnvironmentError("Cuda is not available!")

# TODO: Organize constants into their respective files.
debug("General", f"CUDA device count is {torch.cuda.device_count()}. "
                 f"constants.py has been imported, usually signalling the start of a new process.")
CUDA0 = torch.device('cuda:0')
CUDA1 = torch.device('cuda:1')

State = Prediction = Masks = Optional[Dict[str, torch.Tensor]]
Hidden = Tuple[torch.Tensor, torch.Tensor]


# Training Parameters
SEED: int = 1625582114
NUM_PROCESSES: int = 1
BATCH_SIZE: int = 1  # We don't have batches for now, just single-threaded single-actor GAE.
ITERATION_COUNT: int = 4000
NUM_FORWARD_STEPS_PER_TRAJECTORY: int = 50
LEARNING_RATE: float = 5e-5  # For the optimizer (Adam, but could be RMSProp).
DISCOUNT_FACTOR: float = 0.996  # For generalized advantage estimation.
GAE_PARAMETER: float = 1.00  # For generalized advantage estimation.
ENTROPY_WEIGHT: float = 0.01  # For generalized advantage estimation.
CRITIC_LOSS_WEIGHT: float = 0.5  # For loss calculation.
MAX_GRAD_NORM: float = 40

# Play Parameters
DESTROY_PROBABILITY: float = 0.7

# Log Parameters
ITERATIONS_PER_LOG: int = 5

# Model Parameters
EXPECTED_SIZES: Dict[str, Tuple[int, ...]] = {
    "trap": (2,),
    "wave": (2,),
    "tick": (4,),
    "players": (5, 7),
    "foods": (20, 5),
    "runners": (9, 3),
    "healers": (8, 11),
    "inventory": (28, 6),
    "self": (1, 5),
    "map": (6, 15, 15),
    "drop_count": (1, 9)
}

LSTM_INPUT: int = 2+2+4+65+60+63+64+64+252
LSTM_OUTPUT: int = 512
LSTM_HIDDEN_SIZE: Tuple[int, ...] = (1, 512)