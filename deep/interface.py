from log import debug
from simulation import EventHandler, Room
from .emit import build_emittable_object_from


def emit(self) -> None:
    # TODO: Send this data through to the deep learning controller playing this specific game (if many in parallel).
    build_emittable_object_from(self.game.inspectable)


setattr(Room, "emit_state", emit)
