from .terrain import Locatable, C, D, E, Inspectable


# No logic exists here. All the DroppedItem logic exists in the Players' or Npcs' respective classes.
class DroppedItem(Locatable):
    def __init__(self, location: C, game: Inspectable):
        super().__init__(location, game)
        self.follow_type: C = D.X


class Hammer(DroppedItem):
    def __init__(self, game: Inspectable):
        super().__init__(E.HAMMER_SPAWN, game)


class Logs(DroppedItem):
    NEAR, FAR = 0, 1

    def __init__(self, which: int, game: Inspectable):
        assert which in [Logs.NEAR, Logs.FAR], "We can only create one of two logs, the near one or the far one."
        super().__init__(which == Logs.NEAR and E.LOGS_SPAWN or E.FAR_LOGS_SPAWN, game)


class Egg(DroppedItem):
    RED, BLUE, GREEN = 0, 1, 2

    def __init__(self, location: C, which: int, game: Inspectable):
        super().__init__(location, game)
        self.which: int = which


class Food(DroppedItem):
    TOFU, CRACKERS, WORMS = 0, 1, 2

    def __init__(self, location: C, which: int, is_correct: bool, game: Inspectable):
        super().__init__(location, game)
        self.which: int = which
        self.is_correct: bool = is_correct
