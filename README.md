# The mmdts Big Barbarian Assault Project

### Project Information

The license (MIT) is present in [LICENSE.txt](./LICENSE.txt).

Help is present in the folder [docs](./docs).

Help includes:
* The assumptions this project had to make to come to existence: [assumptions.md](./docs/assumptions.md)<br>
  This project is not true to Runescape in every single decision and mechanism.
* The inheritance structure of the classes used in this project: [inheritance.md](./docs/inheritance.md)<br>
  This can be a bit confusing to understand from code if you don't have a look at this, as they're not really
  very organized (current organization is intentional).
* Contribution guidelines: [contribute.md](./docs/contribute.md)<br>
  `TODO: DOCUMENT Explain contribution.`
* Test help: [test.md](./docs/test.md)<br>
  `TODO: DOCUMENT Explain test.`
* Usage help: [usage.md](./docs/usage.md)<br>
  `TODO: DOCUMENT Explain usage.`

### Progress
Done Till Milestone:
* `main.py`
* `dispenser.py`
* `dropped_item.py`
* `log.py`

Ongoing:
* `terrain.py`
* `runner.py`
* `game.py`
* `unit.py`

Not Started:
`penance.py`
`player.py`
`combat_npc.py`
`role_player.py`
`npc.py`
`test.py`
`game_object.py`

### Project Credits

Current contributors:
* [mmdts](https://github.com/mmdts) ` Main Developer`

Special thanks goes to **Mod Ash** [(Twitter)](https://twitter.com/JagexAsh) who was very helpful in answering
questions about the game that helped shape this project, and make it as accurate as it could be.

Special thanks goes to **Henke96** [(Github)](https://github.com/henke96)  for his valiant effort with his 
[Runner Simulator Project](https://github.com/henke96/BaSim) and his runner chart, which helped shape the
core runner mechanics present in this project.

Special thanks goes to **Icy001** [(Twitch)](https://www.twitch.tv/icy001), as referred by Henke96 to have provided
a good starting point for line of sight calculation.

### The Future of this Project

This project is currently implemented in Python to make prototyping and making changes easy.
Once a finished version gets finalized, the project is going to be ported to C++, with multiple
changes to the dynamics and assumptions being made, as well as performance optimizations.

The C++ project is then going to be used for *evil* purposes (in Evil Dave's voice) which will be
described in its README file after work on it has started.
