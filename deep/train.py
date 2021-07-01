# TODO: Fix this to mask in the policy model itself, by supplying it an input of "available actions".
#  Target should be masked based on available targets (healers / foods) within sight.
from deep.trainer import Trainer


def train(rank, shared_model, counter, lock, optimizer, device):
    Trainer(rank, shared_model, counter, lock, optimizer, device)()
