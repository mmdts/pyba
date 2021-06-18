from game_object import GameObject
from terrain import C, D, E, Inspectable


# No logic exists here. All the Dispenser logic exists in the Players' respective classes.
class Dispenser(GameObject):
    DEFAULT_STOCK: int = 5

    def __init__(self, location: C, game: Inspectable):
        super().__init__(location, game)
        self.follow_type = D.N


class HealerDispenser(Dispenser):
    def __init__(self, game: Inspectable):
        super().__init__(E.HEALER_DISPENSER, game)


class DefenderDispenser(Dispenser):
    def __init__(self, game: Inspectable):
        super().__init__(E.DEFENDER_DISPENSER, game)


class CollectorDispenser(Dispenser):
    def __init__(self, game: Inspectable):
        super().__init__(E.COLLECTOR_DISPENSER, game)


class AttackerDispenser(Dispenser):
    def __init__(self, game: Inspectable):
        super().__init__(E.ATTACKER_DISPENSER, game)
