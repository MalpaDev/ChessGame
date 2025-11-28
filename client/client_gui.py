import tkinter as tk
from tkinter import messagebox
import time
import json
from client_network import ClientNetwork

BOARD_SIZE = 8
SQUARE_SIZE = 80
LIGHT_COLOR = "#F0D9B5"
DARK_COLOR = "#B58863"
HIGHLIGHT_COLOR = "#FFFB7D"

class ChessGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Multiplayer Chess Client")

        # Networking
        self.network = ClientNetwork(on_server_message=self.on_server_message)

        # Game State
        self.board = {}
        self.my_color = None
        self.current_turn = None
        self.game_active = False
        self.selected_square = None
        self.highlight_id = None

        # Clock State
        self.base_white_time = 120.0
        self.base_black_time = 120.0
        self.server_offset = 0.0
        self.last_sync_server_time = None

        # UI Setup
        self.menu_frame = tk.Frame(self.root)
        self.menu_frame.pack(fill=tk.BOTH, expand=True)
        self.build_main_menu()

        self.game_frame = tk.Frame(root)

        # smooth clock update
        self.root.after(30, self.update_local_clocks)


    def build_main_menu(self):
        tk.Label(self.menu_frame, text="Multiplayer Chess", font=("Arial", 20)).pack(pady=10)
        tk.Button(self.menu_frame, text="New Game", command=self.start_new_game).pack(pady=5)
        tk.Button(self.menu_frame, text="Exit", command=self.root.quit).pack(pady=5)
        self.status = tk.Label(self.menu_frame, text="", fg="blue")
        self.status.pack()

    def start_new_game(self):
        if not self.network.running:
            ok = self.network.connect()
            if not ok:
                messagebox.showerror("Connection Failed", "Could not connect to server.")
                return
        self.status.config(text="Waiting for opponent...")
        print("[GUI] Sending READY...")
        self.network.send_ready()


    def build_game_ui(self):
        print("[GUI] Building game UI...")
        self.menu_frame.pack_forget()
        self.game_frame.pack(fill=tk.BOTH, expand=True)

        self.op_timer_label = tk.Label(self.game_frame, text="Opponent: 2:00.000", font=("Arial",16))
        self.op_timer_label.pack()

        self.canvas = tk.Canvas(self.game_frame,
                                width=BOARD_SIZE*SQUARE_SIZE,
                                height=BOARD_SIZE*SQUARE_SIZE)
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_click)

        self.my_timer_label = tk.Label(self.game_frame, text="You: 2:00.000", font=("Arial",16))
        self.my_timer_label.pack()

        self.status_label = tk.Label(self.game_frame, text="", fg="black")
        self.status_label.pack()

        self.draw_board()

    def draw_board(self):
        self.canvas.delete("square")
        for r in range(8):
            for c in range(8):
                x=c*SQUARE_SIZE
                y=r*SQUARE_SIZE
                color = LIGHT_COLOR if (r+c)%2==0 else DARK_COLOR
                self.canvas.create_rectangle(x,y,x+SQUARE_SIZE,y+SQUARE_SIZE,
                                             fill=color,outline="",tags="square")
        self.canvas.tag_lower("square")

    def clear_pieces(self):
        self.canvas.delete("piece")
        self.board.clear()

    def draw_piece(self,pos,piece):
        r,c = pos
        x = c*SQUARE_SIZE
        y = r*SQUARE_SIZE
        cx = x + SQUARE_SIZE/2
        cy = y + SQUARE_SIZE/2
        color = "white" if piece["color"]=="white" else "black"

        pad=12
        left = x+pad
        top = y+pad
        right = x+SQUARE_SIZE-pad
        bottom = y+SQUARE_SIZE-pad

        t = piece["type"]
        ids=[]

        if t=="P":
            ids.append(self.canvas.create_polygon(
                [cx,top, left,bottom, right,bottom],
                fill=color, outline="", tags="piece"))
        elif t=="R":
            ids.append(self.canvas.create_rectangle(
                left,top,right,bottom,
                fill=color,outline="",tags="piece"))
        elif t=="N":
            thickness=16
            ids.append(self.canvas.create_rectangle(
                left,top,left+thickness,bottom,fill=color,outline="",tags="piece"))
            ids.append(self.canvas.create_rectangle(
                left,top,right,top+thickness,fill=color,outline="",tags="piece"))
        elif t=="B":
            ids.append(self.canvas.create_polygon(
                [cx,top, right,cy, cx,bottom, left,cy],
                fill=color,outline="",tags="piece"))
        elif t=="Q":
            crown=[left,bottom, left+12,cy, cx-10,top+10, cx,top+2,
                   cx+10,top+10, right-12,cy, right,bottom]
            ids.append(self.canvas.create_polygon(
                crown, fill=color, outline="", tags="piece"))
        elif t=="K":
            house=[cx,top, right,cy-5, right,bottom, left,bottom, left,cy-5]
            ids.append(self.canvas.create_polygon(
                house, fill=color, outline="", tags="piece"))

        piece["ids"]=ids

    def coords_to_display(self,fen_r,fen_c):
        if self.my_color=="white":
            return (fen_r,fen_c)
        return (7-fen_r,fen_c)

    def display_to_fen_coords(self,pos):
        r,c = pos
        if self.my_color=="white":
            return (r,c)
        return (7-r,c)

    def fen_to_board(self,fen):
        print("[GUI] Rendering board from FEN...")
        self.clear_pieces()
        ranks = fen.split()[0].split("/")

        for fen_r, rank in enumerate(ranks):
            file_idx=0
            for ch in rank:
                if ch.isdigit():
                    file_idx += int(ch)
                else:
                    color="white" if ch.isupper() else "black"
                    t=ch.upper()
                    disp = self.coords_to_display(fen_r,file_idx)
                    self.board[disp]={"type":t,"color":color}
                    file_idx+=1

        for pos,p in self.board.items():
            self.draw_piece(pos,p)

    def on_click(self,event):
        if not self.game_active:
            return
        if self.current_turn != self.my_color:
            self.flash("NOT your turn!")
            return

        col = event.x // SQUARE_SIZE
        row = event.y // SQUARE_SIZE
        pos=(row,col)

        if self.selected_square is None:
            if pos in self.board and self.board[pos]["color"] == self.my_color:
                self.select_square(pos)
            return

        src=self.display_to_fen_coords(self.selected_square)
        dst=self.display_to_fen_coords(pos)

        print("[GUI] Move display coords:", self.selected_square,"->",pos)
        print("[GUI] Move fen coords:", src,"->",dst)

        self.network.send_move(src,dst)
        self.clear_selection()

    def select_square(self,pos):
        self.selected_square=pos
        r,c=pos
        x=c*SQUARE_SIZE
        y=r*SQUARE_SIZE
        self.highlight_id=self.canvas.create_rectangle(
            x+2,y+2,x+SQUARE_SIZE-2,y+SQUARE_SIZE-2,
            outline=HIGHLIGHT_COLOR,width=4)

    def clear_selection(self):
        if self.highlight_id:
            self.canvas.delete(self.highlight_id)
        self.highlight_id=None
        self.selected_square=None

    def flash(self,text):
        self.status_label.config(text=text)
        self.root.after(800, lambda: self.status_label.config(text=""))

    def update_local_clocks(self):
        if self.game_active and self.last_sync_server_time is not None:
            est_server_time = time.time() + self.server_offset
            elapsed = est_server_time - self.last_sync_server_time

            w = self.base_white_time
            b = self.base_black_time

            if self.current_turn=="white":
                w=max(0,w - elapsed)
            elif self.current_turn=="black":
                b=max(0,b - elapsed)

            if self.my_color=="white":
                self.my_timer_label.config(text="You: "+self.format_clock(w))
                self.op_timer_label.config(text="Opponent: "+self.format_clock(b))
            else:
                self.my_timer_label.config(text="You: "+self.format_clock(b))
                self.op_timer_label.config(text="Opponent: "+self.format_clock(w))

        self.root.after(30, self.update_local_clocks)

    def format_clock(self,t):
        mins=int(t)//60
        secs=int(t)%60
        ms=int((t-int(t))*1000)
        return f"{mins}:{secs:02d}.{ms:03d}"

    def on_server_message(self,msg):
        print("[GUI] server msg:", msg)

        t = msg.get("type")

        if t=="join_accepted":
            return

        if t=="game_start":
            print("[GUI] GAME START RECEIVED!")
            self.my_color = msg["color"]
            self.current_turn = msg["turn"]

            self.base_white_time = msg["white_time"]
            self.base_black_time = msg["black_time"]
            self.last_sync_server_time = msg["server_time"]
            self.server_offset = msg["server_time"] - time.time()

            self.build_game_ui()

            self.fen_to_board(msg["fen"])
            self.game_active=True

        elif t=="move_accepted":
            print("[GUI] Turn switching to:", msg["turn"])
            self.current_turn=msg["turn"]

            self.base_white_time = msg["white_time"]
            self.base_black_time = msg["black_time"]
            self.last_sync_server_time = msg["server_time"]
            self.server_offset = msg["server_time"] - time.time()

            self.fen_to_board(msg["fen"])

        elif t=="illegal_move":
            self.flash("Illegal move")

        elif t=="game_over":
            self.flash(msg.get("reason","Game Over"))
            self.game_active=False


if __name__ == "__main__":
    root = tk.Tk()
    gui = ChessGUI(root)
    root.mainloop()