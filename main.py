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

seed = 0
size = 10
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


# for i in range(size):
#     for j in range(size):
#         print(grid[i][j], end=" ")
#     print()


