from typing import Dict, Tuple, Optional

import torch

from log import debug

if not torch.cuda.is_available():
    raise EnvironmentError("Cuda is not available!")

debug("General", f"CUDA DEVICE COUNT IS {torch.cuda.device_count()}.")
CUDA0 = torch.device('cuda:0')
CUDA1 = torch.device('cuda:1')

State = Optional[Dict[str, torch.Tensor]]


# Training Parameters
BATCH_SIZE: int = 1  # We don't have batches for now, just single-threaded single-actor GAE.
ITERATION_COUNT: int = 200
NUM_FORWARD_STEPS_PER_TRAJECTORY: int = 50
LEARNING_RATE: float = 0.0001  # For the optimizer (Adam, but could be RMSProp).
DISCOUNT_FACTOR: float = 0.99  # For generalized advantage estimation.
GAE_PARAMETER: float = 1.00  # For generalized advantage estimation.
ENTROPY_WEIGHT: float = 0.01  # For generalized advantage estimation.

# Play Parameters
DESTROY_PROBABILITY: float = 0.7


# Model Parameters
EXPECTED_SIZES: Dict[str, Tuple] = {
    "trap": (2,),
    "wave": (2,),
    "tick": (2,),
    "players": (5, 7),
    "foods": (20, 5),
    "runners": (9, 3),
    "healers": (8, 11),
    "inventory": (28, 6),
    "self": (1, 5),
    "map": (6, 15, 15),
}

LSTM_INPUT: int = 2+2+4+65+60+63+64+64+252
LSTM_OUTPUT: int = 512
