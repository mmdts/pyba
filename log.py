from typing import List, Tuple, Optional, Dict
from colorama import init, Fore, Style

init()

DEBUG: bool = False
GAME_PRINT: bool = False
J = Style.RESET_ALL
R = Fore.RED
Y = Fore.YELLOW
B = Fore.BLUE
G = Fore.GREEN
C = Fore.CYAN
LC = Fore.LIGHTCYAN_EX
LG = Fore.LIGHTGREEN_EX

ALLOWED_DEBUG_NAMESPACES: Dict[str, Optional[int]] = {
    # "Interface.disconnect_handler": None,
    # "Interface.room_connect": None,
    # "EventHandler.handle": None,
    # "Room.__call__": None,
    # "Wave.__call__": None,

    "Defender.pick_item": LC,
    # "Defender.click_repair_trap": C,
    # "Defender.repair_trap": LC,

    # "Player.__call__": G,  # The busy wait.
    "Player.path": G,
    "Player.move": G,
    "Player.single_step": LG,
    "Unit.exhaust_pmac": LG,

    "Runner.do_cycle": C,
    "Runner.step": LC,
    "Runner.tick_eat": C,
    "Runner.tick_eat.c": B,
    "Runner.tick_target": C,
    "Runner.walk": LC,
}


ALLOWED_GAME_PRINT_NAMESPACES: Dict[str, Optional[int]] = {
    # "Game.print_map": None,
    # "Game.print_runners": None,
    "Penance.print": Y,
    # "Wave.print": None,
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
