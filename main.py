""" I will be making the following assumptions

- the map is a fixed size, such as 10×10 or 12×12
- every tile is either grass or wall
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
size = 10


# I changed the formula since that's obviously not ranoom enough. For now I'll use a mixed LCG

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

# for i in range(size):
#     for j in range(size):
#         print(grid[i][j], end=" ")
#     print()


