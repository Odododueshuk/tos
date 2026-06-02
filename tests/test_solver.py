from core.solver import TOSSolver, evaluate_bitboards_numba
import numpy as np

def test_evaluate_bitboards_counts_combo_and_cleared_cells():
    bitboards = np.zeros(6, dtype=np.uint32)
    bitboards[0] = (1 << 0) | (1 << 1) | (1 << 2)
    bitboards[1] = (1 << 3) | (1 << 9) | (1 << 15)

    score, combos, cleared = evaluate_bitboards_numba(bitboards)

    assert score > 0
    assert combos == 2
    assert cleared == 6


def test_solve_mode_changes_search_policy_without_changing_path_legality():
    grid = [
        [0, 0, 1, 2, 3, 4],
        [1, 2, 3, 4, 5, 0],
        [2, 3, 4, 5, 0, 1],
        [3, 4, 5, 0, 1, 2],
        [4, 5, 0, 1, 2, 3],
    ]
    obs = [[0] * 6 for _ in range(5)]
    solver = TOSSolver(max_steps=4, beam_width=30)

    for mode in ("short_8c", "max_combo", "full_board"):
        path, combos, cleared = solver.solve(grid, obs, solve_mode=mode)
        assert path
        assert combos >= 0
        assert cleared >= 0
        for (r1, c1), (r2, c2) in zip(path, path[1:]):
            assert abs(r1 - r2) + abs(c1 - c2) == 1


def test_obstacle_cells_are_not_used_in_path():
    grid = [
        [0, 1, 2, 3, 4, 5],
        [1, 2, 3, 4, 5, 0],
        [2, 3, 4, 5, 0, 1],
        [3, 4, 5, 0, 1, 2],
        [4, 5, 0, 1, 2, 3],
    ]
    obs = [[0] * 6 for _ in range(5)]
    obs[2][2] = 1

    solver = TOSSolver(max_steps=5, beam_width=40)
    path, _combos, _cleared = solver.solve(grid, obs, solve_mode="full_board")

    assert (2, 2) not in path


def test_custom_target_combo_modes():
    # A standard board layout
    grid = [
        [0, 0, 0, 1, 1, 1],
        [2, 2, 2, 3, 3, 3],
        [4, 4, 4, 5, 5, 5],
        [0, 1, 2, 3, 4, 5],
        [5, 4, 3, 2, 1, 0],
    ]
    obs = [[0] * 6 for _ in range(5)]
    solver = TOSSolver(max_steps=25, beam_width=150)

    # Test "at_least_c" (e.g. at least 4 combos)
    path, combos, cleared = solver.solve(grid, obs, solve_mode="at_least_c", target_combo=4)
    assert combos >= 4

    # Test "exactly_c" (e.g. exactly 5 combos)
    path, combos, cleared = solver.solve(grid, obs, solve_mode="exactly_c", target_combo=5)
    assert combos == 5

    # Test "exactly_orbs" (e.g. exactly 15 orbs)
    path, combos, cleared = solver.solve(grid, obs, solve_mode="exactly_orbs", target_orbs=15)
    assert cleared == 15

