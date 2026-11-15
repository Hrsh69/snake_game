import math
import os
import random
import time
import tkinter as tk
import turtle

# =====================================================================
#  CONFIGURATION  (all the knobs live here)
# =====================================================================
WIDTH = 600
HEIGHT = 660
GRID = 20

# Speed (milliseconds between moves)
INITIAL_DELAY = 150
MIN_DELAY = 60
DELAY_STEP = 3            # speed-up per food eaten
IDLE_DELAY = 50           # frame time while paused / game over / level banner

# Levels
LEVEL_FOODS = 8           # foods eaten per level
LEVEL_PAUSE_FRAMES = 30   # how long the "LEVEL N" banner stays (frames)

# Obstacles
MAX_OBSTACLES = 15
OBSTACLE_MIN_DIST = GRID * 4   # never spawn right in front of the head
MOVER_PERIOD = 2               # patrolling blocks move every N steps
MOVER_LIMIT_X = 260
MOVER_LIMIT_Y = 220

# Bonus food
BONUS_INTERVAL = 5
BONUS_LIFETIME = 45
BONUS_POINTS = 5

# Power-ups
POWERUP_INTERVAL = 4      # a power-up spawns every N foods
POWERUP_LIFETIME = 70     # moves before it disappears
SLOW_MOVES = 40
SLOW_FACTOR = 1.8         # frame delay multiplier while slow-mo is active
PHASE_MOVES = 5           # pass through your own body
MAGNET_MOVES = 30
MAGNET_RADIUS = GRID * 7
MAGNET_STEPS = 2          # cells per move the food is pulled
SHRINK_AMOUNT = 3
MIN_LENGTH = 3
INVULN_STEPS = 3          # safety window after a shield breaks

# Ghosts and power pellet
PELLET_INTERVAL = 6
PELLET_LIFETIME = 80
POWER_STEPS = 60          # how long ghosts stay frightened
GHOST_PERIOD = 2          # ghosts move every N steps (2 = half speed)
FRIGHT_PERIOD = 3         # frightened ghosts are even slower
GHOST_START_WAIT = 12     # steps ghosts stay frozen after a level starts
GHOST_RANDOMNESS = 0.25   # chance a chasing ghost takes a random turn
GHOST_RESPAWN_STEPS = 30
GHOST_POINTS = 10         # 10, 20, 40 for consecutive ghosts

# Play area (head centre must stay inside this)
BOUND_X = 280
BOUND_Y = 240

HIGHSCORE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "highscore.txt"
)

# Colors
BLACK = "#000000"
WHITE = "#FFFFFF"
YELLOW = "#FFFF00"
BODY = "#C9B800"
RED = "#D00000"
ORANGE_BLOCK = "#FF7A00"
CYAN = "#00FFFF"
BLUE = "#2121DE"
GREEN = "#22CC22"
PINK = "#FF77D4"
ORANGE_GHOST = "#FFA500"
FRIGHT = "#3060FF"
PORTAL_A = "#FF8C00"
PORTAL_B = "#4DC3FF"
PHASE_COLOR = "#B070FF"
SHIELD_COLOR = "#4DA6FF"

# kind: (shape, color, toast text)
POWERUPS = {
    "slow":   ("turtle",  "#00FF7F", "SLOW-MO!"),
    "phase":  ("diamond", PHASE_COLOR, "PHASE MODE!"),
    "shrink": ("bar",     "#FFA040", "SHRINK! -3"),
    "shield": ("hex",     SHIELD_COLOR, "SHIELD UP!"),
    "magnet": ("magnet",  "#FF5090", "MAGNET!"),
}

OPPOSITE = {"UP": "DOWN", "DOWN": "UP", "LEFT": "RIGHT", "RIGHT": "LEFT"}
OFFSETS = {
    "UP": (0, GRID),
    "DOWN": (0, -GRID),
    "LEFT": (-GRID, 0),
    "RIGHT": (GRID, 0),
}
HEADINGS = {"RIGHT": 0, "UP": 90, "LEFT": 180, "DOWN": 270}
CORNERS = [(-260, 220), (260, 220), (-260, -220), (260, -220)]


def level_config(level):
    """What each level adds. Odd levels from 3 on wrap; even levels have portals."""
    return {
        "wrap": level >= 3 and level % 2 == 1,
        "portals": level >= 2 and level % 2 == 0,
        "ghosts": 0 if level == 1 else (1 if level <= 3 else 2),
        "statics": min(MAX_OBSTACLES, (level - 1) * 2),
        "movers": 0 if level < 3 else min(3, level - 2),
    }


# =====================================================================
#  HELPERS
# =====================================================================

def load_high_score():
    try:
        with open(HIGHSCORE_FILE) as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return 0


def save_high_score(value):
    try:
        with open(HIGHSCORE_FILE, "w") as f:
            f.write(str(value))
    except OSError:
        pass


def cell(t):
    """Grid cell of a turtle as ints (avoids float comparison problems)."""
    return (int(round(t.xcor())), int(round(t.ycor())))


def sign(v):
    return (v > 0) - (v < 0)


def wrap_point(x, y):
    if x > BOUND_X:
        x = -BOUND_X
    elif x < -BOUND_X:
        x = BOUND_X
    if y > BOUND_Y:
        y = -BOUND_Y
    elif y < -BOUND_Y:
        y = BOUND_Y
    return x, y


def draw_edge(pen, x0, y0, x1, y1, dashed):
    if not dashed:
        pen.penup()
        pen.goto(x0, y0)
        pen.pendown()
        pen.goto(x1, y1)
        pen.penup()
        return
    length = math.hypot(x1 - x0, y1 - y0)
    ux, uy = (x1 - x0) / length, (y1 - y0) / length
    n = int(length // 10)
    for i in range(0, n, 2):
        a, b = i * 10, min((i + 1) * 10, length)
        pen.penup()
        pen.goto(x0 + ux * a, y0 + uy * a)
        pen.pendown()
        pen.goto(x0 + ux * b, y0 + uy * b)
    pen.penup()


def register_shapes(screen):
    """Custom shapes. Polygons are drawn 'upright'; markers use heading 90."""
    r = GRID / 2

    # Pac-Man: mouth toward +y, which turtle treats as "forward"
    pac = [(0, 0)]
    for a in range(130, 411, 10):
        rad = math.radians(a)
        pac.append((r * math.cos(rad), r * math.sin(rad)))
    screen.register_shape("pacman", tuple(pac))

    # Ghost: round top, wavy bottom
    ghost = [(r * math.cos(math.radians(a)), r * math.sin(math.radians(a)))
             for a in range(0, 181, 15)]
    ghost += [(-r, -r), (-r / 2, -r * 0.6), (0, -r), (r / 2, -r * 0.6), (r, -r)]
    screen.register_shape("ghost", tuple(ghost))

    screen.register_shape("diamond", ((0, 12), (9, 0), (0, -12), (-9, 0)))
    screen.register_shape("bar", ((-10, 3), (10, 3), (10, -3), (-10, -3)))
    screen.register_shape(
        "hex",
        tuple((11 * math.cos(math.radians(a)), 11 * math.sin(math.radians(a)))
              for a in range(0, 360, 60)),
    )
    screen.register_shape(
        "magnet",
        ((-10, 10), (-4, 10), (-4, -2), (4, -2), (4, 10), (10, 10),
         (10, -4), (5, -10), (-5, -10), (-10, -4)),
    )


# =====================================================================
#  SNAKE
# =====================================================================

class Snake:
    def __init__(self):
        self.segments = []
        self.chomp = False
        self.reset()

    @property
    def head(self):
        return self.segments[0]

    def reset(self):
        for seg in self.segments:
            seg.clear()
            seg.hideturtle()
        self.segments = []
        self.direction = "RIGHT"        # direction of the last actual move
        self.next_direction = "RIGHT"   # direction requested by the player
        for i in range(3):              # head at (0, 0), body trails left
            self._add_segment(-i * GRID, 0)
        self.head.color(YELLOW)
        self.head.shape("pacman")
        self.head.setheading(0)

    def _add_segment(self, x, y):
        seg = turtle.Turtle()
        seg.shape("circle")
        seg.color(BODY)
        seg.penup()
        seg.goto(x, y)
        self.segments.append(seg)

    def set_direction(self, new_dir):
        # Compare with the direction we last MOVED in, so two quick key
        # presses can't make the snake reverse into itself.
        if new_dir != OPPOSITE[self.direction]:
            self.next_direction = new_dir

    def move(self, wrap=False):
        self.direction = self.next_direction
        dx, dy = OFFSETS[self.direction]

        # Each segment takes the place of the one in front of it (tail first)
        for i in range(len(self.segments) - 1, 0, -1):
            self.segments[i].goto(self.segments[i - 1].pos())

        head = self.head
        x, y = head.xcor() + dx, head.ycor() + dy
        if wrap:
            x, y = wrap_point(x, y)
        head.goto(x, y)
        head.setheading(HEADINGS[self.direction])

        # Chomp animation: alternate open mouth / closed
        self.chomp = not self.chomp
        head.shape("pacman" if self.chomp else "circle")

    def grow(self):
        tail = self.segments[-1]
        self._add_segment(tail.xcor(), tail.ycor())

    def shrink(self, amount):
        removable = max(0, len(self.segments) - MIN_LENGTH)
        for _ in range(min(amount, removable)):
            seg = self.segments.pop()
            seg.clear()
            seg.hideturtle()


# =====================================================================
#  GHOST
# =====================================================================

class Ghost:
    def __init__(self, color, ahead):
        self.base_color = color
        self.ahead = ahead            # cells in front of the head it aims for
        self.t = turtle.Turtle()
        self.t.shape("ghost")
        self.t.color(color)
        self.t.penup()
        self.t.setheading(90)         # upright
        self.t.goto(1000, 1000)
        self.t.hideturtle()
        self.active = False           # part of the current level
        self.visible = False          # False while waiting to respawn
        self.respawn = 0
        self.direction = "LEFT"

    def place(self, pos):
        self.t.goto(pos)
        self.t.color(self.base_color)
        self.t.showturtle()
        self.visible = True
        self.respawn = 0
        self.direction = random.choice(list(OFFSETS))

    def enable(self, pos):
        self.active = True
        self.place(pos)

    def disable(self):
        self.active = False
        self.visible = False
        self.t.hideturtle()

    def eaten(self, delay):
        self.visible = False
        self.respawn = delay
        self.t.hideturtle()


# =====================================================================
#  GAME
# =====================================================================

class SnakeGame:
    def __init__(self):
        self.screen = turtle.Screen()
        self.screen.title("Pac-Snake")
        self.screen.bgcolor(BLACK)
        self.screen.setup(width=WIDTH, height=HEIGHT)
        self.screen.tracer(0)
        register_shapes(self.screen)

        self.border = self._make_pen()
        self.hud = self._make_pen()
        self.msg = self._make_pen()
        self.toast_pen = self._make_pen()
        self.status_pen = self._make_pen()

        self.snake = Snake()
        self.food = self._make_marker("circle", WHITE)
        self.bonus = self._make_marker("triangle", CYAN)
        self.pellet = self._make_marker("circle", WHITE)
        self.pellet.shapesize(1.6, 1.6, 1)
        self.powerup = self._make_marker("circle", WHITE)
        self.powerup.setheading(90)
        self.portals = [self._make_ring(PORTAL_A), self._make_ring(PORTAL_B)]
        self.portal_cells = [None, None]
        self.ghosts = [Ghost(PINK, 0), Ghost(ORANGE_GHOST, 4)]
        self.obstacles = []
        self.mover_dir = {}

        self.high_score = load_high_score()
        self.wrap = False
        self._bind_keys()

        self.state = "ready"   # ready -> running <-> paused -> over (+ levelup)
        self.reset()
        self._show_ready()

    # ----- setup helpers -----

    def _make_pen(self):
        pen = turtle.Turtle()
        pen.penup()
        pen.hideturtle()
        pen.color(WHITE)
        return pen

    def _make_marker(self, shape, color):
        t = turtle.Turtle()
        t.shape(shape)
        t.color(color)
        t.penup()
        t.goto(1000, 1000)
        t.hideturtle()
        return t

    def _make_ring(self, color):
        t = self._make_marker("circle", color)
        t.color(color, BLACK)
        t.shapesize(1.2, 1.2, 3)
        return t

    def _bind_keys(self):
        s = self.screen
        keys = {
            "UP": ("Up", "w", "W"),
            "DOWN": ("Down", "s", "S"),
            "LEFT": ("Left", "a", "A"),
            "RIGHT": ("Right", "d", "D"),
        }
        for direction, names in keys.items():
            for name in names:
                s.onkeypress(lambda d=direction: self.turn(d), name)
        for name in ("space", "p", "P"):
            s.onkeypress(self.toggle_pause, name)
        for name in ("r", "R"):
            s.onkeypress(self.restart, name)
        for name in ("q", "Q", "Escape"):
            s.onkeypress(self.quit, name)
        s.listen()

    # ----- game state -----

    def reset(self):
        self.snake.reset()
        self.score = 0
        self.foods_eaten = 0
        self.level = 1
        self.delay = INITIAL_DELAY
        self.new_record = False
        self.step_count = 0
        self.fx = {"slow": 0, "phase": 0, "magnet": 0, "shield": 0}
        self.invuln = 0
        self.power_ticks = 0
        self.ghost_chain = 0
        self.ghost_wait = 0
        self.bonus_ticks = 0
        self.pellet_ticks = 0
        self.powerup_ticks = 0
        self.powerup_kind = None
        self.toast_text = ""
        self.toast_until = 0
        self.level_frames = 0
        self._status_key = None
        self.toast_pen.clear()
        self.msg.clear()
        self._start_level()
        self._draw_hud()

    def _start_level(self):
        """Build the playfield for self.level."""
        cfg = level_config(self.level)
        self.wrap = cfg["wrap"]
        self._draw_border()

        # clear everything from the previous level
        for obs in self.obstacles:
            obs.clear()
            obs.hideturtle()
        self.obstacles.clear()
        self.mover_dir.clear()
        for item in (self.bonus, self.pellet, self.powerup):
            item.hideturtle()
        self.bonus_ticks = self.pellet_ticks = self.powerup_ticks = 0
        self.power_ticks = 0
        self.ghost_chain = 0

        # portals first so nothing else spawns on them
        self.portal_cells = [None, None]
        for p in self.portals:
            p.hideturtle()
        if cfg["portals"]:
            self._place_portals()

        for _ in range(cfg["statics"]):
            self._spawn_obstacle()
        for _ in range(cfg["movers"]):
            self._spawn_obstacle(mover=True)

        for i, g in enumerate(self.ghosts):
            if i < cfg["ghosts"]:
                g.enable(self._far_corner(i))
            else:
                g.disable()
        self.ghost_wait = GHOST_START_WAIT

        self.food.showturtle()
        self.food.goto(self._random_free_cell())

    def start(self):
        self.state = "running"
        self.msg.clear()

    def restart(self):
        self.reset()
        self.state = "ready"
        self._show_ready()

    def toggle_pause(self):
        if self.state == "ready":
            self.start()
        elif self.state == "running":
            self.state = "paused"
            self._show_message("PAUSED", ["SPACE / P to resume"], WHITE)
        elif self.state == "paused":
            self.state = "running"
            self.msg.clear()
        elif self.state == "over":
            self.restart()

    def turn(self, direction):
        if self.state == "ready":
            self.start()
        if self.state in ("running", "levelup"):
            self.snake.set_direction(direction)

    def quit(self):
        self.screen.bye()

    # ----- drawing -----

    def _draw_border(self):
        b = self.border
        b.clear()
        b.pensize(3)
        b.color(GREEN if self.wrap else BLUE)
        hx, hy = BOUND_X + GRID // 2, BOUND_Y + GRID // 2
        pts = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy), (-hx, -hy)]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            draw_edge(b, x0, y0, x1, y1, self.wrap)

    def _draw_hud(self):
        self.hud.clear()
        self.hud.goto(-BOUND_X - GRID // 2, 258)
        self.hud.write(f"Score: {self.score}", align="left",
                       font=("Courier", 18, "bold"))
        self.hud.goto(BOUND_X + GRID // 2, 258)
        self.hud.write(f"Best: {self.high_score}", align="right",
                       font=("Courier", 18, "bold"))

    def _draw_status(self):
        fx = self.fx
        parts = []
        if fx["slow"]:
            parts.append(f"SLOW {fx['slow']}")
        if fx["phase"]:
            parts.append(f"PHASE {fx['phase']}")
        if fx["magnet"]:
            parts.append(f"MAGNET {fx['magnet']}")
        if fx["shield"]:
            parts.append("SHIELD")
        if self.power_ticks:
            parts.append(f"POWER {self.power_ticks}")
        key = (self.level, self.wrap, tuple(parts))
        if key == self._status_key:
            return
        self._status_key = key

        p = self.status_pen
        p.clear()
        p.goto(-BOUND_X - GRID // 2, -295)
        p.write(f"LEVEL {self.level} {'WRAP' if self.wrap else 'WALLS'}",
                align="left", font=("Courier", 12, "bold"))
        p.goto(BOUND_X + GRID // 2, -295)
        p.write("  ".join(parts), align="right", font=("Courier", 12, "bold"))

    def _toast(self, text):
        self.toast_text = text
        self.toast_until = time.time() + 1.4
        self.toast_pen.clear()
        self.toast_pen.goto(0, 260)
        self.toast_pen.write(text, align="center", font=("Courier", 14, "bold"))

    def _show_message(self, title, lines, color, size=14):
        self.msg.clear()
        self.msg.color(color)
        self.msg.goto(0, 130)
        self.msg.write(title, align="center", font=("Courier", 32, "bold"))
        y = 100
        for line in lines:
            self.msg.goto(0, y)
            self.msg.write(line, align="center", font=("Courier", size, "normal"))
            y -= 22

    def _show_ready(self):
        self._show_message(
            "PAC-SNAKE",
            ["Arrows / WASD move   SPACE start / pause",
             "R restart   Q quit",
             "white +1   cyan triangle +5   big pellet = eat ghosts",
             "turtle SLOW   purple diamond PHASE   orange bar SHRINK",
             "blue hexagon SHIELD   pink U MAGNET   rings = PORTALS"],
            YELLOW, size=11,
        )

    def _show_level_banner(self):
        cfg = level_config(self.level)
        lines = ["Walls WRAP around!" if cfg["wrap"] else "Walls are deadly"]
        if cfg["portals"]:
            lines.append("Portals are open")
        if cfg["ghosts"]:
            lines.append(f"Ghosts: {cfg['ghosts']}  (grab the big pellet!)")
        if cfg["movers"]:
            lines.append(f"Patrolling blocks: {cfg['movers']}")
        self._show_message(f"LEVEL {self.level}", lines, YELLOW)

    # ----- spawning -----

    def _random_free_cell(self, min_head_dist=0):
        taken = {cell(s) for s in self.snake.segments}
        taken |= {cell(o) for o in self.obstacles}
        taken.add(cell(self.food))
        if self.bonus_ticks > 0:
            taken.add(cell(self.bonus))
        if self.pellet_ticks > 0:
            taken.add(cell(self.pellet))
        if self.powerup_ticks > 0:
            taken.add(cell(self.powerup))
        taken |= {c for c in self.portal_cells if c}
        head = self.snake.head

        while True:
            x = random.randint(-13, 13) * GRID
            y = random.randint(-11, 11) * GRID
            if (x, y) in taken:
                continue
            if min_head_dist and head.distance(x, y) < min_head_dist:
                continue
            return x, y

    def _spawn_obstacle(self, mover=False):
        obs = turtle.Turtle()
        obs.shape("square")
        obs.color(ORANGE_BLOCK if mover else RED)
        obs.penup()
        obs.goto(self._random_free_cell(min_head_dist=OBSTACLE_MIN_DIST))
        self.obstacles.append(obs)
        if mover:
            self.mover_dir[obs] = list(random.choice(list(OFFSETS.values())))

    def _remove_obstacle(self, obs):
        obs.clear()
        obs.hideturtle()
        if obs in self.obstacles:
            self.obstacles.remove(obs)
        self.mover_dir.pop(obs, None)

    def _place_portals(self):
        a = self._random_free_cell(min_head_dist=OBSTACLE_MIN_DIST)
        self.portal_cells[0] = a
        while True:
            b = self._random_free_cell(min_head_dist=OBSTACLE_MIN_DIST)
            if math.hypot(a[0] - b[0], a[1] - b[1]) >= GRID * 6:
                break
        self.portal_cells[1] = b
        for ring, pos in zip(self.portals, (a, b)):
            ring.goto(pos)
            ring.showturtle()

    def _spawn_bonus(self):
        self.bonus.goto(self._random_free_cell())
        self.bonus.showturtle()
        self.bonus_ticks = BONUS_LIFETIME

    def _spawn_pellet(self):
        self.pellet.goto(self._random_free_cell())
        self.pellet.showturtle()
        self.pellet_ticks = PELLET_LIFETIME

    def _spawn_powerup(self):
        kinds = [k for k in POWERUPS
                 if not (k == "shrink" and len(self.snake.segments) <= MIN_LENGTH + 2)]
        kind = random.choice(kinds)
        shape, color, _ = POWERUPS[kind]
        self.powerup_kind = kind
        self.powerup.shape(shape)
        self.powerup.color(color)
        self.powerup.goto(self._random_free_cell())
        self.powerup.showturtle()
        self.powerup_ticks = POWERUP_LIFETIME

    def _far_corner(self, index=0):
        head = self.snake.head
        blocked = {cell(o) for o in self.obstacles}
        corners = [c for c in CORNERS if c not in blocked] or CORNERS
        corners = sorted(corners, key=lambda c: -head.distance(c[0], c[1]))
        return corners[min(index, len(corners) - 1)]

    # ----- scoring -----

    def _add_score(self, points):
        self.score += points
        if self.score > self.high_score:
            if self.high_score > 0:
                self.new_record = True
            self.high_score = self.score
            save_high_score(self.high_score)
        self._draw_hud()

    # ----- hits and shield -----

    def _absorb(self):
        """Try to survive a lethal hit. True = survived."""
        if self.invuln > 0:
            return True
        if self.fx["shield"] > 0:
            self.fx["shield"] = 0
            self.invuln = INVULN_STEPS
            self._toast("SHIELD BROKE!")
            return True
        return False

    def _head_on_body(self):
        head = self.snake.head
        return any(head.distance(seg) < GRID / 2 for seg in self.snake.segments[1:])

    def _check_hits(self):
        """Return True if the snake died."""
        head = self.snake.head

        # walls
        if not self.wrap and (abs(head.xcor()) > BOUND_X or abs(head.ycor()) > BOUND_Y):
            if not self._absorb():
                return True
            head.goto(*wrap_point(head.xcor(), head.ycor()))

        # obstacles (a shield smashes the block you hit)
        for obs in list(self.obstacles):
            if head.distance(obs) < GRID / 2:
                if not self._absorb():
                    return True
                self._remove_obstacle(obs)

        # own body
        if self.fx["phase"] <= 0 and self._head_on_body():
            if not self._absorb():
                return True

        # ghosts
        for g in self.ghosts:
            if g.active and g.visible and head.distance(g.t) < GRID / 2:
                if self.power_ticks > 0:
                    self._eat_ghost(g)
                elif self._absorb():
                    g.eaten(GHOST_RESPAWN_STEPS)
                else:
                    return True
        return False

    def _eat_ghost(self, g):
        self.ghost_chain += 1
        points = GHOST_POINTS * (2 ** (self.ghost_chain - 1))
        self._add_score(points)
        g.eaten(GHOST_RESPAWN_STEPS)
        self._toast(f"GHOST +{points}!")

    # ----- portals -----

    def _teleport(self):
        a, b = self.portal_cells
        if not a or not b:
            return
        head = self.snake.head
        here = cell(head)
        if here == a:
            head.goto(b)
        elif here == b:
            head.goto(a)

    # ----- timers and effects -----

    def _tick_timers(self):
        fx = self.fx
        for key in ("slow", "magnet"):
            if fx[key] > 0:
                fx[key] -= 1
        if fx["phase"] > 0:
            fx["phase"] -= 1
            # never let the effect end while the head is inside the body
            if fx["phase"] == 0 and self._head_on_body():
                fx["phase"] = 1
        if self.invuln > 0:
            self.invuln -= 1
        if self.power_ticks > 0:
            self.power_ticks -= 1
            if self.power_ticks == 0:
                self.ghost_chain = 0

        if self.bonus_ticks > 0:
            self.bonus_ticks -= 1
            if self.bonus_ticks == 0:
                self.bonus.hideturtle()
        if self.pellet_ticks > 0:
            self.pellet_ticks -= 1
            if self.pellet_ticks == 0:
                self.pellet.hideturtle()
        if self.powerup_ticks > 0:
            self.powerup_ticks -= 1
            if self.powerup_ticks == 0:
                self.powerup.hideturtle()

    def _pull_toward(self, item, head):
        ix, iy = cell(item)
        hx, hy = cell(head)
        dx, dy = hx - ix, hy - iy
        if dx == 0 and dy == 0:
            return
        horizontal = (sign(dx) * GRID, 0)
        vertical = (0, sign(dy) * GRID)
        order = [horizontal, vertical] if abs(dx) >= abs(dy) else [vertical, horizontal]
        blocked = {cell(o) for o in self.obstacles}
        blocked |= {cell(s) for s in self.snake.segments[1:]}
        for sx, sy in order:
            if sx == 0 and sy == 0:
                continue
            nxt = (ix + sx, iy + sy)
            if nxt not in blocked:
                item.goto(nxt)
                return

    def _magnet(self):
        if self.fx["magnet"] <= 0:
            return
        head = self.snake.head
        targets = [self.food]
        if self.bonus_ticks > 0:
            targets.append(self.bonus)
        for item in targets:
            if head.distance(item) <= MAGNET_RADIUS:
                for _ in range(MAGNET_STEPS):
                    self._pull_toward(item, head)

    # ----- pickups -----

    def _pickups(self):
        """Handle everything the head touches. Returns True on level-up."""
        head = self.snake.head

        if self.bonus_ticks > 0 and head.distance(self.bonus) < GRID / 2:
            self.snake.grow()
            self.bonus_ticks = 0
            self.bonus.hideturtle()
            self._add_score(BONUS_POINTS)

        if self.pellet_ticks > 0 and head.distance(self.pellet) < GRID / 2:
            self.pellet_ticks = 0
            self.pellet.hideturtle()
            self.power_ticks = POWER_STEPS
            self.ghost_chain = 0
            self._add_score(2)
            self._toast("POWER! EAT THE GHOSTS")

        if self.powerup_ticks > 0 and head.distance(self.powerup) < GRID / 2:
            self._eat_powerup()

        if head.distance(self.food) < GRID / 2:
            return self._eat_food()
        return False

    def _eat_powerup(self):
        kind = self.powerup_kind
        self.powerup_ticks = 0
        self.powerup.hideturtle()
        self._toast(POWERUPS[kind][2])
        if kind == "slow":
            self.fx["slow"] = SLOW_MOVES
        elif kind == "phase":
            self.fx["phase"] = PHASE_MOVES
        elif kind == "shrink":
            self.snake.shrink(SHRINK_AMOUNT)
        elif kind == "shield":
            self.fx["shield"] = 1
        elif kind == "magnet":
            self.fx["magnet"] = MAGNET_MOVES

    def _eat_food(self):
        """Returns True if this meal started a new level."""
        self.snake.grow()
        self.foods_eaten += 1
        self._add_score(1)
        self.delay = max(MIN_DELAY, self.delay - DELAY_STEP)

        if self.foods_eaten % LEVEL_FOODS == 0:
            self._level_up()
            return True

        self.food.goto(self._random_free_cell())
        if self.foods_eaten % BONUS_INTERVAL == 0 and self.bonus_ticks == 0:
            self._spawn_bonus()
        if self.foods_eaten % POWERUP_INTERVAL == 0 and self.powerup_ticks == 0:
            self._spawn_powerup()
        if (self.foods_eaten % PELLET_INTERVAL == 0 and self.pellet_ticks == 0
                and any(g.active for g in self.ghosts)):
            self._spawn_pellet()
        return False

    def _level_up(self):
        self.level += 1
        self._start_level()
        self.state = "levelup"
        self.level_frames = LEVEL_PAUSE_FRAMES
        self._show_level_banner()
        self._toast(f"LEVEL {self.level}!")

    # ----- moving obstacles -----

    def _move_movers(self):
        if self.step_count % MOVER_PERIOD:
            return
        blocked = {cell(o) for o in self.obstacles}
        for obs, d in self.mover_dir.items():
            x, y = cell(obs)

            def ok(nx, ny):
                return (abs(nx) <= MOVER_LIMIT_X and abs(ny) <= MOVER_LIMIT_Y
                        and (nx, ny) not in blocked)

            nx, ny = x + d[0], y + d[1]
            if not ok(nx, ny):
                d[0], d[1] = -d[0], -d[1]   # bounce
                nx, ny = x + d[0], y + d[1]
                if not ok(nx, ny):
                    continue
            blocked.discard((x, y))
            blocked.add((nx, ny))
            obs.goto(nx, ny)

    # ----- ghosts -----

    def _move_ghosts(self):
        # respawn timers
        for g in self.ghosts:
            if g.active and not g.visible:
                g.respawn -= 1
                if g.respawn <= 0:
                    g.place(self._far_corner(0))

        if self.ghost_wait > 0:
            self.ghost_wait -= 1
            return
        frightened = self.power_ticks > 0
        period = FRIGHT_PERIOD if frightened else GHOST_PERIOD
        if self.step_count % period:
            return

        blocked = {cell(o) for o in self.obstacles}
        head = self.snake.head
        hx, hy = cell(head)
        ox, oy = OFFSETS[self.snake.direction]

        for g in self.ghosts:
            if not (g.active and g.visible):
                continue
            tx = hx + (ox // GRID) * g.ahead * GRID
            ty = hy + (oy // GRID) * g.ahead * GRID
            self._ghost_step(g, (tx, ty), blocked, frightened)

    def _ghost_step(self, g, target, blocked, frightened):
        gx, gy = cell(g.t)

        def free(nx, ny):
            return abs(nx) <= BOUND_X and abs(ny) <= BOUND_Y and (nx, ny) not in blocked

        options = []
        for d, (ox, oy) in OFFSETS.items():
            if d == OPPOSITE[g.direction]:
                continue
            if free(gx + ox, gy + oy):
                options.append((d, gx + ox, gy + oy))
        if not options:   # dead end: turn around
            d = OPPOSITE[g.direction]
            ox, oy = OFFSETS[d]
            if not free(gx + ox, gy + oy):
                return
            options = [(d, gx + ox, gy + oy)]

        def dist2(opt):
            return (opt[1] - target[0]) ** 2 + (opt[2] - target[1]) ** 2

        if random.random() < (0.5 if frightened else GHOST_RANDOMNESS):
            choice = random.choice(options)
        elif frightened:
            choice = max(options, key=dist2)    # run away
        else:
            choice = min(options, key=dist2)    # chase
        g.direction = choice[0]
        g.t.goto(choice[1], choice[2])

    # ----- visuals -----

    def _update_visuals(self):
        if self.fx["phase"] > 0:
            head_color = PHASE_COLOR
        elif self.fx["shield"] > 0 or self.invuln > 0:
            head_color = SHIELD_COLOR
        else:
            head_color = YELLOW
        self.snake.head.color(head_color)

        frightened = self.power_ticks > 0
        for g in self.ghosts:
            if not (g.active and g.visible):
                continue
            if frightened:
                flash = self.power_ticks <= 12 and self.power_ticks % 2 == 0
                g.t.color(WHITE if flash else FRIGHT)
            else:
                g.t.color(g.base_color)

        if self.pellet_ticks > 0:
            self.pellet.color(WHITE if self.step_count % 2 else "#8888FF")

    # ----- main loop -----

    def _game_over(self):
        self.state = "over"
        lines = [f"Score: {self.score}   Best: {self.high_score}",
                 f"Level {self.level}   Foods {self.foods_eaten}"]
        if self.new_record:
            lines.append("NEW HIGH SCORE!")
        lines.append("R / SPACE to play again   Q to quit")
        self._show_message("GAME OVER", lines, "#FF3030")

    def _step(self):
        self.step_count += 1
        self.snake.move(self.wrap)
        self._teleport()

        if self._check_hits():
            self._game_over()
            return

        self._tick_timers()
        self._magnet()
        if self._pickups():
            return   # level up: skip the rest of this step

        self._move_movers()
        self._move_ghosts()
        if self._check_hits():
            self._game_over()
            return
        self._update_visuals()

    def _frame_delay(self):
        d = self.delay
        if self.fx["slow"] > 0:
            d = int(d * SLOW_FACTOR)
        return d

    def tick(self):
        # One single timer chain for the whole program: it keeps running
        # (idling) when paused / game over, so a restart can never start a
        # second chain and double the speed.
        try:
            if self.state == "running":
                self._step()
            elif self.state == "levelup":
                self.level_frames -= 1
                if self.level_frames <= 0:
                    self.state = "running"
                    self.msg.clear()

            if self.toast_text and time.time() > self.toast_until:
                self.toast_pen.clear()
                self.toast_text = ""

            self._draw_status()
            self.screen.update()
            delay = self._frame_delay() if self.state == "running" else IDLE_DELAY
            self.screen.ontimer(self.tick, delay)
        except (turtle.Terminator, tk.TclError):
            pass  # window was closed

    def run(self):
        self.tick()
        self.screen.mainloop()


def main():
    SnakeGame().run()


if __name__ == "__main__":
    main()