from collections import deque
import sys

try:
    import pygame  # type: ignore[import-not-found]
except ImportError:
    pygame = None

""" I will be making the following assumptions

- the map is a fixed size, such as 10×10 or 12×12
- every tile is either grass, player, treasure or wall
- there is exactly one player
- there is exactly one treasure
- the player can move on grass
- the treasure must be reachable

p = player
g = grass
w = wall
t = treasure
"""

seed = 1500
size = 20

# I changed the formula since that's obviously not random enough while still being deterministic. For now I'll use a mixed LCG

def formula(x, a, c, m):
    return (a * x + c) % m


""" With a mixed LCG, there's rules to adhere to in order to get the maximum period (Most numbers without repeating a cycle):

- gcd(c, m) = 1. In other words c and m are coprime
- a - 1 should be divisible by all the prime factors of m
- If m is divisible by 4, a - 1 should also be divisible by 4

"""

grid = []

#Step 0: Initialize the grid
for i in range(size):
    row = []
    for j in range(size):
        row.append("Unknown")
    grid.append(row)

# Step 1: All tiles become grass
for i in range(size):
    for j in range(size):
        grid[i][j] = "g"

def generate_states():
    state = seed
    for _ in range(size ** 2):
        state = formula(state, 5, 1, 2**32)
        yield state

# We call the generate states function and see if it should be a wall. Note that we should avoid modding by 2,4 and 8 as those are powers of two and with Mixed LCG's, this may not be random
def is_wall(state):
    return state % 9 == 0

def is_player(state):
    return state % 150 == 0


def is_treasure(state):
    return state % 170 == 0


# Actually place the walls
for index, state in enumerate(generate_states()):
    if is_wall(state):
        x, y = divmod(index, size)
        grid[x][y] = "w"

def player_in_map():
    for i in range(size):
        for j in range(size):
            if grid[i][j] == "p":
                return True
    return False


def treasure_in_map():
    for i in range(size):
        for j in range(size):
            if grid[i][j] == "t":
                return True
    return False

def nth_grass_position(n):
    count = 0
    for i in range(0, size):
        for j in range(0, size):
            if grid[i][j] == "g":
                if count == n:
                    return (i, j)
                count += 1
    return None

# To deterministically pick a player and treasure location, we can simply do something like seed % (total of grass places) and then use that to decide where to put the player/treasure
grass_spots = sum(row.count("g") for row in grid)
state_gen = generate_states()
player_seed = next(state_gen) % grass_spots

player_pos = nth_grass_position(player_seed)

if player_pos is not None:
    px, py = player_pos
    grid[px][py] = "p"

# Do the same for the treasure
treasure_spots = sum(row.count("g") for row in grid)
treasure_seed = next(state_gen) % treasure_spots

treasure_pos = nth_grass_position(treasure_seed)

if treasure_pos is not None:
    tx, ty = treasure_pos
    grid[tx][ty] = "t"

# Verify map has 1 player, 1 treasure and that the treasure is reachable
def verify_map(grid):
    local_size = len(grid)
    player_pos = None
    treasure_pos = None
    player_count = 0
    treasure_count = 0

    for i in range(local_size):
        for j in range(local_size):
            if grid[i][j] == "p":
                player_count += 1
                player_pos = (i, j)
            elif grid[i][j] == "t":
                treasure_count += 1
                treasure_pos = (i, j)

    # Must contain exactly one player and one treasure.
    if player_count != 1 or treasure_count != 1:
        return False

    if player_pos is None or treasure_pos is None:
        return False

    queue = deque([player_pos])
    visited = {player_pos}
    directions = ((1, 0), (-1, 0), (0, 1), (0, -1))

    while queue:
        x, y = queue.popleft()

        if (x, y) == treasure_pos:
            return True

        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if 0 <= nx < local_size and 0 <= ny < local_size:
                if (nx, ny) not in visited and grid[nx][ny] != "w":
                    visited.add((nx, ny))
                    queue.append((nx, ny))

    return False

def draw_map_pygame(grid):
    if pygame is None:
        print("Pygame is not installed. Run: pip install pygame")
        return

    hud_height = 88
    min_window_w = 420
    min_window_h = 420
    min_map_size = 5
    max_map_size = 80
    seed_step = 10
    key_repeat_delay_ms = 350
    key_repeat_interval_ms = 250  # 4 repeats/second
    backspace_repeat_interval_ms = 70
    colors = {
        "g": (34, 139, 34),      # grass: green
        "w": (128, 128, 128),    # wall: grey
        "p": (0, 255, 255),      # player: cyan
        "t": (255, 215, 0),      # treasure: gold
    }

    pygame.init()
    pygame.display.set_caption("Procedural Map")
    current_size = size
    initial_w = max(min_window_w, current_size * 32)
    initial_h = max(min_window_h, current_size * 32 + hud_height)
    screen = pygame.display.set_mode((initial_w, initial_h), pygame.RESIZABLE)
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 20)

    current_seed = seed
    seed_input = str(current_seed)
    next_repeat_ms = {}

    def apply_seed_delta(delta):
        nonlocal current_seed, seed_input
        current_seed += delta
        seed_input = str(current_seed)

    def build_map_from_seed(local_seed, map_size):
        local_grid = [["g" for _ in range(map_size)] for _ in range(map_size)]

        state = local_seed
        states = []
        for _ in range(map_size ** 2):
            state = formula(state, 5, 1, 2**32)
            states.append(state)

        for index, value in enumerate(states):
            if is_wall(value):
                x, y = divmod(index, map_size)
                local_grid[x][y] = "w"

        grass_cells = [(i, j) for i in range(map_size) for j in range(map_size) if local_grid[i][j] == "g"]
        if not grass_cells:
            return local_grid

        player_index = states[0] % len(grass_cells)
        px, py = grass_cells[player_index]
        local_grid[px][py] = "p"

        grass_cells = [(i, j) for i in range(map_size) for j in range(map_size) if local_grid[i][j] == "g"]
        if grass_cells:
            treasure_index = states[1] % len(grass_cells)
            tx, ty = grass_cells[treasure_index]
            local_grid[tx][ty] = "t"

        return local_grid

    grid = build_map_from_seed(current_seed, current_size)
    is_possible = verify_map(grid)

    running = True
    while running:
        seed_changed = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                new_w = max(min_window_w, event.w)
                new_h = max(min_window_h, event.h)
                screen = pygame.display.set_mode((new_w, new_h), pygame.RESIZABLE)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    apply_seed_delta(seed_step)
                    seed_changed = True
                    next_repeat_ms[event.key] = pygame.time.get_ticks() + key_repeat_delay_ms
                elif event.key == pygame.K_DOWN:
                    apply_seed_delta(-seed_step)
                    seed_changed = True
                    next_repeat_ms[event.key] = pygame.time.get_ticks() + key_repeat_delay_ms
                elif event.key == pygame.K_RIGHT:
                    apply_seed_delta(1)
                    seed_changed = True
                    next_repeat_ms[event.key] = pygame.time.get_ticks() + key_repeat_delay_ms
                elif event.key == pygame.K_LEFT:
                    apply_seed_delta(-1)
                    seed_changed = True
                    next_repeat_ms[event.key] = pygame.time.get_ticks() + key_repeat_delay_ms
                elif event.key == pygame.K_BACKSPACE:
                    if seed_input:
                        seed_input = seed_input[:-1]
                    next_repeat_ms[event.key] = pygame.time.get_ticks() + key_repeat_delay_ms
                elif event.key == pygame.K_LEFTBRACKET:
                    current_size = max(min_map_size, current_size - 1)
                    seed_changed = True
                    next_repeat_ms[event.key] = pygame.time.get_ticks() + key_repeat_delay_ms
                elif event.key == pygame.K_RIGHTBRACKET:
                    current_size = min(max_map_size, current_size + 1)
                    seed_changed = True
                    next_repeat_ms[event.key] = pygame.time.get_ticks() + key_repeat_delay_ms
                elif event.key == pygame.K_RETURN:
                    if seed_input not in ("", "-"):
                        current_seed = int(seed_input)
                        seed_input = str(current_seed)
                        seed_changed = True
                else:
                    if event.unicode.isdigit():
                        if seed_input == "0":
                            seed_input = event.unicode
                        else:
                            seed_input += event.unicode
                    elif event.unicode == "-":
                        if seed_input == "":
                            seed_input = "-"
            elif event.type == pygame.KEYUP:
                if event.key in next_repeat_ms:
                    del next_repeat_ms[event.key]

        now = pygame.time.get_ticks()
        pressed = pygame.key.get_pressed()
        hold_actions = {
            pygame.K_UP: seed_step,
            pygame.K_RIGHT: 1,
            pygame.K_DOWN: -seed_step,
            pygame.K_LEFT: -1,
        }

        for key, delta in hold_actions.items():
            if pressed[key] and key in next_repeat_ms and now >= next_repeat_ms[key]:
                apply_seed_delta(delta)
                seed_changed = True
                next_repeat_ms[key] = now + key_repeat_interval_ms

        size_hold_actions = {
            pygame.K_LEFTBRACKET: -1,
            pygame.K_RIGHTBRACKET: 1,
        }

        for key, delta in size_hold_actions.items():
            if pressed[key] and key in next_repeat_ms and now >= next_repeat_ms[key]:
                old_size = current_size
                current_size = max(min_map_size, min(max_map_size, current_size + delta))
                if current_size != old_size:
                    seed_changed = True
                next_repeat_ms[key] = now + key_repeat_interval_ms

        if pressed[pygame.K_BACKSPACE] and pygame.K_BACKSPACE in next_repeat_ms:
            if now >= next_repeat_ms[pygame.K_BACKSPACE]:
                if seed_input:
                    seed_input = seed_input[:-1]
                next_repeat_ms[pygame.K_BACKSPACE] = now + backspace_repeat_interval_ms

        if seed_changed:
            grid = build_map_from_seed(current_seed, current_size)
            is_possible = verify_map(grid)

        screen.fill((18, 18, 18))
        info = "up/down +/-10 | left/right +/-1 | [ ] map size | type seed + Enter"
        screen.blit(font.render(info, True, (235, 235, 235)), (8, 8))
        seed_text = f"seed={current_seed} | input={seed_input or '_'} | map_size={current_size}"
        screen.blit(font.render(seed_text, True, (235, 235, 235)), (8, 30))

        if is_possible:
            status_text = "MAP POSSIBLE"
            status_color = (110, 230, 140)
        else:
            status_text = "MAP NOT POSSIBLE"
            status_color = (255, 90, 90)

        screen.blit(font.render(status_text, True, status_color), (8, 52))

        screen_w, screen_h = screen.get_size()
        grid_area_h = screen_h - hud_height
        tile_size = max(1, min(screen_w // current_size, grid_area_h // current_size))
        map_w = tile_size * current_size
        map_h = tile_size * current_size
        origin_x = (screen_w - map_w) // 2
        origin_y = hud_height + (grid_area_h - map_h) // 2

        for i in range(current_size):
            for j in range(current_size):
                tile = grid[i][j]
                color = colors.get(tile, (0, 0, 0))
                rect = (origin_x + j * tile_size, origin_y + i * tile_size, tile_size, tile_size)
                pygame.draw.rect(screen, color, rect)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


#Print the map
players = 0
treasures = 0
for i in range(size):
    for j in range(size):
        print(grid[i][j], end=" ")
    print()

draw_map_pygame(grid)


