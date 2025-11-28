import socket
import threading
import json
import time
import chess

HOST = "127.0.0.1"
PORT = 5000

# Global State
players = []
players_lock = threading.Lock()
game_active = False
board = chess.Board()

white_time = 120.0
black_time = 120.0
turn = "white"
last_server_time = None

# Utility
def safe_send(conn, obj):
    try:
        data = json.dumps(obj) + "\n"
        conn.sendall(data.encode("utf-8"))
    except Exception as e:
        print("[SERVER ERROR]", e)

def broadcast(obj):
    with players_lock:
        for p in players:
            safe_send(p["conn"], obj)

def get_opponent_color(color):
    return "black" if color == "white" else "white"

def deduct_time():
    # Deducts time from the player who has the move
    global white_time, black_time, turn, last_server_time

    now = time.time()
    if last_server_time is None:
        last_server_time = now
        return

    elapsed = now - last_server_time
    last_server_time = now

    if turn == "white":
        white_time = max(0.0, white_time - elapsed)
    else:
        black_time = max(0.0, black_time - elapsed)

# Game Start
def try_start_game():
    global game_active, last_server_time, board
    with players_lock:
        if len(players) != 2:
            return
        if any(not p["ready"] for p in players):
            return

        # All players ready → start game
        print("[SERVER] All players READY → Starting game!")
        game_active = True
        board = chess.Board()
        last_server_time = time.time()

        for p in players:
            safe_send(p["conn"], {
                "type": "game_start",
                "color": p["color"],
                "fen": board.fen(),
                "white_time": white_time,
                "black_time": black_time,
                "turn": "white",
                "server_time": last_server_time
            })

# Move Handling
def handle_move(player_color, msg, conn):
    global board, turn, white_time, black_time

    if not game_active:
        return

    src = msg["from"]
    dst = msg["to"]

    # Convert from array to UCI string
    def to_uci(square):
        r, c = square
        col = "abcdefgh"[c]
        row = str(8 - r)
        return col + row

    uci_move = to_uci(src) + to_uci(dst)

    # Enforce turn order
    if player_color != turn:
        safe_send(conn, {"type": "illegal_move", "reason": "Not your turn"})
        return

    try:
        move = chess.Move.from_uci(uci_move)
        if move not in board.legal_moves:
            safe_send(conn, {"type": "illegal_move", "reason": "Illegal move"})
            return
    except:
        safe_send(conn, {"type": "illegal_move", "reason": "Invalid UCI"})
        return

    # Deduct time for the moving player BEFORE applying move
    deduct_time()

    board.push(move)

    # Switch turn
    turn_color = "white" if board.turn == chess.WHITE else "black"
    turn = turn_color

    now = time.time()

    # Send move to both players
    broadcast({
        "type": "move_accepted",
        "fen": board.fen(),
        "turn": turn,
        "white_time": white_time,
        "black_time": black_time,
        "server_time": now
    })

    # Game end?
    if board.is_game_over():
        result = board.result()
        broadcast({"type": "game_over", "reason": f"Game Over: {result}"})


# Client Listener Thread
def client_listener(conn, addr, color):
    global game_active

    print(f"[SERVER] Listener started for {addr}")

    try:
        buffer = ""
        while True:
            data = conn.recv(4096)
            if not data:
                break

            buffer += data.decode("utf-8")
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if not line.strip():
                    continue

                msg = json.loads(line)
                print("[SERVER] Received:", msg)

                t = msg.get("type")

                if t == "ready":
                    with players_lock:
                        for p in players:
                            if p["conn"] == conn:
                                p["ready"] = True
                                print("[SERVER] Player READY:", addr)
                                break
                    try_start_game()

                elif t == "move":
                    handle_move(color, msg, conn)

    except Exception as e:
        print("[SERVER ERROR]", e)

    finally:
        print("[SERVER] Client disconnected:", addr)
        with players_lock:
            for p in players:
                if p["conn"] == conn:
                    players.remove(p)
                    break
        conn.close()
        game_active = False


# Main Server Loop
def start_server():
    global players, game_active, board, white_time, black_time, turn

    print(f"[SERVER] Listening on {HOST}:{PORT}")

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(5)

    while True:
        conn, addr = s.accept()
        print("[SERVER] Client connected:", addr)

        with players_lock:
            color = "white" if len(players) == 0 else "black"
            players.append({
                "conn": conn,
                "addr": addr,
                "color": color,
                "ready": False
            })

            safe_send(conn, {"type": "join_accepted", "color": color})

        # Start listener
        threading.Thread(target=client_listener,
                         args=(conn, addr, color),
                         daemon=True).start()


if __name__ == "__main__":
    start_server()