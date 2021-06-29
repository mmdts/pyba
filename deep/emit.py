from typing import List

import torch

from simulation.base.dropped_item import Food
from simulation.base.player import Player
from simulation.base.terrain import Y, Terrain
from simulation import penance, Room
from .constants import State

ROLES = {
    "a": [1, 0, 0, 0, 0],
    "s": [0, 1, 0, 0, 0],
    "h": [0, 0, 1, 0, 0],
    "c": [0, 0, 0, 1, 0],
    "d": [0, 0, 0, 0, 1],
}

FOODS = {
    Food.TOFU:     [1, 0, 0],
    Food.CRACKERS: [0, 1, 0],
    Food.WORMS:    [0, 0, 1],
}

INVENTORY = {  # TODO: Try with embeddings for inventory, food, calls and roles.
    Y.EMPTY:        [0, 0, 0, 0, 0, 0],
    Y.TOFU:         [1, 0, 0, 0, 0, 0],
    Y.CRACKERS:     [0, 1, 0, 0, 0, 0],
    Y.WORMS:        [0, 0, 1, 0, 0, 0],
    Y.HAMMER:       [0, 0, 0, 1, 0, 0],
    Y.LOGS:         [0, 0, 0, 0, 1, 0],
    Y.POISON_TOFU:  [1, 0, 0, 0, 0, 0],
    Y.POISON_WORMS: [0, 1, 0, 0, 0, 0],
    Y.POISON_MEAT:  [0, 0, 1, 0, 0, 0],
    Y.VIAL:         [0, 0, 0, 0, 0, 1],
    Y.BLOCKED:      [0, 0, 0, 0, 0, 1],
    Y.HORN:         [0, 0, 0, 0, 0, 1],
}

CALLS = {
    None: [0, 0, 0],
    0: [1, 0, 0],
    1: [0, 1, 0],
    2: [0, 0, 1],
}


def target_info(healer: penance.Healer) -> List:
    if healer.followee is None:
        return [0, 0, 0, 0, 0, 0, 0, 0]

    if isinstance(healer.followee, penance.Runner):
        return [healer.followee.location.x, healer.followee.location.y, 0, 0, 0, 0, 0, 1]

    if isinstance(healer.followee, Player):
        return [healer.followee.location.x, healer.followee.location.y] + ROLES[healer.followee.access_letter()] + [0]

    return [0, 0, 0, 0, 0, 0, 0, 0]


def make_build_emittable_function_for_device(player, device):
    def build_emittable_object_from() -> State:
        nonlocal device, player
        x = player
        return {
            "wave": torch.Tensor([x.game.wave.number] * 2).float().to(device=device),
            "tick": torch.Tensor([x.game.wave.relative_tick] * 4).float().to(device=device),
            "trap": torch.Tensor([x.game.wave.game_objects.trap.charges] * 2).float().to(device=device),
            "players": torch.Tensor([
                [player.location.x, player.location.y] + ROLES[player.access_letter()]
                for key, player in x.game.players
                if player.location.chebyshev_to(x.location) < Player.ACTION_DISTANCE
            ]).float().to(device=device),

            "foods": torch.Tensor([
                [food.location.x, food.location.y] + FOODS[food.which]
                for food in x.game.wave.dropped_food
                if food.location.chebyshev_to(x.location) < Player.ACTION_DISTANCE
            ]).float().to(device=device),

            "runners": torch.Tensor([
                [runner.location.x, runner.location.y, runner.hitpoints]
                for runner in x.game.wave.penance.runners
                if runner.location.chebyshev_to(x.location) < Player.ACTION_DISTANCE
            ]).float().to(device=device),

            "healers": torch.Tensor([
                [healer.location.x, healer.location.y, healer.hitpoints] + target_info(healer)
                for healer in x.game.wave.penance.healers
                if healer.location.chebyshev_to(x.location) < Player.ACTION_DISTANCE
            ]).float().to(device=device),

            "inventory": torch.Tensor([
                INVENTORY[slot]
                for slot in x.inventory
            ]).float().to(device=device),

            "self": torch.Tensor([
                [x.location.x, x.location.y] + CALLS[x.received_call]
            ]).float().to(device=device),

            "map": torch.Tensor([  # TODO: Remove the notes for inspect.
                Terrain.channel_occupiable(x.location, Player.ACTION_DISTANCE // 2),
                Terrain.channel_seeable(x.location, Player.ACTION_DISTANCE // 2),
                Terrain.channel_level(x.location, Player.ACTION_DISTANCE // 2),
                Terrain.channel_players(x.location, Player.ACTION_DISTANCE // 2, x.game.player_map),
                Terrain.channel_runners(x.location, Player.ACTION_DISTANCE // 2, x.game.map),
                Terrain.channel_healers(x.location, Player.ACTION_DISTANCE // 2, x.game.map),
            ]).float().to(device=device),
        }

    return build_emittable_object_from
