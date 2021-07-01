from typing import List, Tuple

import torch

from simulation.base.dropped_item import Food, Hammer, Logs
from simulation.base.game_object import Trap
from simulation.base.player import Player
from simulation.base.terrain import Y, Terrain, E, C
from simulation.player import Defender, Healer
from simulation import penance
from .constants import State, Masks, EXPECTED_SIZES

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


def make_build_emittable_function_for_device(game, role, device):
    def build_emittable_object_from() -> Tuple[State, Masks]:
        nonlocal device, game, role
        player = game.players[role]
        rv = {
            "wave": torch.Tensor([player.game.wave.number] * 2).float().to(device=device),
            "tick": torch.Tensor([player.game.wave.relative_tick] * 4).float().to(device=device),
            "trap": torch.Tensor([player.game.wave.game_objects.trap.charges] * 2).float().to(device=device),
            "players": torch.Tensor([
                [player.location.x, player.location.y] + ROLES[player.access_letter()]
                for key, player in player.game.players
                if player.location.chebyshev_to(player.location) < Player.ACTION_DISTANCE
            ]).float().to(device=device),

            "foods": torch.Tensor([
                [food.location.x, food.location.y] + FOODS[food.which]
                for i, food in enumerate(player.game.wave.dropped_food)
                if food.location.chebyshev_to(player.location) < Player.ACTION_DISTANCE
                and i < EXPECTED_SIZES["foods"][0]
            ]).float().to(device=device),

            "runners": torch.Tensor([
                [runner.location.x, runner.location.y, runner.hitpoints]
                for runner in player.game.wave.penance.runners
                if runner.location.chebyshev_to(player.location) < Player.ACTION_DISTANCE
            ]).float().to(device=device),

            "healers": torch.Tensor([
                [healer.location.x, healer.location.y, healer.hitpoints] + target_info(healer)
                for healer in player.game.wave.penance.healers
                if healer.location.chebyshev_to(player.location) < Player.ACTION_DISTANCE
            ]).float().to(device=device),

            "inventory": torch.Tensor([
                INVENTORY[slot]
                for slot in player.inventory
            ]).float().to(device=device),

            "self": torch.Tensor([
                [player.location.x, player.location.y] + CALLS[player.correct_call]  # TODO: Received
            ]).float().to(device=device),

            "map": torch.Tensor([  # TODO: Remove the notes for inspect.
                Terrain.channel_occupiable(player.location, Player.ACTION_DISTANCE // 2),
                Terrain.channel_seeable(player.location, Player.ACTION_DISTANCE // 2),
                Terrain.channel_level(player.location, Player.ACTION_DISTANCE // 2),
                Terrain.channel_players(player.location, Player.ACTION_DISTANCE // 2, player.game.player_map),
                Terrain.channel_runners(player.location, Player.ACTION_DISTANCE // 2, player.game.map),
                Terrain.channel_healers(player.location, Player.ACTION_DISTANCE // 2, player.game.map),
            ]).float().to(device=device),
        }

        is_defender = isinstance(player, Defender)
        is_healer = isinstance(player, Healer)
        dispenser = player.game.wave.dispensers[player.access_letter()]
        inventory_food_count = is_defender and player.inventory.count(str(player.correct_call)) or 0  # TODO: Received
        valid_target_count = rv[is_defender and "foods" or "healers"].size()[0]

        masks = {
            "action": torch.Tensor([
                # We can't move except after stocking.
                player.has_used_dispenser,
                # We can't stock unless we have empty space and dispenser is in action distance.
                Y.EMPTY in player.inventory
                and player.location.chebyshev_to(dispenser.location) < Player.ACTION_DISTANCE,
                # We can't pick food unless some exists around us.
                is_defender and valid_target_count > 0,
                # We can't repair trap unless it's both not fully charged and within our action distance.
                is_defender and player.game.wave.game_objects.trap.charges < Trap.MAX_CHARGES
                and player.location.chebyshev_to(player.game.wave.game_objects.trap) < Player.ACTION_DISTANCE,
                # We can't use poison food unless we have available food in inventory.
                is_healer and str(player.correct_call) in player.inventory,  # TODO: Received
                # We can't use cannon at all yet.
                # TODO: We can't use cannon unless it is loaded and within action distance.
                0,
                # We can't fire egg at all yet.
                # TODO: We can't fire egg unless we're using cannon.
                0,
                # We can't pick hammer unless it is within action distance and we have a slot for it.
                is_defender and Y.EMPTY in player.inventory
                and any(isinstance(hnl, Hammer) for hnl in player.game.wave.dropped_hnls)
                and player.location.chebyshev_to(E.HAMMER_SPAWN) < Player.ACTION_DISTANCE,
                # We can't pick logs unless it is within action distance and we have a slot for it.
                is_defender and Y.EMPTY in player.inventory
                and any(isinstance(hnl, Logs) for hnl in player.game.wave.dropped_hnls)
                and player.location.chebyshev_to(E.LOGS_SPAWN) < Player.ACTION_DISTANCE,
            ]).float().to(device=device).view(1, -1),
            "target": valid_target_count > torch.arange(EXPECTED_SIZES["foods"][0], device=device).view(1, -1),
            "move": torch.Tensor([
                Terrain.is_occupiable(C(
                    player.location.x + movement // Player.ACTION_DISTANCE - Player.ACTION_DISTANCE // 2,
                    player.location.y + (movement % Player.ACTION_DISTANCE) - Player.ACTION_DISTANCE // 2
                )) for movement in range(Player.ACTION_DISTANCE ** 2)
            ]).float().to(device=device).view(1, -1),
            "destroy_slots": torch.Tensor([
                is_healer and slot in ["0", "1", "2"] for slot in player.inventory
            ]).float().to(device=device).view(1, -1),
            # TODO: Probably impossible later on, but allow for wrong food dropping strategies.
            "drop_count": inventory_food_count > torch.arange(
                EXPECTED_SIZES["drop_count"][1], device=device).view(1, -1),
        }

        return rv, masks

    return build_emittable_object_from
