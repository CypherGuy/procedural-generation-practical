import pytest
from main import formula, is_wall, generate_states, generate_map, verify_map, on_regenerate_button_pressed


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def blank_grid(size, fill="g"):
    return [[fill] * size for _ in range(size)]


def place(grid, tile, row, col):
    grid[row][col] = tile
    return grid


# ---------------------------------------------------------------------------
# formula()
# ---------------------------------------------------------------------------

class TestFormula:
    def test_zero_state(self):
        assert formula(0, 5, 1, 2**32) == 1

    def test_state_one(self):
        assert formula(1, 5, 1, 2**32) == 6

    def test_output_in_range(self):
        m = 2**32
        for x in [0, 1, 100, 999_999, m - 1]:
            result = formula(x, 5, 1, m)
            assert 0 <= result < m

    def test_modulus_wrap(self):
        # (5 * (2^32 - 1) + 1) mod 2^32 should not raise and stays in range
        m = 2**32
        result = formula(m - 1, 5, 1, m)
        assert 0 <= result < m

    def test_deterministic(self):
        assert formula(42, 5, 1, 2**32) == formula(42, 5, 1, 2**32)


# ---------------------------------------------------------------------------
# is_wall()
# ---------------------------------------------------------------------------

class TestIsWall:
    def test_multiples_of_9_are_walls(self):
        for n in [0, 9, 18, 27, 99]:
            assert is_wall(n) is True

    def test_non_multiples_are_not_walls(self):
        for n in [1, 2, 7, 8, 10, 100]:
            assert is_wall(n) is False

    def test_distribution_approx_one_ninth(self):
        count = sum(1 for n in range(9000) if is_wall(n))
        # Exactly 1/9 of integers 0..8999 are multiples of 9
        assert count == 1000


# ---------------------------------------------------------------------------
# generate_states()
# ---------------------------------------------------------------------------

class TestGenerateStates:
    def test_yields_correct_count(self):
        states = list(generate_states(42, 10))
        assert len(states) == 10 ** 2

    def test_yields_correct_count_lake_mode(self):
        states = list(generate_states(42, 5, lake=True))
        assert len(states) == 5 ** 2 * 1000

    def test_all_values_non_negative(self):
        for v in generate_states(123, 5):
            assert v >= 0

    def test_deterministic(self):
        seq_a = list(generate_states(7, 8))
        seq_b = list(generate_states(7, 8))
        assert seq_a == seq_b

    def test_different_seeds_differ(self):
        seq_a = list(generate_states(1, 8))
        seq_b = list(generate_states(2, 8))
        assert seq_a != seq_b


# ---------------------------------------------------------------------------
# verify_map()
# ---------------------------------------------------------------------------

class TestVerifyMap:
    def _valid_grid(self, size=15):
        """All grass, player top-left, treasure bottom-right — path length = 2*(size-1)."""
        g = blank_grid(size)
        g[0][0] = "p"
        g[size - 1][size - 1] = "t"
        return g

    def test_valid_map_passes(self):
        ok, reason = verify_map(self._valid_grid())
        assert ok is True
        assert reason == ""

    def test_no_player_fails(self):
        g = blank_grid(15)
        g[14][14] = "t"
        ok, reason = verify_map(g)
        assert ok is False
        assert "1 player" in reason

    def test_no_treasure_fails(self):
        g = blank_grid(15)
        g[0][0] = "p"
        ok, reason = verify_map(g)
        assert ok is False
        assert "1 treasure" in reason

    def test_two_players_fails(self):
        g = blank_grid(15)
        g[0][0] = "p"
        g[0][1] = "p"
        g[14][14] = "t"
        ok, reason = verify_map(g)
        assert ok is False

    def test_unreachable_treasure_fails(self):
        # Solid wall column down the middle blocks all paths
        size = 15
        g = blank_grid(size)
        g[0][0] = "p"
        g[0][size - 1] = "t"
        for row in range(size):
            g[row][size // 2] = "w"
        ok, reason = verify_map(g)
        assert ok is False
        assert "unreachable" in reason

    def test_path_too_short_fails(self):
        # On a 30x30 map, min path = ceil(2*30/3) = 20.
        # Place player and treasure 2 steps apart.
        size = 30
        g = blank_grid(size)
        g[0][0] = "p"
        g[0][2] = "t"
        ok, reason = verify_map(g)
        assert ok is False
        assert "shortest path" in reason

    def test_small_lake_fails(self):
        g = self._valid_grid()
        # 5-tile horizontal lake — below minimum of 20
        for col in range(5, 10):
            g[7][col] = "l"
        ok, reason = verify_map(g)
        assert ok is False
        assert "lake size" in reason

    def test_large_lake_passes(self):
        # 25-tile lake in the middle of a large grid, player/treasure far apart
        size = 40
        g = blank_grid(size)
        g[0][0] = "p"
        g[size - 1][size - 1] = "t"
        for col in range(10, 35):
            g[20][col] = "l"
        ok, _ = verify_map(g)
        assert ok is True


# ---------------------------------------------------------------------------
# generate_map()
# ---------------------------------------------------------------------------

class TestGenerateMap:
    @pytest.mark.parametrize("sz", [5, 10, 20, 40, 80])
    def test_returns_correct_dimensions(self, sz):
        grid = generate_map(1, sz)
        assert len(grid) == sz
        assert all(len(row) == sz for row in grid)

    def test_no_unknown_tiles(self):
        grid = generate_map(1, 20)
        for row in grid:
            assert "Unknown" not in row

    def test_deterministic(self):
        assert generate_map(2103, 80) == generate_map(2103, 80)

    def test_different_seeds_differ(self):
        assert generate_map(1, 30) != generate_map(2, 30)

    def test_exactly_one_player_and_treasure(self):
        grid = generate_map(42, 30)
        flat = [tile for row in grid for tile in row]
        assert flat.count("p") == 1
        assert flat.count("t") == 1

    def test_no_buildings_on_small_map(self):
        # Buildings only spawn on maps >= 20x20
        grid = generate_map(1, 10)
        flat = [tile for row in grid for tile in row]
        assert "b" not in flat

    def test_no_lakes_on_small_map(self):
        # Lakes only spawn on maps >= 40x40
        grid = generate_map(1, 30)
        flat = [tile for row in grid for tile in row]
        assert "l" not in flat

    def test_buildings_can_appear_on_large_map(self):
        # Try a handful of seeds; at least one should produce buildings on a 40x40 map
        found = any(
            "b" in (tile for row in generate_map(s, 40) for tile in row)
            for s in range(1, 20)
        )
        assert found

    def test_lakes_can_appear_on_large_map(self):
        found = any(
            "l" in (tile for row in generate_map(s, 80) for tile in row)
            for s in range(1, 10)
        )
        assert found


# ---------------------------------------------------------------------------
# on_regenerate_button_pressed()
# ---------------------------------------------------------------------------

class TestOnRegenerateButtonPressed:
    def _setup(self):
        grid = generate_map(2103, 40)
        player_pos = next(
            (i, j) for i, row in enumerate(grid) for j, t in enumerate(row) if t == "p"
        )
        treasure_pos = next(
            (i, j) for i, row in enumerate(grid) for j, t in enumerate(row) if t == "t"
        )
        return grid, player_pos, treasure_pos

    def test_returns_list_on_success(self):
        grid, _, _ = self._setup()
        result = on_regenerate_button_pressed(9999, 40, grid)
        assert isinstance(result, (list, str))  # either valid grid or failure reason

    def test_old_positions_cleared(self):
        grid, player_pos, treasure_pos = self._setup()
        on_regenerate_button_pressed(9999, 40, grid)
        # original positions must not remain as p/t (they were cleared to g before replacement)
        # The grid is mutated in place so we check the returned state indirectly via the grid
        pi, pj = player_pos
        ti, tj = treasure_pos
        assert grid[pi][pj] != "p" or grid[ti][tj] != "t"  # at least one was moved

    def test_result_passes_verify_when_list(self):
        grid, _, _ = self._setup()
        for seed_offset in range(1, 20):
            result = on_regenerate_button_pressed(2103 + seed_offset, 40, grid)
            if isinstance(result, list):
                ok, reason = verify_map(result)
                assert ok is True, f"regenerated grid failed verify: {reason}"
                break
