from collections import deque
import math
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

New: b = building
"""

seed = 1500
size = 20

# The formula we're using here is called the Mixed Congruential Generator (MCG), the backbone of all the rest of the code. This will form the pseudorandomness of the maps
def formula(x, a, c, m):
    return (a * x + c) % m

""" With a mixed LCG, there's rules to adhere to in order to get the maximum period (Most numbers without repeating a cycle):

- gcd(c, m) = 1. In other words c and m are coprime
- a - 1 should be divisible by all the prime factors of m
- If m is divisible by 4, a - 1 should also be divisible by 4

"""

def generate_states(seed, map_size):
    state = seed
    for _ in range(map_size ** 2):
        state = formula(state, 5, 1, 2**32)
        yield state

# We call the generate states function and see if it should be a wall. Note that we should avoid modding by 2,4 and 8 as those are powers of two and with Mixed LCG's, this may not be random
def is_wall(state):
    return state % 9 == 0

def generate_map(local_seed, map_size):
    grid = []

    #Step 0: Initialize the grid
    for i in range(map_size):
        row = []
        for j in range(map_size):
            row.append("Unknown")
        grid.append(row)

    # Step 1: All tiles become grass
    for i in range(map_size):
        for j in range(map_size):
            grid[i][j] = "g"

    # Step 2: Place the walls
    for index, state in enumerate(generate_states(local_seed, map_size)):
        if is_wall(state):
            x, y = divmod(index, map_size)
            grid[x][y] = "w"

    def nth_grass_position(n):
        count = 0
        for i in range(0, map_size):
            for j in range(0, map_size):
                if grid[i][j] == "g":
                    if count == n:
                        return (i, j)
                    count += 1
        return None
    
    def get_all_valid_building_spots(size):
        # To stop the buildings spawning right on the edge, we can slightly change the parameters in range()
        building_spots = []
        for i in range(1, map_size - size):
            for j in range(1, map_size - size):
                if grid[i][j] == "g":
                    building_spots.append((i, j))
        return building_spots

    # To deterministically pick player, building and treasure spots, we can simply do something like seed % (total of grass places) and then use that to decide where to put the player/treasure.
    # For the buildings, I only want them to spawn in if the grid is 20x20 or larger.
    state_gen = generate_states(local_seed, map_size)
    if map_size >= 20:
        grass_spots = sum(row.count("g") for row in grid)
        building_seed = next(state_gen) % grass_spots

        building_size = (next(state_gen) % 3) + 4 # If 0 -> 4x4, if 1 -> 5x5, if 2 -> 6x6

        # Decide where to place the building once we have the size of it
        available_building_spots = nth_grass_position(building_seed)
       
        valid_building_spots = get_all_valid_building_spots(building_size)
        bx, by = valid_building_spots[next(state_gen) % len(valid_building_spots)]

        # Now we build the building. To work out how many total building spots have been placed, we can use the nth term an = 4n-4. But to exclude the corners, we subtract 4 more, so 8 total.
        total_building_spots = 4 * building_size - 8
        building_entrance = (next(state_gen) % total_building_spots)
        count = 0
        for i in range(building_size):
            for j in range(building_size):
                # One thing I noticed during testing is that walls can sometimes block access to, or be inside, the building. As such I'll replace all walls in the building with grass, then switch the block outside the entrance to grass
                if grid[bx+i][by+j] == "w":
                    grid[bx+i][by+j] = "g"
                if i == 0 or i == building_size - 1 or j == 0 or j == building_size - 1:
                    grid[bx+i][by+j] = "b"

                    # If not a corner
                    if not (i == 0 and j == 0) and not (i == 0 and j == building_size - 1) and not (i == building_size - 1 and j == 0) and not (i == building_size - 1 and j == building_size - 1):

                        if count == building_entrance:
                            grid[bx+i][by+j] = "g"
                            # The plan here to prevent walls preventing us from entering the building from the outside is to find out what edge of the building we're on, and replace any possible blockages with grass
                            if i == 0:
                                grid[bx+i-1][by+j] = "g"
                            elif i == building_size - 1:
                                grid[bx+i+1][by+j] = "g"
                            elif j == 0:
                                grid[bx+i][by+j-1] = "g"
                            elif j == building_size - 1:
                                grid[bx+i][by+j+1] = "g"

                        count += 1

                

    grass_spots = sum(row.count("g") for row in grid)
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

    return grid

grid = generate_map(seed, size)

def verify_map(grid):
    """
    Verify map meets all the following: 
    - 1 player 
    - 1 treasure 
    - The treasure is reachable
    - There is a set distance between player and treasure to stop very easy maps
    - The player can access the entrance of all buildings 
    """
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
        return False, "need exactly 1 player and 1 treasure"

    if player_pos is None or treasure_pos is None:
        return False, "player or treasure position missing"
    
    # Set the minimum shortest path to be at least 2/3 of local_size
    min_shortest_path = math.ceil((2 * local_size) / 3)

    queue = deque([(player_pos, 0)])
    visited = {player_pos}
    directions = ((1, 0), (-1, 0), (0, 1), (0, -1))

    while queue:
        (x, y), distance = queue.popleft()

        if (x, y) == treasure_pos:
            if distance >= min_shortest_path:
                return True, ""
            return False, f"shortest path {distance} < required {min_shortest_path}"

        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if 0 <= nx < local_size and 0 <= ny < local_size:
                if (nx, ny) not in visited and grid[nx][ny] not in ("w", "b"):
                    visited.add((nx, ny))
                    queue.append(((nx, ny), distance + 1))

    return False, "treasure is unreachable"

def on_regenerate_button_pressed(seed, map_size, grid):

    # First thing to do is remove the player and treasure from current map
    for i in range(map_size):
        for j in range(map_size):
            if grid[i][j] == "p":
                grid[i][j] = "g"
            elif grid[i][j] == "t":
                grid[i][j] = "g"

    def nth_grass_position(n):
            count = 0
            for i in range(0, map_size):
                for j in range(0, map_size):
                    if grid[i][j] == "g":
                        if count == n:
                            return (i, j)
                        count += 1
            return None

    # Say a user inputs a seed and an invalid world is generated. I think the best way to fix this is to have it, three times, regenerate different things. In the first iteration we can move the player and the treasure and that should be enough for most times.
    state_gen = generate_states(seed, map_size)

    grass_spots = sum(row.count("g") for row in grid)
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

    if verify_map(grid)[0]:
        return grid

    return "New generated map is Invalid. Maybe try again?"

def draw_map_pygame(grid):
    if pygame is None:
        print("Pygame is not installed. Run: pip install pygame")
        return

    hud_height = 124
    min_window_w = 860
    min_window_h = 600
    min_map_size = 5
    max_map_size = 80
    seed_step = 10
    key_repeat_delay_ms = 350
    key_repeat_interval_ms = 250  # Increases value by 4 times a second
    backspace_repeat_interval_ms = 70
    colors = {
        "g": (34, 139, 34),      # grass: green
        "w": (128, 128, 128),    # wall: grey
        "b": (139, 0, 0),        # building: dark red
        "p": (0, 255, 255),      # player: cyan
        "t": (255, 215, 0),      # treasure: gold
    }

    pygame.init()
    pygame.display.set_caption("Procedural Map Generator")
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

    grid = generate_map(current_seed, current_size)
    is_possible, map_reason = verify_map(grid)
    error_bubble_text = ""
    error_bubble_until_ms = 0
    action_bubble_text = ""
    action_bubble_color = (40, 90, 150)
    action_bubble_until_ms = 0
    regenerate_count = 0

    regenerate_button_rect = None
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
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if not is_possible and regenerate_button_rect is not None:
                    if regenerate_button_rect.collidepoint(event.pos):
                        action_bubble_text = "Regenerating..."
                        action_bubble_color = (40, 90, 150)
                        action_bubble_until_ms = pygame.time.get_ticks() + 1000

                        regenerate_count += 1
                        result = on_regenerate_button_pressed(current_seed + regenerate_count, current_size, grid)
                        if isinstance(result, list):
                            grid = result
                            is_possible, map_reason = verify_map(grid)
                            error_bubble_text = ""
                            error_bubble_until_ms = 0
                            action_bubble_text = "New locations generated"
                            action_bubble_color = (50, 120, 70)
                            action_bubble_until_ms = pygame.time.get_ticks() + 1500
                        else:
                            error_bubble_text = str(result) if result else "Invalid Map, maybe try again?"
                            error_bubble_until_ms = pygame.time.get_ticks() + 3000

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
            regenerate_count = 0
            grid = generate_map(current_seed, current_size)
            is_possible, map_reason = verify_map(grid)
            error_bubble_text = ""
            error_bubble_until_ms = 0

        screen.fill((18, 18, 18))
        info = "up/down +/-10 | left/right +/-1 | [ ] map size | type seed + Enter"
        screen.blit(font.render(info, True, (235, 235, 235)), (8, 8))
        seed_text = f"seed={current_seed} | input={seed_input or '_'} | map_size={current_size}"
        screen.blit(font.render(seed_text, True, (235, 235, 235)), (8, 30))

        if is_possible:
            status_text = "MAP POSSIBLE"
            status_color = (110, 230, 140)
        else:
            status_text = f"MAP NOT POSSIBLE - {map_reason}"
            status_color = (255, 90, 90)

        screen.blit(font.render(status_text, True, status_color), (8, 52))

        if not is_possible:
            button_w = 200
            button_h = 30
            button_x = screen.get_width() - button_w - 12
            button_y = 84
            regenerate_button_rect = pygame.Rect(button_x, button_y, button_w, button_h)
            pygame.draw.rect(screen, (60, 60, 60), regenerate_button_rect, border_radius=6)
            pygame.draw.rect(screen, (210, 210, 210), regenerate_button_rect, width=1, border_radius=6)
            button_text = font.render("Regenerate World", True, (240, 240, 240))
            text_rect = button_text.get_rect(center=regenerate_button_rect.center)
            screen.blit(button_text, text_rect)

        if error_bubble_text and pygame.time.get_ticks() < error_bubble_until_ms:
            bubble_h = 32
            bubble_pad_x = 12
            bubble_text = font.render(error_bubble_text, True, (255, 235, 235))
            bubble_w = bubble_text.get_width() + bubble_pad_x * 2
            bubble_x = max(8, (screen.get_width() - bubble_w) // 2)
            bubble_y = hud_height - bubble_h - 4
            bubble_rect = pygame.Rect(bubble_x, bubble_y, bubble_w, bubble_h)
            pygame.draw.rect(screen, (120, 20, 20), bubble_rect, border_radius=8)
            pygame.draw.rect(screen, (220, 130, 130), bubble_rect, width=1, border_radius=8)
            screen.blit(bubble_text, (bubble_x + bubble_pad_x, bubble_y + 6))

        if action_bubble_text and pygame.time.get_ticks() < action_bubble_until_ms:
            bubble_h = 30
            bubble_pad_x = 12
            bubble_text = font.render(action_bubble_text, True, (235, 235, 245))
            bubble_w = bubble_text.get_width() + bubble_pad_x * 2
            bubble_x = max(8, (screen.get_width() - bubble_w) // 2)
            bubble_y = hud_height - 70
            bubble_rect = pygame.Rect(bubble_x, bubble_y, bubble_w, bubble_h)
            pygame.draw.rect(screen, action_bubble_color, bubble_rect, border_radius=8)
            pygame.draw.rect(screen, (210, 210, 210), bubble_rect, width=1, border_radius=8)
            screen.blit(bubble_text, (bubble_x + bubble_pad_x, bubble_y + 5))

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


