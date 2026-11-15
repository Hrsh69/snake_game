# Pac-Snake

A Snake game with a Pac-Man twist, written in pure Python with the built-in `turtle` module. No third-party packages needed.

You play a chomping Pac-Man-headed snake through a series of levels. Eat food to grow and speed up, dodge ghosts and patrolling blocks, use portals, and grab power-ups. Every level changes the rules a little: walls start deadly, then alternate with wrap-around walls, and the ghosts, portals and moving obstacles come in as you progress.

## Features

- **Levels** that add new hazards as you go, with a "LEVEL N" banner explaining what changed
- **Ghosts** that chase you at half speed (one chases directly, one aims ahead of you)
- **Power pellet** that turns the ghosts blue so you can eat them for 10 / 20 / 40 points
- **Teleport portals**: enter one ring, exit the other
- **Five power-ups**: slow-mo, phase (pass through yourself), shrink, shield and magnet
- **Patrolling blocks** that slide back and forth across the arena
- **Deadly walls vs wrap-around walls**, switching by level
- **Bonus food** worth +5 that disappears if you're too slow
- **Persistent high score** saved to a file
- Pause, restart and quit from the keyboard
- Smooth timer-based game loop (no frozen window)

## Requirements

- Python 3.8 or newer
- Tkinter (ships with most Python installs, since `turtle` is built on it)

Check that you have it:

```bash
python -m tkinter
```

A small window should appear. If you get an import error, see [Troubleshooting](#troubleshooting).

## Running the game

```bash
python game.py
```

On some systems the command is `python3 game.py`.

Click the game window once after it opens so it receives keyboard input.

## Controls

| Key | Action |
|---|---|
| Arrow keys / `W` `A` `S` `D` | Steer the snake |
| `Space` or `P` | Start, pause and resume (also restarts after game over) |
| `R` | Restart at any time |
| `Q` or `Esc` | Quit |

The snake can't reverse directly into itself, and two quick key presses can't sneak a reversal in either.

## How to play

Eat the white dots to grow and score. You die if you hit a wall (on deadly-wall levels), an obstacle, your own body, or a ghost that isn't frightened.

### Scoring

| Item | Points |
|---|---|
| White food | +1 |
| Cyan triangle (bonus), every 5 foods, lasts 45 moves | +5 |
| Big flashing pellet | +2 and frightens the ghosts |
| Frightened ghosts, in a row | +10, +20, +40 |

The game gets faster with every food eaten, down to a minimum delay. Your best score is saved automatically.

### Levels

You advance every **8 foods**. What each level adds:

| Level | Walls | Portals | Ghosts | Static blocks | Patrolling blocks |
|---|---|---|---|---|---|
| 1 | Deadly | no | 0 | 0 | 0 |
| 2 | Deadly | yes | 1 | 2 | 0 |
| 3 | **Wrap** | no | 1 | 4 | 1 |
| 4 | Deadly | yes | 2 | 6 | 2 |
| 5 | **Wrap** | no | 2 | 8 | 3 |
| 6+ | Alternates (odd = wrap) | Alternates (even = yes) | 2 | +2 per level, max 15 | 3 |

The border shows the rule: **solid blue** means walls are deadly, **dashed green** means they wrap around.

### Ghosts and the power pellet

Ghosts move at half your speed and freeze briefly at the start of each level. The pink ghost heads straight for you, the orange one aims several cells ahead of you, and both take the occasional random turn.

When ghosts are on the field, a big flashing pellet appears every 6 foods. Eating it turns the ghosts blue and slower for about 60 moves. Touch a blue ghost to eat it. They flash white right before the effect ends, then respawn in a far corner a few moves after being eaten.

### Portals

On portal levels, two rings appear (orange and sky blue). Moving onto one exits from the other, and your body follows you through. Use them to escape, or watch out for what's waiting on the other side.

### Power-ups

One power-up spawns every 4 foods and stays for about 70 moves. Each has its own shape and color:

| Shape | Color | Power-up | Effect |
|---|---|---|---|
| Turtle | Green | **Slow-mo** | The whole game slows down for 40 moves |
| Diamond | Purple | **Phase** | Pass through your own body for 5 moves (your head turns purple). It won't end while you're still inside your body |
| Bar | Orange | **Shrink** | Lose 3 segments (never below 3) |
| Hexagon | Blue | **Shield** | Survive one fatal hit (see below) |
| Horseshoe | Pink | **Magnet** | Pulls food and bonus items within 7 cells toward you for 30 moves |

**Shield details:** it absorbs one hit from a wall, obstacle, your own body or a ghost, then you're safe for 3 moves. A wall hit wraps you to the opposite side, an obstacle hit smashes the block, and a ghost hit sends that ghost back home. Your head glows blue while the shield is up.

### Status bar

The bottom bar shows the current level, whether walls are deadly or wrap, and your active effects with countdowns (for example `SLOW 23  SHIELD  POWER 41`). Pickup messages appear at the top of the screen.

## Configuration

All the tuning values are constants at the top of `game.py`, so you can change the game without touching the logic. A few useful ones:

| Constant | What it does |
|---|---|
| `INITIAL_DELAY`, `MIN_DELAY`, `DELAY_STEP` | Starting speed, top speed, and speed-up per food (milliseconds per move) |
| `LEVEL_FOODS` | Foods needed per level |
| `GHOST_PERIOD`, `FRIGHT_PERIOD` | Ghost speed (moves every N steps, so higher is slower) |
| `GHOST_RANDOMNESS` | How often chasing ghosts take a random turn |
| `POWER_STEPS` | How long ghosts stay frightened |
| `SLOW_MOVES`, `PHASE_MOVES`, `MAGNET_MOVES` | Power-up durations |
| `POWERUP_INTERVAL`, `PELLET_INTERVAL`, `BONUS_INTERVAL` | How often each pickup spawns |
| `MAX_OBSTACLES` | Cap on static blocks |

To change what each level contains, edit the `level_config(level)` function.

## High score

Your best score is stored in `highscore.txt`, created next to `game.py`. Delete the file to reset it.

## Troubleshooting

**`ModuleNotFoundError: No module named 'tkinter'`**
Install the Tk bindings for your platform:

- Debian / Ubuntu: `sudo apt install python3-tk`
- Fedora: `sudo dnf install python3-tkinter`
- macOS (Homebrew): `brew install python-tk`
- Windows: re-run the Python installer and make sure "tcl/tk and IDLE" is ticked

**The window opens but the keys don't work**
Click the window once to give it keyboard focus.

**The window freezes or crashes on macOS**
The system Tk that ships with older macOS Python builds is unstable. Use Python from [python.org](https://www.python.org/downloads/) or a recent Homebrew Python with `python-tk` instead.

**The window is cut off on a small screen**
The window is 600 x 660. Lower `HEIGHT` at the top of `game.py` if your screen is short, though the bottom status bar may then be clipped.

## Project structure

```
game.py          # the whole game
highscore.txt    # created automatically after your first score
README.md
```

Inside `game.py`:

- `Snake`: movement, growth, shrinking
- `Ghost`: ghost state (the AI lives in `SnakeGame`)
- `SnakeGame`: input, levels, spawning, collisions, power-ups and the main loop
- `level_config()`: defines what each level adds

The game loop runs on a single Tk timer (`ontimer`) rather than a blocking `while` loop with `sleep`, so the window stays responsive.

## License

Add your preferred license here (for example MIT).
