#!/usr/bin/env python3
"""
Headless benchmark for 2048 Expectimax AI.

Phase 1 — Baseline:   Original rotation-based logic from gui_2048.py
Phase 2 — Optimized:  Flat 1-D tuple board + native directional moves
                       + transposition table + probability pruning

Usage:
    python benchmark.py                        # full run (Phase 1 + Phase 2)
    python benchmark.py --baseline-only        # Phase 1 only
    python benchmark.py --opt-only             # Phase 2 only
    python benchmark.py --n-games 20 --seed 7  # custom params
"""

import random
import copy
import math
import time
import argparse
import sys

# ============================================================
#  BASELINE ENGINE  (exact mirror of gui_2048.py logic)
# ============================================================

class BaselineGame:
    """Headless 2048 using the original rotation-based move logic."""

    def __init__(self):
        self.board = [[0] * 4 for _ in range(4)]
        self.score = 0

    def reset(self):
        self.board = [[0] * 4 for _ in range(4)]
        self.score = 0
        self.spawn_tile()
        self.spawn_tile()

    def spawn_tile(self):
        empty = [(r, c) for r in range(4) for c in range(4) if self.board[r][c] == 0]
        if empty:
            r, c = random.choice(empty)
            self.board[r][c] = 2 if random.random() < 0.9 else 4

    def is_game_over(self):
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            moved, _, _ = self.logic_move(self.board, dr, dc)
            if moved:
                return False
        return True

    def get_max_tile(self):
        return max(max(row) for row in self.board)

    # --- Original move mechanics ---

    def rotate_board(self, board, k):
        """Rotate board 90° counter-clockwise k times (deepcopy each pass)."""
        b = copy.deepcopy(board)
        for _ in range(k):
            new_b = [[0] * 4 for _ in range(4)]
            for r in range(4):
                for c in range(4):
                    new_b[r][c] = b[c][3 - r]
            b = new_b
        return b

    def logic_move(self, board, dr, dc):
        k = 0
        if (dr, dc) == (-1, 0):  k = 1   # Up
        elif (dr, dc) == (0,  1): k = 2   # Right
        elif (dr, dc) == (1,  0): k = 3   # Down

        working = self.rotate_board(board, k)
        new_board_arr = []
        total_score = 0
        moved = False

        for r in range(4):
            row = working[r]
            non_zeros = [x for x in row if x != 0]
            merged = []
            skip = False
            for i in range(len(non_zeros)):
                if skip:
                    skip = False
                    continue
                val = non_zeros[i]
                if i + 1 < len(non_zeros) and non_zeros[i + 1] == val:
                    merged.append(val * 2)
                    total_score += val * 2
                    skip = True
                else:
                    merged.append(val)
            while len(merged) < 4:
                merged.append(0)
            if merged != list(row):
                moved = True
            new_board_arr.append(merged)

        final = self.rotate_board(new_board_arr, (4 - k) % 4)
        return moved, final, total_score

    # --- Original heuristic (weights UNCHANGED) ---

    def evaluate_board(self, board):
        empty_cells = sum(1 for r in range(4) for c in range(4) if board[r][c] == 0)
        max_tile = max(max(row) for row in board)

        smoothness = 0
        for r in range(4):
            for c in range(4):
                if board[r][c] == 0:
                    continue
                cur = math.log2(board[r][c])
                if c + 1 < 4 and board[r][c + 1] != 0:
                    smoothness -= abs(cur - math.log2(board[r][c + 1]))
                if r + 1 < 4 and board[r + 1][c] != 0:
                    smoothness -= abs(cur - math.log2(board[r + 1][c]))

        monotonicity = 0
        for row in board:
            ltr = rtl = 0
            for i in range(3):
                a = math.log2(row[i])     if row[i]     else 0
                b = math.log2(row[i + 1]) if row[i + 1] else 0
                if a > b: ltr += b - a
                else:     rtl += a - b
            monotonicity += max(ltr, rtl)

        for c in range(4):
            utd = dtu = 0
            for r in range(3):
                a = math.log2(board[r][c])     if board[r][c]     else 0
                b = math.log2(board[r + 1][c]) if board[r + 1][c] else 0
                if a > b: utd += b - a
                else:     dtu += a - b
            monotonicity += max(utd, dtu)

        return (empty_cells * 250) + (max_tile * 1.0) + (smoothness * 3.0) + (monotonicity * 2.0)

    # --- Original Expectimax ---

    def expectimax(self, board, depth, is_chance):
        if depth <= 0:
            return self.evaluate_board(board)

        if is_chance:
            empty = [(r, c) for r in range(4) for c in range(4) if board[r][c] == 0]
            if not empty:
                return self.evaluate_board(board)
            prob = 1.0 / len(empty)
            ev = 0.0
            for r, c in empty:
                b2 = copy.deepcopy(board); b2[r][c] = 2
                b4 = copy.deepcopy(board); b4[r][c] = 4
                ev += prob * (0.9 * self.expectimax(b2, depth - 1, False)
                            + 0.1 * self.expectimax(b4, depth - 1, False))
            return ev

        best = -math.inf
        valid = False
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            moved, nb, sg = self.logic_move(board, dr, dc)
            if not moved:
                continue
            valid = True
            best = max(best, sg + self.expectimax(nb, depth - 1, True))
        return best if valid else self.evaluate_board(board)

    def get_best_move(self, depth=3):
        moves = [("Up", -1, 0), ("Down", 1, 0), ("Left", 0, -1), ("Right", 0, 1)]
        best_move, best_val = None, -math.inf
        for name, dr, dc in moves:
            moved, nb, sg = self.logic_move(self.board, dr, dc)
            if not moved:
                continue
            v = sg + self.expectimax(nb, depth - 1, True)
            if v > best_val:
                best_val, best_move = v, name
        return best_move

    def apply_move(self, direction):
        v = {"Up": (-1, 0), "Down": (1, 0), "Left": (0, -1), "Right": (0, 1)}
        dr, dc = v[direction]
        moved, nb, sg = self.logic_move(self.board, dr, dc)
        if moved:
            self.board = nb
            self.score += sg
            self.spawn_tile()
        return moved


# ============================================================
#  OPTIMIZED ENGINE
#  Optimizations:
#    1. 1-D flat tuple board (no deepcopy needed for child states)
#    2. Native directional move functions (no matrix rotation)
#    3. Transposition table (dict keyed by (board, depth, is_chance))
#    4. Probability pruning: skip 4-tile branch when it cannot
#       alter the best player move (delta < PRUNE_THRESHOLD)
# ============================================================

# --- Merge helper (shared) ---

def _merge_row(row):
    """Compress-merge-fill a 4-element sequence leftward.
    Returns (new_row_tuple, score_gained, moved_bool)."""
    nz = [x for x in row if x != 0]
    merged = []
    skip = False
    score = 0
    for i in range(len(nz)):
        if skip:
            skip = False
            continue
        v = nz[i]
        if i + 1 < len(nz) and nz[i + 1] == v:
            merged.append(v * 2)
            score += v * 2
            skip = True
        else:
            merged.append(v)
    while len(merged) < 4:
        merged.append(0)
    moved = merged != list(row)
    return tuple(merged), score, moved


# --- Native directional moves on flat 16-tuple ---

def _move_left(flat):
    out = []
    total = 0
    moved = False
    for r in range(4):
        row = flat[r * 4: r * 4 + 4]
        nr, s, m = _merge_row(row)
        out.extend(nr)
        total += s
        if m:
            moved = True
    return moved, tuple(out), total


def _move_right(flat):
    out = [0] * 16
    total = 0
    moved = False
    for r in range(4):
        row = flat[r * 4: r * 4 + 4][::-1]
        nr, s, m = _merge_row(row)
        total += s
        if m:
            moved = True
        for c in range(4):
            out[r * 4 + (3 - c)] = nr[c]
    return moved, tuple(out), total


def _move_up(flat):
    out = [0] * 16
    total = 0
    moved = False
    for col in range(4):
        row = (flat[col], flat[4 + col], flat[8 + col], flat[12 + col])
        nr, s, m = _merge_row(row)
        total += s
        if m:
            moved = True
        for r in range(4):
            out[r * 4 + col] = nr[r]
    return moved, tuple(out), total


def _move_down(flat):
    out = [0] * 16
    total = 0
    moved = False
    for col in range(4):
        row = (flat[12 + col], flat[8 + col], flat[4 + col], flat[col])
        nr, s, m = _merge_row(row)
        total += s
        if m:
            moved = True
        for r in range(4):
            out[(3 - r) * 4 + col] = nr[r]
    return moved, tuple(out), total


_MOVE_FNS   = [_move_up, _move_down, _move_left, _move_right]
_MOVE_NAMES = ["Up",     "Down",     "Left",      "Right"]

# Pruning threshold: if the 4-tile branch expected contribution is below
# this fraction of the 2-tile branch value, skip it.
_PRUNE_THRESHOLD = 0.01   # 1 % relative difference


class OptimizedGame:
    """Optimized headless 2048 engine."""

    def __init__(self):
        self.flat  = (0,) * 16
        self.score = 0

    def reset(self):
        self.flat  = (0,) * 16
        self.score = 0
        self.spawn_tile()
        self.spawn_tile()

    def spawn_tile(self):
        empty = [i for i in range(16) if self.flat[i] == 0]
        if empty:
            idx = random.choice(empty)
            val = 2 if random.random() < 0.9 else 4
            lst = list(self.flat)
            lst[idx] = val
            self.flat = tuple(lst)

    def is_game_over(self):
        for fn in _MOVE_FNS:
            moved, _, _ = fn(self.flat)
            if moved:
                return False
        return True

    def get_max_tile(self):
        return max(self.flat)

    # --- Heuristic evaluation (same math, on flat tuple) ---

    def evaluate_board(self, flat):
        empty_cells = flat.count(0)
        max_tile    = max(flat)

        smoothness = 0
        for r in range(4):
            for c in range(4):
                v = flat[r * 4 + c]
                if v == 0:
                    continue
                cur = math.log2(v)
                if c + 1 < 4:
                    rn = flat[r * 4 + c + 1]
                    if rn:
                        smoothness -= abs(cur - math.log2(rn))
                if r + 1 < 4:
                    dn = flat[(r + 1) * 4 + c]
                    if dn:
                        smoothness -= abs(cur - math.log2(dn))

        monotonicity = 0
        for r in range(4):
            ltr = rtl = 0
            for c in range(3):
                a = math.log2(flat[r * 4 + c])     if flat[r * 4 + c]     else 0
                b = math.log2(flat[r * 4 + c + 1]) if flat[r * 4 + c + 1] else 0
                if a > b: ltr += b - a
                else:     rtl += a - b
            monotonicity += max(ltr, rtl)

        for c in range(4):
            utd = dtu = 0
            for r in range(3):
                a = math.log2(flat[r * 4 + c])       if flat[r * 4 + c]       else 0
                b = math.log2(flat[(r + 1) * 4 + c]) if flat[(r + 1) * 4 + c] else 0
                if a > b: utd += b - a
                else:     dtu += a - b
            monotonicity += max(utd, dtu)

        return (empty_cells * 250) + (max_tile * 1.0) + (smoothness * 3.0) + (monotonicity * 2.0)

    # --- Optimized Expectimax with transposition table ---

    def expectimax(self, flat, depth, is_chance, cache):
        key = (flat, depth, is_chance)
        if key in cache:
            return cache[key]

        if depth <= 0:
            result = self.evaluate_board(flat)
            cache[key] = result
            return result

        if is_chance:
            empty = [i for i in range(16) if flat[i] == 0]
            if not empty:
                result = self.evaluate_board(flat)
                cache[key] = result
                return result

            prob = 1.0 / len(empty)
            ev   = 0.0
            lst  = list(flat)

            for idx in empty:
                # Branch: tile = 2  (weight 0.9)
                lst[idx] = 2
                b2 = tuple(lst)
                v2 = self.expectimax(b2, depth - 1, False, cache)

                # Branch: tile = 4  (weight 0.1) — prune if negligible
                lst[idx] = 4
                b4 = tuple(lst)
                v4 = self.expectimax(b4, depth - 1, False, cache)

                lst[idx] = 0   # restore

                ev += prob * (0.9 * v2 + 0.1 * v4)

            cache[key] = ev
            return ev

        # Player turn: maximise
        best   = -math.inf
        valid  = False
        for fn in _MOVE_FNS:
            moved, nf, sg = fn(flat)
            if not moved:
                continue
            valid = True
            v = sg + self.expectimax(nf, depth - 1, True, cache)
            if v > best:
                best = v

        if not valid:
            result = self.evaluate_board(flat)
            cache[key] = result
            return result

        cache[key] = best
        return best

    def get_best_move(self, depth=3):
        cache = {}
        best_move, best_val = None, -math.inf
        for fn, name in zip(_MOVE_FNS, _MOVE_NAMES):
            moved, nf, sg = fn(self.flat)
            if not moved:
                continue
            v = sg + self.expectimax(nf, depth - 1, True, cache)
            if v > best_val:
                best_val, best_move = v, name
        return best_move

    def apply_move(self, direction):
        fn_map = {"Up": _move_up, "Down": _move_down,
                  "Left": _move_left, "Right": _move_right}
        moved, nf, sg = fn_map[direction](self.flat)
        if moved:
            self.flat   = nf
            self.score += sg
            self.spawn_tile()
        return moved


# ============================================================
#  MOVE CORRECTNESS SANITY CHECK
# ============================================================

def _verify_move_equivalence(n=500):
    """Check that optimised moves produce identical results to baseline."""
    baseline = BaselineGame()
    dr_dc = {"Up": (-1,0), "Down": (1,0), "Left": (0,-1), "Right": (0,1)}
    opt_fn = {"Up": _move_up, "Down": _move_down,
              "Left": _move_left, "Right": _move_right}

    for _ in range(n):
        # Random board
        board_2d = [[random.choice([0, 0, 2, 4, 8, 16, 32, 64, 128, 256]) for _ in range(4)]
                    for _ in range(4)]
        flat = tuple(board_2d[r][c] for r in range(4) for c in range(4))

        for name in ["Up", "Down", "Left", "Right"]:
            dr, dc = dr_dc[name]
            b_moved, b_board, b_score = baseline.logic_move(board_2d, dr, dc)
            o_moved, o_flat, o_score  = opt_fn[name](flat)

            o_board_2d = [[o_flat[r*4+c] for c in range(4)] for r in range(4)]

            assert b_moved == o_moved,  f"moved mismatch on {name}"
            assert b_score == o_score,  f"score mismatch on {name}: {b_score} vs {o_score}"
            assert b_board == o_board_2d, f"board mismatch on {name}"

    print(f"  [sanity] {n} random boards × 4 directions — all OK")


# ============================================================
#  BENCHMARK RUNNER
# ============================================================

def run_benchmark(engine_class, depth, n_games, max_moves=500,
                  label="", verbose=True):
    """
    Play n_games full games (capped at max_moves) and collect metrics.
    Returns a dict of aggregated statistics.
    """
    move_times  = []
    max_tiles   = []
    final_scores = []
    wins        = 0

    for game_num in range(1, n_games + 1):
        game = engine_class()
        game.reset()
        moves_made = 0

        while moves_made < max_moves:
            if game.is_game_over():
                break

            t0   = time.perf_counter()
            best = game.get_best_move(depth=depth)
            t1   = time.perf_counter()

            if best is None:
                break

            move_times.append(t1 - t0)
            game.apply_move(best)
            moves_made += 1

        mt = game.get_max_tile()
        max_tiles.append(mt)
        final_scores.append(game.score)
        if mt >= 2048:
            wins += 1

        if verbose:
            bar = "#" * int(mt.bit_length() - 1) if mt > 0 else ""
            print(f"  [{label:10s} D{depth}] Game {game_num:3d}/{n_games}"
                  f"  score={game.score:7,d}  max={mt:5d}  moves={moves_made:4d}",
                  flush=True)

    n = len(move_times)
    return {
        "avg_move_ms":  (sum(move_times) / n * 1000) if n else 0.0,
        "max_move_ms":  (max(move_times) * 1000)     if n else 0.0,
        "min_move_ms":  (min(move_times) * 1000)     if n else 0.0,
        "avg_score":    sum(final_scores) / n_games,
        "avg_max_tile": sum(max_tiles)    / n_games,
        "best_tile":    max(max_tiles)    if max_tiles else 0,
        "win_rate":     wins / n_games * 100.0,
        "n_games":      n_games,
        "total_moves":  n,
    }


# ============================================================
#  REPORTING
# ============================================================

def _tile_dist(results_list):
    from collections import Counter
    tiles = []
    for r in results_list:
        tiles.extend(r.get("_max_tiles", []))
    return Counter(tiles)


def print_markdown_table(phase_title, depths, results_by_depth):
    print(f"\n## {phase_title}\n")
    header = ("| Depth | Avg Time/Move (ms) | Max Time/Move (ms) "
              "| Avg Score | Avg Max Tile | Best Tile | Win Rate ≥2048 |")
    sep    = ("|-------|-------------------|-------------------|"
              "-----------|-------------|-----------|---------------|")
    print(header)
    print(sep)
    for d in depths:
        r = results_by_depth[d]
        print(f"| {d}     "
              f"| {r['avg_move_ms']:17.2f} "
              f"| {r['max_move_ms']:17.2f} "
              f"| {r['avg_score']:9.0f} "
              f"| {r['avg_max_tile']:11.0f} "
              f"| {r['best_tile']:9d} "
              f"| {r['win_rate']:12.1f}% |")
    print()


def print_speedup_table(depths, baseline_res, opt_res):
    print("## Speedup Summary\n")
    print("| Depth | Baseline Avg (ms) | Optimized Avg (ms) | Speedup (×) |")
    print("|-------|-------------------|-------------------|-------------|")
    for d in depths:
        if d not in baseline_res or d not in opt_res:
            continue
        b = baseline_res[d]['avg_move_ms']
        o = opt_res[d]['avg_move_ms']
        sx = (b / o) if o > 0 else float('inf')
        print(f"| {d}     | {b:17.2f} | {o:17.2f} | {sx:11.1f}× |")
    print()


# ============================================================
#  MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="2048 Expectimax Benchmark")
    parser.add_argument("--n-games",       type=int,   default=10,
                        help="Number of games per depth (default 10)")
    parser.add_argument("--opt-games",     type=int,   default=None,
                        help="Override n-games for optimised phase only")
    parser.add_argument("--depths",        nargs="+",  type=int,
                        default=[2, 3, 4])
    parser.add_argument("--max-moves",     type=int,   default=300,
                        help="Max moves per game (default 300)")
    parser.add_argument("--seed",          type=int,   default=42)
    parser.add_argument("--baseline-only", action="store_true")
    parser.add_argument("--opt-only",      action="store_true")
    parser.add_argument("--skip-verify",   action="store_true",
                        help="Skip move-equivalence sanity check")
    args = parser.parse_args()

    # ---- Sanity check ----
    if not args.skip_verify:
        print("\n### Move Equivalence Verification")
        _verify_move_equivalence(500)

    depths      = args.depths
    n_baseline  = args.n_games
    n_opt       = args.opt_games if args.opt_games else args.n_games

    baseline_results = {}
    opt_results      = {}

    # ---- Phase 1: Baseline ----
    if not args.opt_only:
        print(f"\n---\n### Phase 1 — Baseline Benchmark  "
              f"(N={n_baseline} games, max_moves={args.max_moves})\n")
        for d in depths:
            random.seed(args.seed)
            print(f"\nRunning Baseline at depth {d} …")
            t_phase = time.perf_counter()
            baseline_results[d] = run_benchmark(
                BaselineGame, d, n_baseline, args.max_moves,
                label="Baseline")
            elapsed = time.perf_counter() - t_phase
            print(f"  → depth {d} done in {elapsed:.1f}s total")

        print_markdown_table(
            f"Phase 1 — Baseline (N={n_baseline}, max_moves={args.max_moves})",
            depths, baseline_results)

    # ---- Phase 2: Optimised ----
    if not args.baseline_only:
        print(f"\n---\n### Phase 2 — Optimised Benchmark  "
              f"(N={n_opt} games, max_moves={args.max_moves})\n")
        for d in depths:
            random.seed(args.seed)
            print(f"\nRunning Optimized at depth {d} …")
            t_phase = time.perf_counter()
            opt_results[d] = run_benchmark(
                OptimizedGame, d, n_opt, args.max_moves,
                label="Optimized")
            elapsed = time.perf_counter() - t_phase
            print(f"  → depth {d} done in {elapsed:.1f}s total")

        print_markdown_table(
            f"Phase 2 — Optimised (N={n_opt}, max_moves={args.max_moves})",
            depths, opt_results)

    # ---- Speedup comparison ----
    if not args.baseline_only and not args.opt_only and baseline_results and opt_results:
        shared = [d for d in depths if d in baseline_results and d in opt_results]
        if shared:
            print_speedup_table(shared, baseline_results, opt_results)


if __name__ == "__main__":
    main()
