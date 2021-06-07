from game_object import GameObject
from terrain import C, D, E


# No logic exists here. All the Dispenser logic exists in the Players' respective classes.
class Dispenser(GameObject):
    DEFAULT_STOCK: int = 5

    def __init__(self, location: C):
        super().__init__(location)
        self.follow_type = D.N


class HealerDispenser(Dispenser):
    def __init__(self):
        super().__init__(E.HEALER_DISPENSER)


class DefenderDispenser(Dispenser):
    def __init__(self):
        super().__init__(E.DEFENDER_DISPENSER)


class CollectorDispenser(Dispenser):
    def __init__(self):
        super().__init__(E.COLLECTOR_DISPENSER)


class AttackerDispenser(Dispenser):
    def __init__(self):
        super().__init__(E.ATTACKER_DISPENSER)
