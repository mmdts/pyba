from terrain import Locatable, C, D, E


class GameObject(Locatable):
    def __init__(self, location: C):
        super().__init__(location)


class WEGameObject(GameObject):
    EAST, WEST = 0, 1

    east_spawn: C = None
    west_spawn: C = None

    def __init__(self, which: int):
        assert which in [WEGameObject.EAST, WEGameObject.WEST], \
            "We can only create one of two of this game object, the east one one or the west one."
        assert self.east_spawn is not None and self.west_spawn is not None, \
            "Please set the spawn locations in Subclass.__init__ before calling super().__init__."
        self.which = which
        super().__init__(which == WEGameObject.EAST and self.east_spawn or self.west_spawn)


class Trap(WEGameObject):
    MAX_CHARGES: int = 2

    # Logic for breaking in Runner, logic for repair in Defender.
    def __init__(self, which: int):
        self.east_spawn: C = E.TRAP
        self.west_spawn: C = E.WEST_TRAP
        self.charges: int = Trap.MAX_CHARGES
        super().__init__(which)
        self.follow_type = D.B


class Cannon(WEGameObject):
    def __init__(self, which: int):
        self.east_spawn = E.CANNON
        self.west_spawn = E.WEST_CANNON
        super().__init__(which)
        self.follow_type = D.S


class Hopper(WEGameObject):
    def __init__(self, which: int):
        self.east_spawn = E.HOPPER
        self.west_spawn = E.WEST_HOPPER
        super().__init__(which)
        self.follow_type = D.S


class GameObjects:
    def __init__(self):
        self.west_cannon = Cannon(WEGameObject.WEST)
        self.cannon = Cannon(WEGameObject.EAST)
        self.west_hopper = Hopper(WEGameObject.WEST)
        self.hopper = Hopper(WEGameObject.EAST)
        self.west_trap = Trap(WEGameObject.WEST)
        self.trap = Trap(WEGameObject.EAST)

        # These lists need to be east first then west, so that we can access them using lst[EAST] and lst[WEST].
        self.cannons = [self.cannon, self.west_cannon]
        self.hoppers = [self.hopper, self.west_hopper]
        self.traps = [self.trap, self.west_trap]
