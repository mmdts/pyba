from typing import Optional, Dict
from colorama import init, Fore, Back

init()

DEBUG: bool = False
GAME_PRINT: bool = False
J = Fore.RESET
K = Back.RESET
X = Back.BLACK

R = Fore.RED
Y = Fore.YELLOW
G = Fore.GREEN
C = Fore.CYAN
B = Fore.BLUE
M = Fore.MAGENTA

LR = Fore.LIGHTRED_EX
LY = Fore.LIGHTYELLOW_EX
LG = Fore.LIGHTGREEN_EX
LC = Fore.LIGHTCYAN_EX
LB = Fore.LIGHTBLUE_EX
LM = Fore.LIGHTMAGENTA_EX

# Defender is B, Runner is LB
# Healer is G, Penance Healer is LG
# Attacker is M, CombatNpc are LM
# Collector is LY
# Game Print is Y
# C is used for general purpose Player / Unit.
# LC is used for general purpose Npc.
# R and LR are used for errors.
# None is used for anything Wave and above.
ALLOWED_DEBUG_NAMESPACES: Dict[str, Optional[int]] = {
    # "Interface.disconnect_handler": None,
    # "Interface.room_connect": None,
    # "EventHandler.handle": None,
    # "Room.__call__": None,
    # "Wave.__call__": None,

    # "Defender.pick_item": B,
    # "Defender.click_repair_trap": B,
    # "Defender.repair_trap": B,

    # "Player.__call__": C,  # The busy wait.
    # "Player.path": C,
    "Player.move": C,
    # "Player.move.pathing_queue": C,
    # "Player.single_step": C,
    "Unit.exhaust_pmac": C,
    # "Npc.__call__": LC,

    # "Runner.do_cycle": LB,
    # "Runner.step": LB,
    # "Runner.tick_eat": LB,
    "Runner.tick_eat.c": LB,
    # "Runner.tick_target": LB,
    # "Runner.walk": LB,

    "Healer.heal": LG,
    "Healer.do_cycle": LG,
    "Healer.switch_target": LG,
    "Healer.single_step": G,
    "Healer.on_reach": LG,
}


ALLOWED_GAME_PRINT_NAMESPACES: Dict[str, Optional[int]] = {
    # "Game.print_map": None,
    # "Game.print_runners": None,
    "Penance.print": Y,
    "Player.print": Y,
    "Wave.print": Y,
    # "Terrain.print": None,
}


def debug(namespace: str, *args, **kwargs) -> None:
    if not DEBUG:
        return None

    if namespace not in ALLOWED_DEBUG_NAMESPACES:
        return None

    color = ALLOWED_DEBUG_NAMESPACES[namespace] or ""

    return print(f"DEBUG:: {color}{namespace:<20}{J}::", *args, **kwargs)


def game_print(namespace: str, *args, **kwargs) -> None:
    if not GAME_PRINT:
        return None

    if namespace not in ALLOWED_GAME_PRINT_NAMESPACES:
        return None

    color = ALLOWED_GAME_PRINT_NAMESPACES[namespace] or ""

    return print(f"GAME :: {color}{namespace:<20}{J}::", *args, **kwargs)
