import numpy as np
from typing import Dict, List, Optional, Tuple
import numba as nb

DIRECTIONS = np.array([[-1, 0], [1, 0], [0, -1], [0, 1]], dtype=np.int32)
ROWS = 5
COLS = 6
CELLS = ROWS * COLS
ORB_TYPES = 6

NOT_LEFT_COL = 0x3FFFFFFF & ~((1 << 0) | (1 << 6) | (1 << 12) | (1 << 18) | (1 << 24))
NOT_RIGHT_COL = 0x3FFFFFFF & ~((1 << 5) | (1 << 11) | (1 << 17) | (1 << 23) | (1 << 29))
H_MASK = 0
for r in range(ROWS):
    for c in range(COLS - 2):
        H_MASK |= 1 << (r * COLS + c)
V_MASK = 0
for r in range(ROWS - 2):
    for c in range(COLS):
        V_MASK |= 1 << (r * COLS + c)

SUPPORTED_SOLVE_MODES = {"short_8c", "max_combo", "full_board", "priority_color", "at_least_c", "exactly_c"}


@nb.njit(cache=True)
def popcount(n):
    c = 0
    while n:
        n &= n - 1
        c += 1
    return c

@nb.njit(cache=True)
def evaluate_bitboards_numba(bitboards):
    total_combos = 0
    total_cleared = 0
    group_score = 0

    for color in range(6):
        color_board = bitboards[color]
        if not color_board:
            continue

        hm = color_board & (color_board >> 1) & (color_board >> 2) & H_MASK
        hm_cells = hm | (hm << 1) | (hm << 2)

        vm = color_board & (color_board >> COLS) & (color_board >> (COLS * 2)) & V_MASK
        vm_cells = vm | (vm << COLS) | (vm << (COLS * 2))

        match_mask = hm_cells | vm_cells

        if match_mask:
            mask = match_mask
            while mask:
                total_combos += 1
                lsb = mask & -mask
                region = lsb
                while True:
                    new_region = (
                        region
                        | ((region & NOT_LEFT_COL) >> 1)
                        | ((region & NOT_RIGHT_COL) << 1)
                        | (region >> COLS)
                        | (region << COLS)
                    )
                    new_region &= mask
                    if new_region == region:
                        break
                    region = new_region

                total_cleared += popcount(region)
                mask ^= region

        unmatched = color_board & ~match_mask
        h_adj = unmatched & ((unmatched & NOT_LEFT_COL) >> 1)
        v_adj = unmatched & (unmatched >> COLS)
        group_score += popcount(h_adj) + popcount(v_adj)

    return total_combos * 10000.0 + total_cleared * 100.0 + group_score * 10.0, total_combos, total_cleared

# Mode flags
MODE_SHORT_8C = 0
MODE_MAX_COMBO = 1
MODE_FULL_BOARD = 2
MODE_AT_LEAST_C = 3
MODE_EXACTLY_C = 4


@nb.njit(cache=True)
def hash_bitboards(bitboards, pos):
    h = np.uint64(pos)
    for i in range(6):
        h ^= (np.uint64(bitboards[i]) << np.uint64(i * 5))
    return h

@nb.njit(cache=True)
def run_beam_search(grid_flat, blocked, max_steps, beam_width, mode, target_combo):
    init_bitboards = np.zeros(6, dtype=np.uint32)
    for r in range(ROWS):
        for c in range(COLS):
            idx = r * COLS + c
            color = grid_flat[idx]
            if 0 <= color < 6:
                init_bitboards[color] |= np.uint32(1 << idx)
                
    max_cands = beam_width * 4
    
    beam_paths = np.empty((beam_width, max_steps + 1), dtype=np.int32)
    beam_path_lens = np.zeros(beam_width, dtype=np.int32)
    beam_bitboards = np.empty((beam_width, 6), dtype=np.uint32)
    beam_flat = np.empty((beam_width, CELLS), dtype=np.int32)
    beam_scores = np.empty(beam_width, dtype=np.float32)
    beam_combos = np.empty(beam_width, dtype=np.int32)
    beam_cleared = np.empty(beam_width, dtype=np.int32)
    
    cand_paths = np.empty((max_cands, max_steps + 1), dtype=np.int32)
    cand_path_lens = np.zeros(max_cands, dtype=np.int32)
    cand_bitboards = np.empty((max_cands, 6), dtype=np.uint32)
    cand_flat = np.empty((max_cands, CELLS), dtype=np.int32)
    cand_scores = np.empty(max_cands, dtype=np.float32)
    cand_combos = np.empty(max_cands, dtype=np.int32)
    cand_cleared = np.empty(max_cands, dtype=np.int32)

    beam_size = 0
    for r in range(ROWS):
        for c in range(COLS):
            idx = r * COLS + c
            if (blocked & (1 << idx)) != 0:
                continue
            if beam_size < beam_width:
                beam_paths[beam_size, 0] = idx
                beam_path_lens[beam_size] = 1
                for i in range(6):
                    beam_bitboards[beam_size, i] = init_bitboards[i]
                for i in range(CELLS):
                    beam_flat[beam_size, i] = grid_flat[i]
                beam_scores[beam_size] = -999999.0
                beam_combos[beam_size] = 0
                beam_cleared[beam_size] = 0
                beam_size += 1
                
    if beam_size == 0:
        return np.empty(0, dtype=np.int32), 0, 0
        
    best_overall_score = -9999999.0
    best_overall_combos = 0
    best_overall_cleared = 0
    best_overall_path = np.empty(max_steps + 1, dtype=np.int32)
    best_overall_path_len = 0
    
    best_target_found = False

    for step in range(max_steps):
        cand_size = 0
        
        for i in range(beam_size):
            path_len = beam_path_lens[i]
            curr_idx = beam_paths[i, path_len - 1]
            curr_r = curr_idx // COLS
            curr_c = curr_idx % COLS
            
            prev_idx = -1
            if path_len >= 2:
                prev_idx = beam_paths[i, path_len - 2]
                
            for d in range(4):
                nr = curr_r + DIRECTIONS[d, 0]
                nc = curr_c + DIRECTIONS[d, 1]
                
                if nr < 0 or nr >= ROWS or nc < 0 or nc >= COLS:
                    continue
                    
                n_idx = nr * COLS + nc
                if n_idx == prev_idx:
                    continue
                    
                if (blocked & (1 << n_idx)) != 0:
                    continue
                    
                if cand_size < max_cands:
                    for c in range(6):
                        cand_bitboards[cand_size, c] = beam_bitboards[i, c]
                    for c in range(CELLS):
                        cand_flat[cand_size, c] = beam_flat[i, c]
                        
                    color_a = beam_flat[i, curr_idx]
                    color_b = beam_flat[i, n_idx]
                    if color_a != color_b:
                        if 0 <= color_a < 6:
                            cand_bitboards[cand_size, color_a] &= ~(np.uint32(1 << curr_idx))
                            cand_bitboards[cand_size, color_a] |= np.uint32(1 << n_idx)
                        if 0 <= color_b < 6:
                            cand_bitboards[cand_size, color_b] &= ~(np.uint32(1 << n_idx))
                            cand_bitboards[cand_size, color_b] |= np.uint32(1 << curr_idx)
                        
                        cand_flat[cand_size, curr_idx] = color_b
                        cand_flat[cand_size, n_idx] = color_a
                        
                    for p in range(path_len):
                        cand_paths[cand_size, p] = beam_paths[i, p]
                    cand_paths[cand_size, path_len] = n_idx
                    cand_path_lens[cand_size] = path_len + 1
                    
                    cand_size += 1
                    
        if cand_size == 0:
            break
            
        for i in range(cand_size):
            raw_score, est_combos, est_cleared = evaluate_bitboards_numba(cand_bitboards[i])
            
            cand_combos[i] = est_combos
            cand_cleared[i] = est_cleared
            
            path_len = cand_path_lens[i]
            path_penalty = (path_len - 1) * 0.5
            
            if mode == MODE_SHORT_8C:
                cand_scores[i] = raw_score - path_penalty
            elif mode == MODE_MAX_COMBO:
                cand_scores[i] = est_combos * 100000.0 + est_cleared * 100.0 - path_penalty
            elif mode == MODE_AT_LEAST_C:
                if est_combos >= target_combo:
                    cand_scores[i] = 1000000.0 + est_combos * 10000.0 - path_penalty
                else:
                    cand_scores[i] = est_combos * 10000.0 + est_cleared * 100.0 - path_penalty
            elif mode == MODE_EXACTLY_C:
                if est_combos == target_combo:
                    cand_scores[i] = 1000000.0 - path_penalty
                else:
                    diff = abs(est_combos - target_combo)
                    cand_scores[i] = -diff * 10000.0 + est_cleared * 10.0 - path_penalty
            else:
                cand_scores[i] = est_combos * 100000.0 + est_cleared * 1000.0 - path_penalty

                
            if cand_scores[i] > best_overall_score:
                best_overall_score = cand_scores[i]
                best_overall_combos = est_combos
                best_overall_cleared = est_cleared
                best_overall_path_len = path_len
                for p in range(path_len):
                    best_overall_path[p] = cand_paths[i, p]
                    
            if mode == MODE_SHORT_8C and est_combos >= 8:
                best_target_found = True
                break
            if mode == MODE_AT_LEAST_C and est_combos >= target_combo:
                best_target_found = True
                break
            if mode == MODE_EXACTLY_C and est_combos == target_combo:
                best_target_found = True
                break

                
        if best_target_found:
            break
            
        sort_indices = np.argsort(-cand_scores[:cand_size])
        
        seen = set()
        new_beam_size = 0
        
        for idx in sort_indices:
            h = hash_bitboards(cand_bitboards[idx], cand_paths[idx, cand_path_lens[idx]-1])
            if h not in seen:
                seen.add(h)
                
                for c in range(6):
                    beam_bitboards[new_beam_size, c] = cand_bitboards[idx, c]
                for c in range(CELLS):
                    beam_flat[new_beam_size, c] = cand_flat[idx, c]
                for p in range(cand_path_lens[idx]):
                    beam_paths[new_beam_size, p] = cand_paths[idx, p]
                beam_path_lens[new_beam_size] = cand_path_lens[idx]
                beam_scores[new_beam_size] = cand_scores[idx]
                beam_combos[new_beam_size] = cand_combos[idx]
                beam_cleared[new_beam_size] = cand_cleared[idx]
                
                new_beam_size += 1
                if new_beam_size >= beam_width:
                    break
                    
        beam_size = new_beam_size

    out_path = np.empty(best_overall_path_len, dtype=np.int32)
    for i in range(best_overall_path_len):
        out_path[i] = best_overall_path[i]
        
    return out_path, best_overall_combos, best_overall_cleared

class TOSSolver:
    """
    神魔之塔路徑求解器。(經過 Numba 優化版)

    solve_mode:
    - short_8c: 找到 >= 8 combo 的最短路徑即停。
    - max_combo: 在步數限制內追求最高 combo。
    - full_board: 追求 combo，並偏好消除顆數較多的盤面。
    - priority_color: 保留介面相容，現階段等同 full_board。
    """

    def __init__(self, max_steps: int = 80, beam_width: int = 200):
        self.max_steps = max_steps
        self.beam_width = beam_width

    def solve(
        self,
        grid: List[List[int]],
        obs: Optional[List[List[int]]] = None,
        solve_mode: str = "max_combo",
        target_combo: int = 8,
    ) -> Tuple[List[Tuple[int, int]], int, int]:
        mode = solve_mode if solve_mode in SUPPORTED_SOLVE_MODES else "max_combo"
        
        mode_flag = MODE_MAX_COMBO
        if mode == "short_8c":
            mode_flag = MODE_SHORT_8C
        elif mode == "at_least_c":
            mode_flag = MODE_AT_LEAST_C
        elif mode == "exactly_c":
            mode_flag = MODE_EXACTLY_C
        elif mode in ("full_board", "priority_color"):
            mode_flag = MODE_FULL_BOARD

        blocked = self._blocked_mask(obs)
        grid_flat = np.array([color for row in grid for color in row], dtype=np.int32)
        
        path_indices, combos, cleared = run_beam_search(
            grid_flat, blocked, self.max_steps, self.beam_width, mode_flag, target_combo
        )
        
        path = [(int(idx // COLS), int(idx % COLS)) for idx in path_indices]
        return path, combos, cleared

    def _blocked_mask(self, obs: Optional[List[List[int]]]) -> int:
        if not obs:
            return 0
        mask = 0
        for r in range(min(ROWS, len(obs))):
            for c in range(min(COLS, len(obs[r]))):
                if obs[r][c] != 0:
                    mask |= 1 << (r * COLS + c)
        return mask
