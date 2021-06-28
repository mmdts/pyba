from typing import Dict, Callable, Union, Any, List

import torch

from simulation.base.dropped_item import Food
from simulation.base.player import Player
from simulation.base.terrain import Y, Terrain
from simulation import penance

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

INVENTORY = {
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


def build_emittable_object_from(x: Player) -> Dict[str, torch.Tensor]:
    return {
        "players": torch.Tensor([
            [player.location.x, player.location.y] + ROLES[player.access_letter()]
            for player in x.game.players
            if player.location.chebyshev_to(x.location) < Player.ACTION_DISTANCE
        ], dtype=torch.float32),

        "dropped_food": torch.Tensor([
            [food.location.x, food.location.y] + FOODS[food.which]
            for food in x.game.wave.dropped_foodplayers
            if food.location.chebyshev_to(x.location) < Player.ACTION_DISTANCE
        ], dtype=torch.float32),

        "runners": torch.Tensor([
            [runner.location.x, runner.location.y, runner.hitpoints]
            for runner in x.game.wave.penance.runnersplayers
            if runner.location.chebyshev_to(x.location) < Player.ACTION_DISTANCE
        ], dtype=torch.float32),

        "healers": torch.Tensor([
            [healer.location.x, healer.location.y, healer.hitpoints] + target_info(healer)
            for healer in x.game.wave.penance.healersplayers
            if healer.location.chebyshev_to(x.location) < Player.ACTION_DISTANCE
        ], dtype=torch.float32),

        "inventory": torch.Tensor([
            INVENTORY[slot]
            for slot in x.inventory
        ], dtype=torch.float32),

        "self": torch.Tensor([x.location.x, x.location.y].extend(CALLS[x.received_call]), dtype=torch.float32),

        "map": torch.Tensor([
            Terrain.channel_occupiable(x.location, Player.ACTION_DISTANCE),
            Terrain.channel_seeable(x.location, Player.ACTION_DISTANCE),
            Terrain.channel_level(x.location, Player.ACTION_DISTANCE),
            Terrain.channel_players(x.location, Player.ACTION_DISTANCE, x.game.player_map),
            Terrain.channel_runners(x.location, Player.ACTION_DISTANCE, x.game.map),
            Terrain.channel_healers(x.location, Player.ACTION_DISTANCE, x.game.map),
        ], dtype=torch.float32),
    }
