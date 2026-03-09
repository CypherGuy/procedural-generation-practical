from collections import deque

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
size = 5


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

# Place a player
for index, state in enumerate(generate_states()):
    x, y = divmod(index, size)
    if not player_in_map():
        if is_player(state) and grid[x][y] != "t" and grid[x][y] != "w":
            grid[x][y] = "p"

# Place a treasure
for index, state in enumerate(generate_states()):
    x, y = divmod(index, size)
    if not treasure_in_map():
        if is_treasure(state) and grid[x][y] != "w" and grid[x][y] != "p":
            grid[x][y] = "t"
    


# Verify map has 1 player, 1 treasure and that the treasure is reachable
def verify_map(grid):
    player_pos = None
    treasure_pos = None
    player_count = 0
    treasure_count = 0

    for i in range(size):
        for j in range(size):
            if grid[i][j] == "p":
                player_count += 1
                player_pos = (i, j)
            elif grid[i][j] == "t":
                treasure_count += 1
                treasure_pos = (i, j)

    # Must contain exactly one player and one treasure.
    if player_count != 1 or treasure_count != 1:
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
            if 0 <= nx < size and 0 <= ny < size:
                if (nx, ny) not in visited and grid[nx][ny] != "w":
                    visited.add((nx, ny))
                    queue.append((nx, ny))

    return False


#Print the map
players = 0
treasures = 0
for i in range(size):
    for j in range(size):
        print(grid[i][j], end=" ")
    print()



