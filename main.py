from os import system
from time import sleep

# from ai import \
#     RuleBasedMainAttacker as MainAttackerAi, \
#     RuleBasedSecondAttacker as SecondAttackerAi, \
#     RuleBasedDefender as DefenderAi, \
#     RuleBasedCollector as CollectorAi, \
#     RuleBasedHealer as HealerAi

import interface
# import test  # Please comment this import out if not testing.


def main():
    try:
        interface.server.run(interface.app)
    except (KeyboardInterrupt, TypeError, AssertionError, AttributeError, OSError, NotImplementedError, KeyError) as e:
        # interface.server can be used here to try to shut it and everything else down.
        raise e


if __name__ == "__main__":
    main()
