# The mmdts Big Barbarian Assault Project

### 2023-02-01 Update - The rest of the README is not up-to-date!

Some interest was sparked in this project. So here's an updated status:

* The project has three branches. `master`, `playground`, and `ongoing-playground-work`. The relation between them is strictly linear (each branch builds on top of the one before it). The only exception to this linearity is this commit that modifies the readme (which is present only on master so far).
* `master` has a good known state. It exhibits some bugs that were built while `playground` and `ongoing-playground-work` were being built. It is missing a lot of new things that were introduced during the building of `playground`, but it's just some stable state iirc.
* `playground` has all the deep-learning work that was started. It's a failed attempt at creating an RL agent that plays BA. However, a lot of bugs in the simulation itself, and some more penance monster AI improvement was made along the way.
* `ongoing-playground-work` has my most recent folder state. I just committed it and pushed it because I don't even remember what I was doing. I don't think this will run without issues, but if you want to pick up dev work on this, start from here.
* An unpublished branch has _fighter and ranger AIs_ that I don't think I want to put on github for the time being.
* Commits e11d167049d32ac495eb279131a49099bdde67f1 and 9de005bafedc955b1d2b9e14d4ff0b338535a575 are what you want to look at if you want some stable project state iirc.
* Right now, I don't have any of this running anywhere. There's a nice web-ui included, and 2~3 defender role players have tried it in secret :) I will spend 2~3 hours more on this to try to bring `ongoing-playground-work` into a playable state, and republish it on a relative's AWS account or a friend's Heroku account or something. Then I'll leave a link here.
* If you need to contact me about this, there's an issue called chat, or you could ping me on discord. Either way, don't expect a real-time reply!

---

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
