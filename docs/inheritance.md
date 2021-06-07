## Class Inheritance

### Bottom Level Files

These files include functions and constants that should be accessible
by every class. In turn, these files cannot import any of the files below.

* `log.py`

### Helper Classes

All these classes do not extend anything, and are more
of storage containers, constants, or game logic classes
than anything else.

* Terrain `terrain.py`
* C `terrain.py`
* D `terrain.py`
* E `terrain.py`
* Locatable `terrain.py`  -- **SEE BELOW**
* Inspectable `terrain.py`

### Locatable Classes

These classes represent actual entities in the game.
They are things you can interact with in some way or another.
They all extend the class `Locatable` found in `terrain.py`,
which means that  their respective objects have to exist on
some location on the map.

* GameObject `game_object.py` -- Cannot import `Unit`
  * Trap `game_object.py`
  * Cannon `game_object.py`
  * Hopper `game_object.py`
  * Dispenser `dispenser.py`
    * AttackerDispenser `dispenser.py`
    * DefenderDispenser `dispenser.py`
    * HealerDispenser `dispenser.py`
    * CollectorDispenser `dispenser.py`
* DroppedItem `dropped_item.py` -- Cannot import `Unit`
  * Hammer `dropped_item.py`
  * Logs `dropped_item.py`
  * Egg `dropped_item.py`
  * Food `dropped_item.py`
* Unit `unit.py`
  * Player `player.py`
    * Defender `role_player.py`
    * collector `role_player.py`
    * Healer `role_player.py`
    * Attacker `role_player.py`
      * MainAttacker `role_player.py`
      * SecondAttacker `role_player.py`
  * Npc `npc.py`
    * Runner `npc.py`
    * Healer `penance.py`
    * CombatNpc `combat_npc.py`
      * Fighter `combat_npc.py`
      * Ranger `combat_npc.py`

### Top Level Classes

These are like helper classes, but they need to be able to
import all locatable classes. Also, `Game` and `Wave` need
to be able to import `Players` and `Penance` respectively.

* Penance `penance.py`
* Players `player.py`
* Wave `game.py`
* Game `game.py`
* Ai `ai.py`
  * RuleBasedAi `ai.py`

### Top Level Files

These files do not include classes. They include top level functions,
and no class is capable of importing them.

* `main.py`
  * `test.py`
  * `interface.py`
