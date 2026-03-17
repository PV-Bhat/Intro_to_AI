"""
This module implements a 4x4 grid GUI for 2048 game.
"""
import tkinter as tk
from tkinter import messagebox
import random
import copy
import platform
import math
# --- Configuration & Constants ---

# Colors (Gabriele Cirulli style)
COLORS = {
    'bg': "#faf8ef",
    'grid_bg': "#bbada0",
    'tile_empty': "#cdc1b4",
    'text_dark': "#776e65",
    'text_light': "#f9f6f2",
    2: "#eee4da",
    4: "#ede0c8",
    8: "#f2b179",
    16: "#f59563",
    32: "#f67c5f",
    64: "#f65e3b",
    128: "#edcf72",
    256: "#edcc61",
    512: "#edc850",
    1024: "#edc53f",
    2048: "#edc22e",
    'super': "#3c3a32" # For > 2048
}

FONT_SCORE_LABEL = ("Verdana", 12, "bold")
FONT_SCORE_VAL = ("Verdana", 20, "bold")
FONT_TILE = ("Clear Sans", 24, "bold")
FONT_MSG = ("Helvetica", 12)
FONT_RECOMMENDATION = ("Arial", 54, "bold")

# Game States
STATE_PLAYING = "STATE_PLAYING"

# Platform-specific right-click
RIGHT_CLICK = "<Button-2>" if platform.system() == "Darwin" else "<Button-3>"

class Game2048GUI:
    def __init__(self, root):
        self.root = root
        self.root.title("2048 Game")
        self.root.geometry("700x430")
        self.root.configure(bg=COLORS['bg'])

        # --- Game Data ---
        self.board = [[0]*4 for _ in range(4)]
        self.score = 0
        
        # Undo history: (board_copy, score_copy)
        self.undo_stack = None 
        
        self.current_state = STATE_PLAYING
        
        # --- UI Setup ---
        self._setup_ui()
        
        # Bindings
        self.root.bind("<Key>", self.handle_keypress)
        self.root.bind("<Button-1>", self.clear_focus, add="+")

        # Initial setup
        self.init_game()
        self.update_board_ui()
        self.update_recommendation_display()

    def _setup_ui(self):
        # Main Container
        main_frame = tk.Frame(self.root, bg=COLORS['bg'])
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # -- Left Area: Board --
        self.left_frame = tk.Frame(main_frame, bg=COLORS['grid_bg'], width=400, height=400)
        self.left_frame.pack(side="left", padx=(0, 20))
        self.left_frame.pack_propagate(False) # Force size

        # Initialize Grid Tiles (Labels)
        self.tiles = []
        for r in range(4):
            row_tiles = []
            for c in range(4):
                # Frame for padding/spacing
                f = tk.Frame(self.left_frame, bg=COLORS['tile_empty'], width=85, height=85)
                f.grid(row=r, column=c, padx=5, pady=5)
                f.pack_propagate(False)
                
                # The label displaying the number
                l = tk.Label(f, text="", bg=COLORS['tile_empty'], font=FONT_TILE)
                l.pack(fill="both", expand=True)
                
                row_tiles.append((f, l))
            self.tiles.append(row_tiles)

        # -- Right Area: Info --
        self.right_frame = tk.Frame(main_frame, bg=COLORS['bg'])
        self.right_frame.pack(side="left", fill="both", expand=True)

        # Slot 1: Score
        score_frame = tk.Frame(self.right_frame, bg=COLORS['bg'])
        score_frame.pack(fill="x", pady=(0, 10))
        tk.Label(score_frame, text="SCORE", bg=COLORS['bg'], fg=COLORS['text_dark'], font=FONT_SCORE_LABEL).pack(anchor="w")
        
        # Score Display
        self.score_var = tk.StringVar(value="0")
        self.score_label = tk.Label(score_frame, textvariable=self.score_var, bg=COLORS['bg'], fg=COLORS['text_dark'], font=FONT_SCORE_VAL)
        self.score_label.pack(anchor="w")

        # Slot 2: Messages
        ai_frame = tk.Frame(self.right_frame, bg=COLORS['bg'])
        ai_frame.pack(fill="x", pady=(0, 10))
        tk.Label(ai_frame, text="RECOMMENDED MOVE", bg=COLORS['bg'], fg=COLORS['text_dark'], font=FONT_SCORE_LABEL).pack(anchor="w")

        self.recommendation_var = tk.StringVar(value="")
        self.recommendation_label = tk.Label(
            ai_frame,
            textvariable=self.recommendation_var,
            bg=COLORS['bg'],
            fg="#f65e3b",
            font=FONT_RECOMMENDATION
        )
        self.recommendation_label.pack(anchor="center")

        # Slot 3: Messages
        msg_frame = tk.Frame(self.right_frame, bg=COLORS['grid_bg'], padx=10, pady=10)
        msg_frame.pack(fill="x", pady=0)
        
        self.msg_label = tk.Label(msg_frame, text="Use arrow keys to move.\nCtrl+Z to undo.", bg=COLORS['grid_bg'], fg="#f9f6f2", 
                                  font=FONT_MSG, wraplength=240, justify="left")
        self.msg_label.pack(anchor="nw")

    # --- Logic: Validation & Helpers ---

    def update_score_display(self):
        self.score_var.set(str(self.score))

    def init_game(self):
        self.board = [[0]*4 for _ in range(4)]
        self.score = 0
        self.spawn_tile()
        self.spawn_tile()
        self.update_score_display()

    def spawn_tile(self):
        empty_cells = [(r, c) for r in range(4) for c in range(4) if self.board[r][c] == 0]
        if empty_cells:
            r, c = random.choice(empty_cells)
            self.board[r][c] = 2 if random.random() < 0.9 else 4

    def is_game_over(self):
        # Check if any moves are possible
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            moved, _, _ = self.logic_move(self.board, dr, dc)
            if moved:
                return False
        return True

    def update_board_ui(self):
        for r in range(4):
            for c in range(4):
                val = self.board[r][c]
                frame, label = self.tiles[r][c]
                
                # Background color
                bg_color = COLORS.get(val, COLORS['super']) if val > 2048 else COLORS.get(val, COLORS['tile_empty'])
                if val == 0: bg_color = COLORS['tile_empty']
                
                # Text color
                fg_color = COLORS['text_dark'] if val in (2, 4) else COLORS['text_light']
                
                text = str(val) if val > 0 else ""
                
                frame.config(bg=bg_color)
                label.config(text=text, bg=bg_color, fg=fg_color)

# --- Interaction Handlers ---

    def handle_keypress(self, event):
        key = event.keysym
        
        if self.current_state == STATE_PLAYING:
            if key in ["Up", "Down", "Left", "Right"]:
                self.perform_game_move(key)
            elif key.lower() == "a":
                self.perform_ai_move()
            elif (event.state & 0x0004) and (key.lower() == 'z'): # Ctrl+Z
                self.undo_move()
            elif key == "Undo": 
                self.undo_move()
    
    def clear_focus(self, event):
        self.root.focus_set()

    # --- 2048 Move Implementation ---

    def perform_game_move(self, key_direction):
        """
        Executes the move on the internal board.
        Saves state for Undo.
        Updates Score.
        Spawns new tile if move was valid.
        """
        # Save state for Undo
        prev_board = copy.deepcopy(self.board)
        prev_score = self.score
        
        # Map key to vector
        vectors = {
            "Up": (-1, 0), "Down": (1, 0),
            "Left": (0, -1), "Right": (0, 1)
        }
        dr, dc = vectors[key_direction]
        
        moved, new_board, score_gain = self.logic_move(self.board, dr, dc)
        
        if moved:
            self.undo_stack = (prev_board, prev_score)
            self.board = new_board
            self.score += score_gain
            self.update_score_display()
            self.update_board_ui()
            
            # Spawn new tile
            self.spawn_tile()
            self.update_board_ui()
            self.update_recommendation_display()
            
            # Check game over
            if self.is_game_over():
                self.msg_label.config(text="Game Over!\n\nNo more moves possible.\nPress Ctrl+Z to undo or restart.")
                self.recommendation_var.set("✖")
        else:
            # Invalid move (nothing changed)
            pass

    def undo_move(self):
        if self.undo_stack:
            self.board, self.score = self.undo_stack
            self.undo_stack = None # Clear stack (one level undo)
            self.update_board_ui()
            self.update_score_display()
            self.update_recommendation_display()
            self.msg_label.config(text="Move undone.\nUse arrow keys to move.\nCtrl+Z to undo.")
        else:
            print("Nothing to undo")

    def perform_ai_move(self):
        best_move = self.get_best_move(depth=3)
        if not best_move:
            self.recommendation_var.set("✖")
            self.msg_label.config(text="No valid AI move available.")
            return

        self.recommendation_var.set(self.move_to_arrow(best_move))

        self.perform_game_move(best_move)
        if self.current_state == STATE_PLAYING:
            self.msg_label.config(text=f"AI played: {best_move}\nPress A for next AI move.")

    def move_to_arrow(self, move_name):
        arrows = {
            "Up": "↑",
            "Down": "↓",
            "Left": "←",
            "Right": "→",
        }
        return arrows.get(move_name, move_name)

    def update_recommendation_display(self):
        best_move = self.get_best_move(depth=3)
        if best_move:
            self.recommendation_var.set(self.move_to_arrow(best_move))
        else:
            self.recommendation_var.set("✖")

    def get_best_move(self, depth=3):
        moves = [
            ("Up", -1, 0),
            ("Down", 1, 0),
            ("Left", 0, -1),
            ("Right", 0, 1),
        ]

        best_move = None
        best_value = -math.inf

        for move_name, dr, dc in moves:
            moved, next_board, score_gain = self.logic_move(self.board, dr, dc)
            if not moved:
                continue

            value = score_gain + self.expectimax(next_board, depth - 1, is_chance=True)
            if value > best_value:
                best_value = value
                best_move = move_name

        return best_move

    def expectimax(self, board, depth, is_chance):
        if depth <= 0:
            return self.evaluate_board(board)

        if is_chance:
            empty_cells = [(r, c) for r in range(4) for c in range(4) if board[r][c] == 0]
            if not empty_cells:
                return self.evaluate_board(board)

            probability_per_cell = 1.0 / len(empty_cells)
            expected_value = 0.0

            for r, c in empty_cells:
                board_2 = copy.deepcopy(board)
                board_2[r][c] = 2
                board_4 = copy.deepcopy(board)
                board_4[r][c] = 4

                value_2 = self.expectimax(board_2, depth - 1, is_chance=False)
                value_4 = self.expectimax(board_4, depth - 1, is_chance=False)

                expected_value += probability_per_cell * (0.9 * value_2 + 0.1 * value_4)

            return expected_value

        best_value = -math.inf
        has_valid_move = False

        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            moved, next_board, score_gain = self.logic_move(board, dr, dc)
            if not moved:
                continue

            has_valid_move = True
            value = score_gain + self.expectimax(next_board, depth - 1, is_chance=True)
            best_value = max(best_value, value)

        return best_value if has_valid_move else self.evaluate_board(board)

    def evaluate_board(self, board):
        empty_cells = sum(1 for r in range(4) for c in range(4) if board[r][c] == 0)
        max_tile = max(max(row) for row in board)

        smoothness = 0
        for r in range(4):
            for c in range(4):
                if board[r][c] == 0:
                    continue
                current_log = math.log2(board[r][c])

                if c + 1 < 4 and board[r][c + 1] != 0:
                    smoothness -= abs(current_log - math.log2(board[r][c + 1]))
                if r + 1 < 4 and board[r + 1][c] != 0:
                    smoothness -= abs(current_log - math.log2(board[r + 1][c]))

        monotonicity = 0
        for row in board:
            left_to_right = 0
            right_to_left = 0
            for i in range(3):
                a = math.log2(row[i]) if row[i] else 0
                b = math.log2(row[i + 1]) if row[i + 1] else 0
                if a > b:
                    left_to_right += b - a
                else:
                    right_to_left += a - b
            monotonicity += max(left_to_right, right_to_left)

        for c in range(4):
            up_to_down = 0
            down_to_up = 0
            for r in range(3):
                a = math.log2(board[r][c]) if board[r][c] else 0
                b = math.log2(board[r + 1][c]) if board[r + 1][c] else 0
                if a > b:
                    up_to_down += b - a
                else:
                    down_to_up += a - b
            monotonicity += max(up_to_down, down_to_up)

        return (empty_cells * 250) + (max_tile * 1.0) + (smoothness * 3.0) + (monotonicity * 2.0)

    def logic_move(self, board, dr, dc):
        """
        Generic 2048 move logic.
        Returns (moved_boolean, new_board, score_gained)
        """
        # We'll rotate the board so we always process "Left" logic, then rotate back
        # This simplifies the merging logic significantly.
        
        # Standardize to Left:
        # Up: Rotate 270 (or -90)
        # Right: Rotate 180
        # Down: Rotate 90
        # Left: 0
        
        k = 0
        if (dr, dc) == (-1, 0): k = 1 # Up
        elif (dr, dc) == (0, 1): k = 2 # Right
        elif (dr, dc) == (1, 0): k = 3 # Down
        
        working_board = self.rotate_board(board, k)
        
        # Process Left Move
        new_board_arr = []
        total_score = 0
        moved = False
        
        for r in range(4):
            row = working_board[r]
            # 1. Compress (remove zeros)
            non_zeros = [x for x in row if x != 0]
            
            # 2. Merge
            merged = []
            skip = False
            for i in range(len(non_zeros)):
                if skip:
                    skip = False
                    continue
                val = non_zeros[i]
                if i + 1 < len(non_zeros) and non_zeros[i+1] == val:
                    merged.append(val * 2)
                    total_score += (val * 2)
                    skip = True
                else:
                    merged.append(val)
            
            # 3. Fill zeros
            while len(merged) < 4:
                merged.append(0)
                
            if merged != row:
                moved = True
            new_board_arr.append(merged)
            
        # Rotate back (4-k)
        final_board = self.rotate_board(new_board_arr, (4 - k) % 4)
        
        return moved, final_board, total_score

    def rotate_board(self, board, k):
        """Rotate board 90 degrees Anti-Clockwise k times"""
        b = copy.deepcopy(board)
        for _ in range(k):
            # Transpose + Reverse (standard matrix rotation)
            # To rotate 90 Counter Clockwise:
            # New[i][j] = Old[j][Width-1-i]
            new_b = [[0]*4 for _ in range(4)]
            for r in range(4):
                for c in range(4):
                    new_b[r][c] = b[c][3-r]
            b = new_b
        return b

if __name__ == "__main__":
    root = tk.Tk()
    app = Game2048GUI(root)
    root.mainloop()