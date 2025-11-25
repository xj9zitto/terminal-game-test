#!/usr/bin/env python3
"""
Compact: raycaster w/ safe multi-key hold, slower movement & rotation.

Behavior:
- Uses last-seen timestamps for keys (HOLD window) so W+A/D works reliably.
- Movement model: instant step per-frame (normalized diagonal) like your chosen version.
- Slower defaults for movement and rotation.
- Keeps colors, tilt, and safe drawing (never writes last column).
"""
import math
import curses
import time

# -----------------------------
# CONFIG (tweak these)
# -----------------------------
KEY_HOLD_TIME = 0.32   # seconds: how long a key counts as "held" after last repeat
MOVE_STEP = 0.06       # per-frame step (smaller = slower)
ROT_STEP  = 0.04       # per-frame rotation (radians)
TILT_STEP = 1          # rows per tilt press
TILT_LIMIT = 10

# -----------------------------
# MAP (unchanged)
# -----------------------------
MAP = [
    "############",
    "#..........#",
    "#..........#",
    "#..........#",
    "#..........#",
    "############",
]

# -----------------------------
# ASCII textures & shading
# -----------------------------
TEXTURE = [
    "@@###%%%***",
    "@###%%%***+",
    "##%%**++---",
    "#%%**++---.",
    "%%%**+---..",
    "%%**+--....",
    "%**+--.....",
    "**+--......",
]
TEX_W = len(TEXTURE[0])
TEX_H = len(TEXTURE)

CEILING = ".-+*%#@"
FLOOR   = ".-+*%#@"

# -----------------------------
# Player state
# -----------------------------
player_x = 3.0
player_y = 3.0
player_angle = 0.0
camera_tilt = 0
FOV = math.radians(60)

# -----------------------------
# key handling (last-seen timestamps)
# -----------------------------
last_seen = {}  # key_name -> last time it was seen

# map curses key codes to names
KEYMAP = {
    ord('w'): 'w', ord('a'): 'a', ord('s'): 's', ord('d'): 'd',
    ord('q'): 'q',
    curses.KEY_LEFT: 'left', curses.KEY_RIGHT: 'right',
    curses.KEY_UP: 'up', curses.KEY_DOWN: 'down'
}

def is_held(name, now):
    """Return True if key name is considered held in the KEY_HOLD_TIME window."""
    t = last_seen.get(name, 0.0)
    return (now - t) <= KEY_HOLD_TIME

# -----------------------------
# Raycaster (as you used)
# -----------------------------
def cast_ray(px, py, angle):
    sin_a = math.sin(angle)
    cos_a = math.cos(angle)

    for d in range(1, 400):
        x = px + cos_a * d * 0.03
        y = py + sin_a * d * 0.03

        if int(y) < 0 or int(y) >= len(MAP) or int(x) < 0 or int(x) >= len(MAP[0]):
            return d * 0.03, x, y, False

        if MAP[int(y)][int(x)] == "#":
            return d * 0.03, x, y, abs(cos_a) > abs(sin_a)

    return 15.0, px, py, False

# -----------------------------
# Rendering
# -----------------------------
def render_scene(stdscr):
    h, w = stdscr.getmaxyx()
    max_col = max(0, w - 1)  # we will iterate to w-1 (avoid last column)
    horizon = h // 2

    for col in range(max_col):
        ray_angle = player_angle - FOV/2 + (col / float(w)) * FOV
        dist, hx, hy, hit_vertical = cast_ray(player_x, player_y, ray_angle)

        wall_h = int(h / (dist + 1e-6))
        start = max(0, horizon - wall_h//2 - camera_tilt)
        end   = min(h, horizon + wall_h//2 - camera_tilt)

        tex_x = (hy - int(hy)) if hit_vertical else (hx - int(hx))
        tx = min(TEX_W - 1, max(0, int(tex_x * TEX_W)))

        # ceiling
        for row in range(0, start):
            dy = horizon - row + camera_tilt
            lvl = 0 if dy <= 0 else min(int((h / (dy + 1)) / 2), len(CEILING) - 1)
            ch = CEILING[lvl]
            stdscr.addstr(row, col, ch, curses.color_pair(3))

        # wall
        for row in range(start, end):
            rel = (row - start) / max(1, (end - start))
            ty = min(TEX_H - 1, int(rel * TEX_H))
            ch = TEXTURE[ty][tx]
            if ty < TEX_H * 0.33:
                color = curses.color_pair(1)
            elif ty < TEX_H * 0.66:
                color = curses.color_pair(2)
            else:
                color = curses.color_pair(4)
            stdscr.addstr(row, col, ch, color)

        # floor
        for row in range(end, h):
            dy = row - horizon + camera_tilt
            lvl = 0 if dy <= 0 else min(int((h / (dy + 1)) / 2), len(FLOOR) - 1)
            ch = FLOOR[lvl]
            stdscr.addstr(row, col, ch, curses.color_pair(5))

# -----------------------------
# Main loop
# -----------------------------
def draw(stdscr):
    global player_x, player_y, player_angle, camera_tilt, last_seen

    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.scrollok(False)
    stdscr.clearok(False)
    stdscr.keypad(True)

    # init colors
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_YELLOW, -1)
    curses.init_pair(2, curses.COLOR_WHITE, -1)
    curses.init_pair(4, curses.COLOR_MAGENTA, -1)
    curses.init_pair(3, curses.COLOR_CYAN, -1)
    curses.init_pair(5, curses.COLOR_GREEN, -1)

    # initial render
    stdscr.erase()
    render_scene(stdscr)
    stdscr.refresh()

    while True:
        now = time.time()

        # consume all pending key events this frame so repeats update last_seen
        k = stdscr.getch()
        while k != -1:
            if k in KEYMAP:
                last_seen[KEYMAP[k]] = now
            else:
                # accept ascii lowercase delivered as numbers
                if 0 <= k < 256:
                    ch = chr(k)
                    code = ord(ch)
                    if code in KEYMAP:
                        last_seen[KEYMAP[code]] = now
            k = stdscr.getch()

        # derive held/pressed state
        held = {
            'w': is_held('w', now),
            's': is_held('s', now),
            'a': is_held('a', now),
            'd': is_held('d', now),
            'left': is_held('left', now),
            'right': is_held('right', now),
            'up': is_held('up', now),
            'down': is_held('down', now),
            'q': is_held('q', now)
        }

        # quit
        if held['q']:
            return

        changed = False

        # rotation (held-continuous)
        if held['left']:
            player_angle -= ROT_STEP
            changed = True
        if held['right']:
            player_angle += ROT_STEP
            changed = True

        # tilt
        if held['up']:
            camera_tilt = max(-TILT_LIMIT, camera_tilt - TILT_STEP)
            changed = True
        if held['down']:
            camera_tilt = min(TILT_LIMIT, camera_tilt + TILT_STEP)
            changed = True

        # movement (use held keys, normalized diagonal)
        move_x = 0.0
        move_y = 0.0

        if held['w']:
            move_x += math.cos(player_angle)
            move_y += math.sin(player_angle)
        if held['s']:
            move_x -= math.cos(player_angle)
            move_y -= math.sin(player_angle)
        if held['a']:
            move_x += math.sin(player_angle)
            move_y -= math.cos(player_angle)
        if held['d']:
            move_x -= math.sin(player_angle)
            move_y += math.cos(player_angle)

        if move_x != 0.0 or move_y != 0.0:
            L = math.hypot(move_x, move_y)
            move_x /= L
            move_y /= L

            nx = player_x + move_x * MOVE_STEP
            ny = player_y + move_y * MOVE_STEP

            # collision check & bounds
            if 0 <= int(ny) < len(MAP) and 0 <= int(nx) < len(MAP[0]) and MAP[int(ny)][int(nx)] == ".":
                player_x = nx
                player_y = ny
                changed = True

        # redraw if anything changed
        if changed:
            stdscr.erase()
            render_scene(stdscr)
            stdscr.refresh()

        time.sleep(0.01)

if __name__ == "__main__":
    curses.wrapper(draw)
