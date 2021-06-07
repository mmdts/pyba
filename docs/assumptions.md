### Current Assumptions:

1. Wave 10 is not implemented. `TODO`
   * The simulation has no way of dealing with the penance queen.
   * The simulation has not been informed of the differences in the map (one trap, one cannon, cave switches, pools).
1. Cannon is not implemented. `TODO`
   * The cannon is there, and it takes up space, but no interaction with it is possible.
1. Blue eggs cannot be fired even after cannon gets implemented. `TODO`
   * Blue egg interaction is *not yet understood by me* and therefore cannot be implemented.
   * As a result, models built on top of this simulation cannot understand or participate in blue egg strategies.
1. Waves cannot last longer than 6 calls.
   * This is to prevent a timeout situation
1. The attacker is either always divine-potted or not.
   * This simplifies implementing potting in the simulation.
   * Tick-perfect divine potting / resetting divine pot timer while running to penance makes this not an issue.
1. No other form of potting / stat boosting is implemented.
   * The simulation does not account for boosted defence, stat drain, etc.
   * Most high level players won't need to use a potion in their entire life at Barbarian Assault
   * If your  defence is very low, raise it or use another account.
1. Player hitpoints (and thus dying) is not implemented.
   * If you die doing Barbarian Assault, raise your combat stats or use another account.
1. Armor is not implemented. Accuracy / damage boosting armor, along with set effects, are implemented as
   variables that can be set on the attacker.
1. Following players is not implemented.
   * I did not see a reason to follow another player in Barbarian Assault.
1. Prayer is not implemented.
   * Attacker stalling is implemented as a "stall" command, without going down to the gritty details.
   * No other usage of prayer exists in Barbarian Assault
1. Special attacks are only implemented for attacker, and for a select few weapons.
   * Send a pull request / file an issue if you believe a great special attack weapon has been forgotten.
1. Inventories are assumed to be properties of their respective players, rather than simulated.
   * This means that Healer / defender / collector having any items in their inventory is not implemented.
      * The defender will always have 9 of each food and a horn in his inventory.
      * The healer will always have a horn and a vial, but has the option to overstock food.
      * The collector will always have only a collector bag and a horn in his inventory.
   * It also means that attackers can only use the specified set of weapons, and can use nothing else.
1. As a result of the point above, some strategy-related inventory-based mechanics are not implemented.
   * Only main attacker can scroll.
   * Alching horn is not implemented. `TODO`
   * Defender overstocking is not implemented.
1. Everyone is level 5 in their respective role.
   * Get to level 5 or use another account.
1. Only waves are implemented. Rounds aren't (and time in room between waves isn't).
   * This way is much easier, as I won't have to build a map for the waiting room, and implement teleportation.
   * I also do not consider closing an interface and running to a ladder worth simulating.
   * Models built on top of this simulation have to hard-code their inter-wave activity, which is trivial.
1. Blocking caves is not implemented, as it is not part of usual Barbarian Assault play.
1. No penance can target or hit you after you go on cannon. I don't know if Runescape acts this way, but it
   should be a fairly realistic assumption, since most people won't move to cannon except after they deal with
   fighters and rangers, and the assumption *is* true for healers.
1. <font color="#c00">RED CLICKS ARE NOT IMPLEMENTED.</font> `todo`
   * Seriously how do people even come up with this stuff?
   * I'm not going to implement this because I'm just salty, even if it isn't too complex to implement (which it is).
1. Healer pool and vial usage are not implemented. This is a direct consequence of player hitpoints not being
   implemented in the first place. Right now it's just a block that takes up four tiles.
1. The big horn on the south-east corner is not implemented. The area for it is completely removed from map
   and is considered not pathable. I don't remember the last time I saw someone walking up there outside 2L on RS2.
1. Tile masks (required for guaranteed line of sight operation) are not implemented.
   * This shouldn't be an issue because line of sight blocking in waves 1 to 9 is pretty simple.
   * Please file issues for any line of sight bugs.
   * These will be implemented in the future C version.
1.