from typing import Dict, Callable, Union, Any

from .base.terrain import C, Locatable, Inspectable


def build_transmittable_object_from(x: Union[Locatable, Inspectable]) -> Dict:
    # TODO: Clean this up to only include transmittable stuff (inspects).
    if isinstance(x, Locatable):
        _dict = {
            "uuid": x.uuid,
            "location": (x.location.x, x.location.y),
            "_": x.__class__.__name__,
        }

        attr_list = [
            "inventory",
            # "busy_i",
            "calls_with",
            "destination",
            # "pathing_queue",
            "followee",
            "follow_type",
            "follow_allow_under",
            "is_running",
            "followee_last_found",
            "CALL_COUNT",
            "INVENTORY_SPACE",
            "correct_call",
            "required_call",
            "received_call",
            "sent_call",
            "name",
            "spec_restore_i",
            "spec",
            "gear_bonus",
            "is_stalling",
            "stall_queue",
            "access_letter",
            "which",  # For food and eggs.
            "is_correct",
            "charges",  # For trap.
        ]

        for attr in attr_list:
            try:
                _attr: Union[Callable, Any] = x.__getattribute__(attr)
            except AttributeError:
                _attr = None
            if _attr is not None:
                if isinstance(_attr, list) and len(_attr) == 0:
                    _attr = None  # Empty array, we don't know type yet.

                if attr == "access_letter":
                    _attr = _attr()

                if isinstance(_attr, list) and len(_attr) > 0 and isinstance(_attr[0], tuple):
                    _attr = len(_attr)

                if isinstance(_attr, list) and len(_attr) > 0 and isinstance(_attr[0], C):
                    _attr = [[c.x, c.y] for c in _attr]

                if isinstance(_attr, C):
                    _attr = [_attr.x, _attr.y]

                if isinstance(_attr, Locatable):
                    _attr = str(_attr.uuid)

                _dict[attr] = _attr

        return _dict

    if isinstance(x, Inspectable):
        _dict = {
            "tick": x.tick,
            "text": x.text_payload,
            "players": {k: build_transmittable_object_from(locatable) for k, locatable in x.players},
            "print_map": x.arg.print_map(ret=True),
            "original_map": x.arg.original_map,
            "wave": {
                "correct_calls": x.wave.correct_calls,
                "start_tick": x.wave.start_tick,
                "relative_tick": x.wave.relative_tick,
                "calls": x.wave.calls,
                "number": x.wave.number,
                "end_flag": x.wave.end_flag,
                "game_objects": {
                    "west_cannon": build_transmittable_object_from(x.wave.game_objects.west_cannon),
                    "cannon": build_transmittable_object_from(x.wave.game_objects.cannon),
                    "west_hopper": build_transmittable_object_from(x.wave.game_objects.west_hopper),
                    "hopper": build_transmittable_object_from(x.wave.game_objects.hopper),
                    "west_trap": build_transmittable_object_from(x.wave.game_objects.west_trap),
                    "trap": build_transmittable_object_from(x.wave.game_objects.trap),
                },
                "dropped_food": [build_transmittable_object_from(locatable)
                                 for locatable in x.wave.dropped_food],
                "dispensers": {k: build_transmittable_object_from(locatable)
                               for k, locatable in x.wave.dispensers.items()},
                "dropped_eggs": [build_transmittable_object_from(locatable)
                                 for locatable in x.wave.dropped_eggs],
                "dropped_hnls": [build_transmittable_object_from(locatable)
                                 for locatable in x.wave.dropped_hnls],
                "penance": {k: [build_transmittable_object_from(locatable)
                                for locatable in v] for k, v in x.wave.penance},
            }
        }

        return _dict

    raise NotImplementedError(f"The object provided, {x} cannot be transmitted.")
