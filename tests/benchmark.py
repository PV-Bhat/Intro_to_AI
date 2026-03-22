"""
Headless benchmark for the 2048 Expectimax AI.
- Per-game wall-clock timeout (default 45s) — game is abandoned if it exceeds it
- Live progress printed and flushed after every move
- Sparse chance-node sampling for depth >= 4

Run:  python3 -u tests/benchmark.py
"""
import copy, math, random, sys, time, threading
from collections import Counter

# ── Config ────────────────────────────────────────────────────────────────────
GAMES_BY_DEPTH   = {2: 10, 3: 10, 4: 5}
GAME_TIMEOUT_S   = 45          # wall-clock seconds before a game is abandoned
MAX_CHANCE_CELLS = 5           # sparse sampling cap for depth >= 4
SEED             = 42

def p(*args, **kw):
    """Print and flush immediately."""
    print(*args, **kw, flush=True)

# ── Core game logic ───────────────────────────────────────────────────────────
def rotate_board(board, k):
    b = copy.deepcopy(board)
    for _ in range(k):
        nb = [[0]*4 for _ in range(4)]
        for r in range(4):
            for c in range(4):
                nb[r][c] = b[c][3-r]
        b = nb
    return b

def logic_move(board, dr, dc):
    k = {(-1,0):1, (0,1):2, (1,0):3}.get((dr,dc), 0)
    working = rotate_board(board, k)
    result, score, moved = [], 0, False
    for row in working:
        nz = [x for x in row if x]
        merged, skip = [], False
        for i in range(len(nz)):
            if skip: skip = False; continue
            if i+1 < len(nz) and nz[i+1] == nz[i]:
                merged.append(nz[i]*2); score += nz[i]*2; skip = True
            else:
                merged.append(nz[i])
        while len(merged) < 4: merged.append(0)
        if merged != row: moved = True
        result.append(merged)
    return moved, rotate_board(result, (4-k)%4), score

DIRS = [(-1,0),(1,0),(0,-1),(0,1)]

def spawn_tile(board):
    empty = [(r,c) for r in range(4) for c in range(4) if not board[r][c]]
    if empty:
        r,c = random.choice(empty)
        board[r][c] = 2 if random.random() < 0.9 else 4

def new_game():
    b = [[0]*4 for _ in range(4)]
    spawn_tile(b); spawn_tile(b)
    return b

def valid_moves(board):
    return [(dr,dc) for dr,dc in DIRS if logic_move(board,dr,dc)[0]]

# ── Heuristic (identical to gui_2048.py) ─────────────────────────────────────
def evaluate(board):
    empty = sum(board[r][c]==0 for r in range(4) for c in range(4))
    mx    = max(board[r][c] for r in range(4) for c in range(4))
    smooth = 0
    for r in range(4):
        for c in range(4):
            if not board[r][c]: continue
            cur = math.log2(board[r][c])
            if c+1<4 and board[r][c+1]: smooth -= abs(cur - math.log2(board[r][c+1]))
            if r+1<4 and board[r+1][c]: smooth -= abs(cur - math.log2(board[r+1][c]))
    mono = 0
    for row in board:
        ltr = rtl = 0
        for i in range(3):
            a = math.log2(row[i]) if row[i] else 0
            b = math.log2(row[i+1]) if row[i+1] else 0
            if a>b: ltr += b-a
            else:   rtl += a-b
        mono += max(ltr, rtl)
    for c in range(4):
        utd = dtu = 0
        for r in range(3):
            a = math.log2(board[r][c]) if board[r][c] else 0
            b = math.log2(board[r+1][c]) if board[r+1][c] else 0
            if a>b: utd += b-a
            else:   dtu += a-b
        mono += max(utd, dtu)
    return empty*250 + mx*1.0 + smooth*3.0 + mono*2.0

# ── Expectimax ────────────────────────────────────────────────────────────────
def expectimax(board, depth, is_chance, sparse):
    if depth <= 0: return evaluate(board)
    if is_chance:
        empty = [(r,c) for r in range(4) for c in range(4) if not board[r][c]]
        if not empty: return evaluate(board)
        if sparse and len(empty) > MAX_CHANCE_CELLS:
            empty = random.sample(empty, MAX_CHANCE_CELLS)
        prob = 1.0/len(empty)
        ev = 0.0
        for r,c in empty:
            b2 = copy.deepcopy(board); b2[r][c] = 2
            b4 = copy.deepcopy(board); b4[r][c] = 4
            ev += prob*(0.9*expectimax(b2,depth-1,False,sparse)
                      + 0.1*expectimax(b4,depth-1,False,sparse))
        return ev
    best, has_valid = -math.inf, False
    for dr,dc in DIRS:
        moved,nb,gain = logic_move(board,dr,dc)
        if not moved: continue
        has_valid = True
        val = gain + expectimax(nb,depth-1,True,sparse)
        if val > best: best = val
    return best if has_valid else evaluate(board)

def best_move(board, depth, sparse):
    bm, bv = None, -math.inf
    for dr,dc in DIRS:
        moved,nb,gain = logic_move(board,dr,dc)
        if not moved: continue
        val = gain + expectimax(nb,depth-1,True,sparse)
        if val > bv: bv, bm = val, (dr,dc)
    return bm

# ── Game runner with wall-clock timeout ───────────────────────────────────────
def play_game(depth, sparse, game_idx, n_games):
    board = new_game()
    score, n_moves, t_ai = 0, 0, 0.0
    timed_out = False
    deadline  = time.perf_counter() + GAME_TIMEOUT_S

    while True:
        if time.perf_counter() > deadline:
            timed_out = True
            break

        t0   = time.perf_counter()
        move = best_move(board, depth, sparse)
        dt   = time.perf_counter() - t0
        t_ai += dt
        n_moves += 1

        if move is None: break
        _, board, gain = logic_move(board, move[0], move[1])
        score += gain
        spawn_tile(board)

        # Live progress every 50 moves
        if n_moves % 50 == 0:
            mx = max(board[r][c] for r in range(4) for c in range(4))
            p(f"    move {n_moves:>4} | score {score:>7} | max_tile {mx:>5} "
              f"| last_move {dt*1000:.1f}ms", end="\r")

        if not valid_moves(board): break

    max_tile = max(board[r][c] for r in range(4) for c in range(4))
    avg_ms   = (t_ai/n_moves*1000) if n_moves else 0
    flag     = " [TIMEOUT]" if timed_out else ""
    p(f"  [{game_idx:>2}/{n_games}] score={score:>7,}  max_tile={max_tile:>5}"
      f"  moves={n_moves:>4}  avg={avg_ms:.1f}ms{flag}    ")
    return score, max_tile, n_moves, t_ai, timed_out

# ── Benchmark a single depth ──────────────────────────────────────────────────
def run_benchmark(depth, n_games):
    sparse = depth >= 4
    tag = f" [sparse ≤{MAX_CHANCE_CELLS} cells]" if sparse else ""
    p(f"\n{'='*58}")
    p(f"  Depth {depth}{tag}  —  {n_games} games  (timeout {GAME_TIMEOUT_S}s/game)")
    p(f"{'='*58}")

    scores, tiles, moves_list, times, timeouts = [], [], [], [], 0
    t_wall = time.perf_counter()

    for i in range(1, n_games+1):
        sc, mt, nm, ta, to = play_game(depth, sparse, i, n_games)
        scores.append(sc); tiles.append(mt); moves_list.append(nm); times.append(ta)
        if to: timeouts += 1

    elapsed = time.perf_counter() - t_wall
    tile_dist   = Counter(tiles)
    most_common = max(tile_dist, key=tile_dist.get)
    avg_score   = sum(scores)/n_games
    avg_moves   = sum(moves_list)/n_games
    avg_ms      = sum(times)/sum(moves_list)*1000 if sum(moves_list) else 0

    p(f"\n  ── Summary ─────────────────────────────────────")
    p(f"  Avg score      : {avg_score:,.0f}")
    p(f"  Most freq tile : {most_common}  dist={dict(sorted(tile_dist.items()))}")
    p(f"  Avg moves/game : {avg_moves:.0f}")
    p(f"  Avg time/move  : {avg_ms:.1f} ms")
    p(f"  Timeouts       : {timeouts}/{n_games}")
    p(f"  Total wall time: {elapsed:.1f}s")

    return dict(depth=depth, n_games=n_games, sparse=sparse,
                avg_score=avg_score, avg_ms=avg_ms,
                avg_moves=avg_moves, tile_dist=tile_dist,
                most_common_tile=most_common, timeouts=timeouts)

# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    random.seed(SEED)
    p("2048 Expectimax Benchmark")
    p(f"Depths: {list(GAMES_BY_DEPTH.keys())}  |  Games: {list(GAMES_BY_DEPTH.values())}")
    p(f"Timeout per game: {GAME_TIMEOUT_S}s  |  Sparse cap (depth≥4): {MAX_CHANCE_CELLS} cells")

    results = [run_benchmark(d, GAMES_BY_DEPTH[d]) for d in [2, 3, 4]]

    p("\n\n" + "="*58)
    p("  FINAL RESULTS")
    p("="*58)
    p(f"{'Depth':<8} {'Avg Score':>11} {'Top Tile':>9} {'Avg Moves':>11} {'ms/move':>8}")
    p("-"*58)
    for r in results:
        sp = "*" if r["sparse"] else " "
        p(f"  {r['depth']}{sp}      {r['avg_score']:>10,.0f}  {r['most_common_tile']:>8}"
          f"  {r['avg_moves']:>10.0f}  {r['avg_ms']:>7.1f}")
    p("  * sparse chance-node sampling")

    p("\n\n-- LaTeX table --")
    p(r"\begin{table}[h]")
    p(r"\centering\small")
    p(r"\begin{tabular}{|c|r|r|r|r|}")
    p(r"\hline")
    p(r"\textbf{Depth} & \textbf{Avg.\ Score} & \textbf{Most Freq.\ Max Tile}"
      r" & \textbf{Avg.\ Moves} & \textbf{Avg.\ Time/Move (ms)} \\ \hline")
    for r in results:
        sp = r"$^*$" if r["sparse"] else ""
        p(f"{r['depth']}{sp} & {r['avg_score']:,.0f} & {r['most_common_tile']}"
          f" & {r['avg_moves']:.0f} & {r['avg_ms']:.1f} \\\\")
    p(r"\hline")
    p(r"\end{tabular}")
    n2,n3,n4 = GAMES_BY_DEPTH[2], GAMES_BY_DEPTH[3], GAMES_BY_DEPTH[4]
    p(r"\caption{Expectimax AI performance across search depths ("
      f"depth~2: {n2} games, depth~3: {n3} games, "
      f"depth~4$^*$: {n4} games with sparse chance-node sampling, "
      f"max {MAX_CHANCE_CELLS} cells per node" + r").}")
    p(r"\label{tab:benchmarks}")
    p(r"\end{table}")
