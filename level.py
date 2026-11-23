import exopython as exo
from exopython import scripts as exoscript, variables as exovar

# ---------------------------------------------------------------------------
# 1. Level Initialization
# ---------------------------------------------------------------------------
lvl = exo.init(
    "Chess (Full Rules)",
    bg_type="Custom",
    laps=1,
    gravity=(0.0, 0.0),
    settings={
        "AllowDirectionChange": True,
        "DisableStartAnim": True,
        "DisableRevivePads": True,
        "CenterCamera": True,
        "CustomBackgroundColor": "#181615",
    },
)

board_layer = exo.CreateLayer("Board", foreground_type=0)
piece_layer = exo.CreateLayer("Pieces", foreground_type=1)
ui_layer = exo.CreateLayer("UI", foreground_type=1)

# ---------------------------------------------------------------------------
# 2. Static Board Geometry & Visual Piece Setup
# ---------------------------------------------------------------------------
FILE_CENTERS = (-3.5, -2.5, -1.5, -0.5, 0.5, 1.5, 2.5, 3.5)
RANK_CENTERS = (-3.5, -2.5, -1.5, -0.5, 0.5, 1.5, 2.5, 3.5)
FILES = ("a", "b", "c", "d", "e", "f", "g", "h")
RANKS = ("1", "2", "3", "4", "5", "6", "7", "8")

# Signed Piece Codes stored inside Exoracer runtime variables:
#  0 = Empty
#  1 = White Pawn,   2 = White Knight,  3 = White Bishop
#  4 = White Rook,   5 = White Queen,   6 = White King
# -1 = Black Pawn,  -2 = Black Knight, -3 = Black Bishop
# -4 = Black Rook,  -5 = Black Queen,  -6 = Black King
BACK_RANK_CODES = (4, 2, 3, 5, 6, 3, 2, 4)

GLYPHS = {
    6: "♔", 5: "♕", 4: "♖", 3: "♗", 2: "♘", 1: "♙",
    -6: "♚", -5: "♛", -4: "♜", -3: "♝", -2: "♞", -1: "♟",
}

PIECE_SCALE = {
    6: (0.78, 0.78),
    5: (0.74, 0.74),
    4: (0.66, 0.66),
    3: (0.68, 0.68),
    2: (0.66, 0.66),
    1: (0.54, 0.54),
}

# Outer board frame
(
    exo.CreateObj("rect", (0.0, 0.0))
    .settings(
        {
            "Width": 8.6,
            "Height": 8.6,
            "Color": "#3B2818",
            "BorderColor": "#21150C",
            "BorderThickness": 0.08,
            "CornerRadius": 0.12,
            "Layer": board_layer,
        }
    )
    .pack()
)

# 64 squares + rank/file labels
for r in range(8):
    y = RANK_CENTERS[r]
    (
        exo.CreateObj("text", (-4.15, y))
        .settings({"Text": RANKS[r], "FontSize": 0.34, "Color": "#E5D3B3", "Layer": ui_layer})
        .pack()
    )
    for f in range(8):
        x = FILE_CENTERS[f]
        sq_color = "#EEEED2" if ((r + f) % 2) == 1 else "#769656"
        (
            exo.CreateObj("rect", (x, y))
            .settings(
                {
                    "Width": 0.98,
                    "Height": 0.98,
                    "Color": sq_color,
                    "BorderColor": sq_color,
                    "BorderThickness": 0.01,
                    "Layer": board_layer,
                }
            )
            .pack()
        )
        if r == 0:
            (
                exo.CreateObj("text", (x, -4.15))
                .settings({"Text": FILES[f], "FontSize": 0.34, "Color": "#E5D3B3", "Layer": ui_layer})
                .pack()
            )

# Build initial 64-square board table and spawn piece visual objects (token + glyph)
initial_board = [0] * 64
piece_tokens: list[exo.GameObject] = []
piece_glyphs: list[exo.GameObject] = []

for f in range(8):
    initial_board[0 * 8 + f] = BACK_RANK_CODES[f]
    initial_board[1 * 8 + f] = 1
    initial_board[6 * 8 + f] = -1
    initial_board[7 * 8 + f] = -BACK_RANK_CODES[f]

for idx in range(64):
    code = initial_board[idx]
    if code == 0:
        continue
    r = idx // 8
    f = idx % 8
    x = FILE_CENTERS[f]
    y = RANK_CENTERS[r]
    abs_c = code if code > 0 else -code
    sx, sy = PIECE_SCALE[abs_c]
    is_white = code > 0

    tok = (
        exo.CreateObj("rect", (x, y))
        .settings(
            {
                "Width": 0.84,
                "Height": 0.84,
                "Scale": (sx, sy),
                "Color": "#FFFDF7" if is_white else "#242124",
                "BorderColor": "#2B2118" if is_white else "#F4EBD9",
                "BorderThickness": 0.06,
                "CornerRadius": 0.18 if abs_c in (1, 5, 6) else 0.06,
                "Layer": piece_layer,
            }
        )
        .pack()
    )
    gly = (
        exo.CreateObj("text", (x, y))
        .settings(
            {
                "Text": GLYPHS[code],
                "FontSize": 0.56,
                "Color": "#1A1612" if is_white else "#FFFDF7",
                "Layer": piece_layer,
            }
        )
        .pack()
    )
    piece_tokens.append(tok)
    piece_glyphs.append(gly)

# ---------------------------------------------------------------------------
# 3. Cursor, Selection Ring & HUD Objects
# ---------------------------------------------------------------------------
hover_ring = (
    exo.CreateObj("rect_outline", (-3.5, -3.5))
    .settings({"Width": 0.96, "Height": 0.96, "Color": "#FFD166", "Thickness": 0.06, "Layer": ui_layer})
    .pack()
)

selected_ring = (
    exo.CreateObj("rect_outline", (0.0, -100.0))
    .settings({"Width": 0.98, "Height": 0.98, "Color": "#00E5FF", "Thickness": 0.08, "Layer": ui_layer})
    .pack()
)

turn_banner = (
    exo.CreateObj("text", (0.0, 4.65))
    .settings({"Text": "WHITE TO MOVE  |  Move: 1", "FontSize": 0.36, "Color": "#FFFFFF", "Layer": ui_layer})
    .pack()
)

status_footer = (
    exo.CreateObj("text", (0.0, -4.68))
    .settings(
        {
            "Text": "Click a White piece to begin | Jump+Left: Cancel selection",
            "FontSize": 0.28,
            "Color": "#CFC6B8",
            "Layer": ui_layer,
        }
    )
    .pack()
)

# ---------------------------------------------------------------------------
# 4. Exoracer Runtime Variables (exovar.*) — ALL Game State Lives Here
# ---------------------------------------------------------------------------
# 64 Exoracer Int variables representing the live 8x8 board state
board_vars = [exovar.Int(f"sq_{i}", initial_board[i]) for i in range(64)]

# Core match state in Exoracer variables
turn_side = exovar.Int("turn_side", 1)          # 1 = White, -1 = Black
game_over = exovar.Bool("game_over", False)
has_selection = exovar.Bool("has_selection", False)
move_number = exovar.Int("move_number", 1)

# Selected square coordinates & piece info
sel_f = exovar.Int("sel_f", -1)
sel_r = exovar.Int("sel_r", -1)
sel_idx = exovar.Int("sel_idx", -1)
sel_code = exovar.Int("sel_code", 0)
sel_pos = exovar.Vector("sel_pos", (0.0, -100.0))

# Hovered / clicked square coordinates & piece info
cur_f = exovar.Int("cur_f", 0)
cur_r = exovar.Int("cur_r", 0)
cur_idx = exovar.Int("cur_idx", 0)
cur_pos = exovar.Vector("cur_pos", (-3.5, -3.5))

# Scratch registers for board lookup, raycasting & move validation
query_idx = exovar.Int("query_idx", 0)
query_val = exovar.Int("query_val", 0)
write_idx = exovar.Int("write_idx", 0)
write_val = exovar.Int("write_val", 0)

target_code = exovar.Int("target_code", 0)
abs_piece = exovar.Int("abs_piece", 0)
df = exovar.Int("df", 0)
dr = exovar.Int("dr", 0)
abs_df = exovar.Int("abs_df", 0)
abs_dr = exovar.Int("abs_dr", 0)
step_f = exovar.Int("step_f", 0)
step_r = exovar.Int("step_r", 0)
ray_f = exovar.Int("ray_f", 0)
ray_r = exovar.Int("ray_r", 0)
path_clear = exovar.Bool("path_clear", True)
is_legal = exovar.Bool("is_legal", False)

# Visual object references & HUD strings
moving_token = exovar.Object("moving_token", 0)
moving_glyph = exovar.Object("moving_glyph", 0)
captured_token = exovar.Object("captured_token", 0)
captured_glyph = exovar.Object("captured_glyph", 0)

turn_str = exovar.String("turn_str", "WHITE TO MOVE")
status_str = exovar.String("status_str", "Click a White piece to begin")

token_set = exovar.object_set(piece_tokens)
glyph_set = exovar.object_set(piece_glyphs)

# ---------------------------------------------------------------------------
# 5. Runtime Board Array Read/Write Functions (@exoscript.func)
# ---------------------------------------------------------------------------
@exoscript.func
def read_board():
    """Reads board_vars[query_idx] into query_val inside Exoracer VM."""
    b = exoscript.block().set_var(query_val, 0)
    for i in range(64):
        b = b.if_else(
            query_idx.eq(i),
            exoscript.block().set_var(query_val, board_vars[i]),
        )
    return b


@exoscript.func
def write_board():
    """Writes write_val into board_vars[write_idx] inside Exoracer VM."""
    b = exoscript.block()
    for i in range(64):
        b = b.if_else(
            write_idx.eq(i),
            exoscript.block().set_var(board_vars[i], write_val),
        )
    return b


@exoscript.func
def refresh_hud():
    """Updates top and bottom HUD banners from Exoracer variables."""
    return (
        exoscript.block()
        .if_else(
            exovar.not_(game_over),
            exoscript.block().if_else(
                turn_side.eq(1),
                exoscript.block().set_var(turn_str, "WHITE TO MOVE"),
                exoscript.block().set_var(turn_str, "BLACK TO MOVE"),
            ),
        )
        .set_text(
            turn_banner,
            turn_str + "  |  Move: " + exovar.str_from_int(move_number),
        )
        .set_text(status_footer, status_str)
    )


# ---------------------------------------------------------------------------
# 6. Runtime Raycast & Legal Move Validator (@exoscript.func)
# ---------------------------------------------------------------------------
@exoscript.func
def check_ray_clear():
    """Steps from (sel_f, sel_r) toward (cur_f, cur_r) checking intermediate squares."""
    return (
        exoscript.block()
        .set_var(path_clear, True)
        .set_var(step_f, exovar.sign_int(df))
        .set_var(step_r, exovar.sign_int(dr))
        .set_var(ray_f, sel_f + step_f)
        .set_var(ray_r, sel_r + step_r)
        .repeat_while(
            exovar.or_(exovar.ne(ray_f, cur_f), exovar.ne(ray_r, cur_r)),
            exoscript.block()
            .set_var(query_idx, ray_r * 8 + ray_f)
            .call(read_board, wait=True)
            .if_else(
                exovar.ne(query_val, 0),
                exoscript.block().set_var(path_clear, False),
            )
            .set_var(ray_f, ray_f + step_f)
            .set_var(ray_r, ray_r + step_r),
            wait=True,
        )
    )


@exoscript.func
def validate_move():
    """Evaluates full chess legality for moving sel_code from (sel_f,sel_r) -> (cur_f,cur_r)."""
    return (
        exoscript.block()
        .set_var(is_legal, False)
        .set_var(df, cur_f - sel_f)
        .set_var(dr, cur_r - sel_r)
        .set_var(abs_df, exovar.abs_int(df))
        .set_var(abs_dr, exovar.abs_int(dr))
        .set_var(abs_piece, exovar.abs_int(sel_code))
        # Read destination square occupancy
        .set_var(query_idx, cur_idx)
        .call(read_board, wait=True)
        .set_var(target_code, query_val)
        # Cannot stay on same square or capture friendly piece (same sign)
        .if_else(
            exovar.and_(
                exovar.or_(exovar.ne(df, 0), exovar.ne(dr, 0)),
                exovar.le(target_code * turn_side, 0),
            ),
            exoscript.block()
            # --- 1. PAWN (abs_piece == 1) ---
            .if_else(
                abs_piece.eq(1),
                exoscript.block()
                # Single square forward push into empty square
                .if_else(
                    exovar.and_(
                        exovar.and_(df.eq(0), dr.eq(turn_side)),
                        target_code.eq(0),
                    ),
                    exoscript.block().set_var(is_legal, True),
                )
                # Double square forward push from starting rank (White r=1, Black r=6)
                .if_else(
                    exovar.and_(
                        exovar.and_(df.eq(0), dr.eq(turn_side * 2)),
                        exovar.and_(
                            target_code.eq(0),
                            exovar.or_(
                                exovar.and_(turn_side.eq(1), sel_r.eq(1)),
                                exovar.and_(turn_side.eq(-1), sel_r.eq(6)),
                            ),
                        ),
                    ),
                    exoscript.block()
                    .set_var(query_idx, (sel_r + turn_side) * 8 + sel_f)
                    .call(read_board, wait=True)
                    .if_else(
                        query_val.eq(0),
                        exoscript.block().set_var(is_legal, True),
                    ),
                )
                # Diagonal capture onto enemy piece
                .if_else(
                    exovar.and_(
                        exovar.and_(abs_df.eq(1), dr.eq(turn_side)),
                        exovar.lt(target_code * turn_side, 0),
                    ),
                    exoscript.block().set_var(is_legal, True),
                ),
            )
            # --- 2. KNIGHT (abs_piece == 2) ---
            .if_else(
                abs_piece.eq(2),
                exoscript.block().if_else(
                    exovar.or_(
                        exovar.and_(abs_df.eq(1), abs_dr.eq(2)),
                        exovar.and_(abs_df.eq(2), abs_dr.eq(1)),
                    ),
                    exoscript.block().set_var(is_legal, True),
                ),
            )
            # --- 3. BISHOP (abs_piece == 3) ---
            .if_else(
                abs_piece.eq(3),
                exoscript.block().if_else(
                    abs_df.eq(abs_dr),
                    exoscript.block()
                    .call(check_ray_clear, wait=True)
                    .if_else(path_clear, exoscript.block().set_var(is_legal, True)),
                ),
            )
            # --- 4. ROOK (abs_piece == 4) ---
            .if_else(
                abs_piece.eq(4),
                exoscript.block().if_else(
                    exovar.or_(df.eq(0), dr.eq(0)),
                    exoscript.block()
                    .call(check_ray_clear, wait=True)
                    .if_else(path_clear, exoscript.block().set_var(is_legal, True)),
                ),
            )
            # --- 5. QUEEN (abs_piece == 5) ---
            .if_else(
                abs_piece.eq(5),
                exoscript.block().if_else(
                    exovar.or_(
                        abs_df.eq(abs_dr),
                        exovar.or_(df.eq(0), dr.eq(0)),
                    ),
                    exoscript.block()
                    .call(check_ray_clear, wait=True)
                    .if_else(path_clear, exoscript.block().set_var(is_legal, True)),
                ),
            )
            # --- 6. KING (abs_piece == 6) ---
            .if_else(
                abs_piece.eq(6),
                exoscript.block().if_else(
                    exovar.and_(exovar.le(abs_df, 1), exovar.le(abs_dr, 1)),
                    exoscript.block().set_var(is_legal, True),
                ),
            ),
        )
    )


# ---------------------------------------------------------------------------
# 7. Main Interactive Input & Move Execution Loop
# ---------------------------------------------------------------------------
main_sc = exoscript.create("ChessEngine", activation_count=1)
main_sc.on(0)

pw = exovar.pointer_world_pos()
raw_f = exovar.floor_int(exovar.vec_x(pw) + 4.0)
raw_r = exovar.floor_int(exovar.vec_y(pw) + 4.0)
clamped_f = exovar.max_int(0, exovar.min_int(7, raw_f))
clamped_r = exovar.max_int(0, exovar.min_int(7, raw_r))

main_sc.call(refresh_hud, wait=True)

frame_loop = (
    exoscript.block()
    # Snap pointer into 0..7 file/rank integers and board world coordinates
    .set_var(cur_f, clamped_f)
    .set_var(cur_r, clamped_r)
    .set_var(cur_idx, cur_r * 8 + cur_f)
    .set_var(
        cur_pos,
        exovar.vec_values(
            exovar.to_float(cur_f) - 3.5,
            exovar.to_float(cur_r) - 3.5,
        ),
    )
    .move(hover_ring, cur_pos, is_global=True, duration=0.0)
    # Jump + Left cancels current piece selection
    .if_else(
        exovar.and_(exovar.input_held(), exovar.input_pressed_left()),
        exoscript.block()
        .set_var(has_selection, False)
        .move(selected_ring, (0.0, -100.0), is_global=True, duration=0.0)
        .set_var(status_str, "Selection cancelled")
        .call(refresh_hud, wait=True),
    )
    # Handle click/tap when game is active
    .if_else(
        exovar.and_(exovar.pointer_down(), exovar.not_(game_over)),
        exoscript.block()
        .set_var(query_idx, cur_idx)
        .call(read_board, wait=True)
        .if_else(
            exovar.not_(has_selection),
            # --- STEP A: Select a friendly piece ---
            exoscript.block().if_else(
                exovar.gt(query_val * turn_side, 0),
                exoscript.block()
                .set_var(sel_f, cur_f)
                .set_var(sel_r, cur_r)
                .set_var(sel_idx, cur_idx)
                .set_var(sel_code, query_val)
                .set_var(sel_pos, cur_pos)
                .set_var(has_selection, True)
                .move(selected_ring, cur_pos, is_global=True, duration=0.0)
                .play_sound("click", volume=0.7, pitch=1.3)
                .set_var(status_str, "Piece selected — click a valid destination square")
                .call(refresh_hud, wait=True),
                exoscript.block()
                .play_sound("click", volume=0.4, pitch=0.7)
                .set_var(status_str, "Select one of your own pieces")
                .call(refresh_hud, wait=True),
            ),
            # --- STEP B: Switch selection if clicking another friendly piece, else validate move ---
            exoscript.block().if_else(
                exovar.gt(query_val * turn_side, 0),
                exoscript.block()
                .set_var(sel_f, cur_f)
                .set_var(sel_r, cur_r)
                .set_var(sel_idx, cur_idx)
                .set_var(sel_code, query_val)
                .set_var(sel_pos, cur_pos)
                .move(selected_ring, cur_pos, is_global=True, duration=0.0)
                .play_sound("click", volume=0.7, pitch=1.3)
                .set_var(status_str, "Switched selected piece")
                .call(refresh_hud, wait=True),
                exoscript.block()
                .call(validate_move, wait=True)
                .if_else(
                    is_legal,
                    exoscript.block()
                    # Locate moving visual token & glyph on sel_pos
                    .set_var(moving_token, exovar.closest_from_point(token_set, sel_pos))
                    .set_var(moving_glyph, exovar.closest_from_point(glyph_set, sel_pos))
                    # Handle capture if target square holds an enemy piece
                    .if_else(
                        exovar.ne(target_code, 0),
                        exoscript.block()
                        .set_var(captured_token, exovar.closest_from_point(token_set, cur_pos))
                        .set_var(captured_glyph, exovar.closest_from_point(glyph_set, cur_pos))
                        .move(captured_token, (0.0, -100.0), is_global=True, duration=0.0)
                        .move(captured_glyph, (0.0, -100.0), is_global=True, duration=0.0)
                        .play_sound("hit", volume=0.95, pitch=1.1)
                        .camera_shake(strength=0.22, duration=0.08),
                        exoscript.block().play_sound("blip", volume=0.8, pitch=1.0),
                    )
                    # Clear origin square in board_vars
                    .set_var(write_idx, sel_idx)
                    .set_var(write_val, 0)
                    .call(write_board, wait=True)
                    # Check Pawn Promotion on back rank (White r=7 -> +5, Black r=0 -> -5)
                    .if_else(
                        exovar.and_(
                            exovar.abs_int(sel_code).eq(1),
                            exovar.or_(
                                exovar.and_(turn_side.eq(1), cur_r.eq(7)),
                                exovar.and_(turn_side.eq(-1), cur_r.eq(0)),
                            ),
                        ),
                        exoscript.block()
                        .set_var(sel_code, 5 * turn_side)
                        .if_else(
                            turn_side.eq(1),
                            exoscript.block().set_text(moving_glyph, "♕"),
                            exoscript.block().set_text(moving_glyph, "♛"),
                        ),
                    )
                    # Write piece code to destination square in board_vars
                    .set_var(write_idx, cur_idx)
                    .set_var(write_val, sel_code)
                    .call(write_board, wait=True)
                    # Animate moving piece token & glyph to cur_pos
                    .move(moving_token, cur_pos, is_global=True, duration=0.12, wait=False)
                    .move(moving_glyph, cur_pos, is_global=True, duration=0.12, wait=True)
                    # Check if enemy King (abs(target_code) == 6) was captured
                    .if_else(
                        exovar.abs_int(target_code).eq(6),
                        exoscript.block()
                        .set_var(game_over, True)
                        .if_else(
                            turn_side.eq(1),
                            exoscript.block().set_var(turn_str, "CHECKMATE — WHITE WINS!"),
                            exoscript.block().set_var(turn_str, "CHECKMATE — BLACK WINS!"),
                        )
                        .set_var(status_str, "Game over! Restart level to play again"),
                        exoscript.block()
                        .set_var(turn_side, 0 - turn_side)
                        .set_var(move_number, move_number + 1)
                        .set_var(status_str, "Move accepted"),
                    )
                    .set_var(has_selection, False)
                    .move(selected_ring, (0.0, -100.0), is_global=True, duration=0.0)
                    .call(refresh_hud, wait=True),
                    # Illegal move feedback
                    exoscript.block()
                    .play_sound("click", volume=0.5, pitch=0.55)
                    .set_var(status_str, "Illegal move for that piece!")
                    .call(refresh_hud, wait=True),
                ),
            ),
        ),
    )
    .wait_frames(1)
)

main_sc.repeat_while(True, frame_loop, wait=True).pack()

# ---------------------------------------------------------------------------
# 8. Export .exolvl & Decompile/Write output.py for GitHub Actions Workflow
# ---------------------------------------------------------------------------
lvl.export("chess.exolvl")
exo.decompile("chess.exolvl", out_py="output.py")
print("Built chess.exolvl and generated output.py successfully.")
