"""Core move analysis and metric calculations."""

from chess_analysis.engine import (
    BISHOP,
    BLACK,
    KNIGHT,
    PAWN,
    QUEEN,
    ROOK,
    WHITE,
    analyze_position,
    mate_for_player,
    piece_name,
    principal_variation,
    score_for_player,
)


def parse_clock(comment):
    """Return a clock comment's remaining time in seconds, or None."""
    marker = "[%clk "
    start = comment.find(marker)

    if start == -1:
        return None

    value = comment[start + len(marker) :].split("]", 1)[0]
    parts = value.split(":")

    if len(parts) != 3:
        return None

    hours, minutes, seconds = parts

    try:
        return int(hours) * 3600 + int(minutes) * 60 + int(seconds)
    except ValueError:
        return None


def result_for_player(game, player_color):
    """Return the game result from the selected player's perspective."""
    termination = game.headers.get("Termination", "").lower()

    if "time" in termination or "flag" in termination:
        return "timeout"

    result = game.headers.get("Result", "")

    if result == "1/2-1/2":
        return "draw"
    if result == "1-0":
        return "win" if player_color == WHITE else "loss"
    if result == "0-1":
        return "loss" if player_color == WHITE else "win"

    return ""


def game_phase(board):
    """Roughly classify a position as opening, middlegame, or endgame."""
    if board.fullmove_number <= 10:
        return "opening"

    values = {
        KNIGHT: 3,
        BISHOP: 3,
        ROOK: 5,
        QUEEN: 9,
    }
    non_pawn_material = sum(
        (len(board.pieces(piece_type, WHITE)) + len(board.pieces(piece_type, BLACK)))
        * value
        for piece_type, value in values.items()
    )

    return "endgame" if non_pawn_material <= 20 else "middlegame"


def classify_loss(loss):
    """Classify a move by its centipawn loss."""
    if loss < 20:
        return "good"
    if loss < 50:
        return "inaccuracy"
    if loss < 100:
        return "mistake"
    return "blunder"


def material_balance(board, color):
    """Return material balance in pawns from the player's perspective."""
    values = {
        PAWN: 1,
        KNIGHT: 3,
        BISHOP: 3,
        ROOK: 5,
        QUEEN: 9,
    }

    return sum(
        value
        * (
            len(board.pieces(piece_type, color))
            - len(board.pieces(piece_type, not color))
        )
        for piece_type, value in values.items()
    )


def analyze_game(engine, game, player, depth):
    """Analyze every move made by player in one game."""
    white = game.headers.get("White", "")
    black = game.headers.get("Black", "")

    if white.lower() == player.lower():
        player_color, opponent = WHITE, black
        player_rating = game.headers.get("WhiteElo", "")
        opponent_rating = game.headers.get("BlackElo", "")
    elif black.lower() == player.lower():
        player_color, opponent = BLACK, white
        player_rating = game.headers.get("BlackElo", "")
        opponent_rating = game.headers.get("WhiteElo", "")
    else:
        return []

    board = game.board()
    rows = []
    previous_clocks = {WHITE: None, BLACK: None}
    time_since_last_move = {WHITE: None, BLACK: None}

    for node in game.mainline():
        move = node.move
        move_color = board.turn
        clock = parse_clock(node.comment)

        if clock is not None and previous_clocks[move_color] is not None:
            time_since_last_move[move_color] = previous_clocks[move_color] - clock
        if clock is not None:
            previous_clocks[move_color] = clock

        if move_color != player_color:
            board.push(move)
            continue

        fen_before = board.fen()
        move_number = board.fullmove_number
        ply = board.ply() + 1
        san = board.san(move)
        phase = game_phase(board)
        piece_at_move = board.piece_at(move.from_square)
        piece = piece_name(piece_at_move.piece_type) if piece_at_move else ""
        material_before = material_balance(board, player_color)
        capture = board.is_capture(move)
        castling = board.is_castling(move)
        en_passant = board.is_en_passant(move)

        before = analyze_position(engine, board, depth)
        before_score = score_for_player(before, player_color)
        mate_before = mate_for_player(before, player_color)
        pv = before.get("pv", [])
        best_move = pv[0] if pv else None
        best_san = board.san(best_move) if best_move else ""
        best_pv = principal_variation(board, before)

        board.push(move)
        after = analyze_position(engine, board, depth)
        after_score = score_for_player(after, player_color)
        mate_after = mate_for_player(after, player_color)
        loss = max(0, before_score - after_score)

        rows.append(
            {
                "date": game.headers.get("Date", ""),
                "result": result_for_player(game, player_color),
                "color": "White" if player_color else "Black",
                "opponent": opponent,
                "my_rating": player_rating,
                "opponent_rating": opponent_rating,
                "time_since_my_last_move": (
                    time_since_last_move[player_color]
                    if time_since_last_move[player_color] is not None
                    else ""
                ),
                "time_since_my_opponents_move": (
                    time_since_last_move[not player_color]
                    if time_since_last_move[not player_color] is not None
                    else ""
                ),
                "my_time_remaining": clock if clock is not None else "",
                "move_number": move_number,
                "ply": ply,
                "phase": phase,
                "piece": piece,
                "move": san,
                "best_move": best_san,
                "played_best_move": move == best_move,
                "principal_variation": best_pv,
                "eval_before": before_score,
                "eval_after": after_score,
                "centipawn_loss": loss,
                "classification": classify_loss(loss),
                "mate_before": mate_before if mate_before is not None else "",
                "mate_after": mate_after if mate_after is not None else "",
                "capture": capture,
                "check": board.is_check(),
                "castling": castling,
                "en_passant": en_passant,
                "material_before": material_before,
                "material_after": material_balance(board, player_color),
                "fen": fen_before,
            }
        )

    return rows
