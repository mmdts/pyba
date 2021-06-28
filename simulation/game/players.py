from typing import Tuple, Union, List

from player import Player
from role_player import MainAttacker, SecondAttacker, Healer, Collector, Defender
from terrain import Inspectable


class Players:
    # ONLY click_ AND inspect_ METHODS AND __init__ AND __call__ SHOULD USE THE self.game VARIABLE!!
    # All other methods should be passed the parameters they need explicitly!
    def __init__(self, game: Inspectable):
        self.game: Inspectable = game
        self.main_attacker: MainAttacker = MainAttacker(self.game)
        self.second_attacker: SecondAttacker = SecondAttacker(self.game)
        self.healer: Healer = Healer(self.game)
        self.collector: Collector = Collector(self.game)
        self.defender: Defender = Defender(self.game)

        self.main_attacker.calls_with = self.collector
        self.second_attacker.calls_with = self.collector
        self.collector.calls_with = self.main_attacker
        self.healer.calls_with = self.defender
        self.defender.calls_with = self.healer

    def __iter__(self) -> Tuple[str, Player]:
        yield "a", self.main_attacker
        yield "s", self.second_attacker
        yield "h", self.healer
        yield "c", self.collector
        yield "d", self.defender

    def __getitem__(self, key: Union[int, str]) -> Player:
        if isinstance(key, str):
            key = key.lower()
            key = key.replace("_", "")
        assert key != "attacker", "Please specify which attacker you want."
        if key in ["mainattacker", "main", "a", 0]:
            return self.main_attacker
        if key in ["secondattacker", "second", "2a", "2", "s", 1]:
            return self.second_attacker
        if key in ["healer", "heal", "h", 2]:
            return self.healer
        if key in ["collector", "coll", "col", "c", 3]:
            return self.collector
        if key in ["defender", "def", "d", 4]:
            return self.defender
        raise KeyError(f"Players[{key}] does not exist.")

    def __call__(self) -> bool:
        for key, player in self:
            if not player():
                # Returns False if any player dies, a condition for wave end.
                # However, right now, players cannot die and will always return True,
                # making this if statement never execute, so we don't need to worry here.
                return False

        return True

    def get_iterable(self) -> List[Player]:
        return [self.main_attacker, self.second_attacker, self.healer, self.collector, self.defender]
