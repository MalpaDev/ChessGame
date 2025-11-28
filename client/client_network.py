import socket
import threading
import json
import time

class ClientNetwork:
    def __init__(self, host="127.0.0.1", port=5000, on_server_message=None):
        self.host = host
        self.port = port
        self.sock = None
        self.running = False
        self.on_server_message = on_server_message
        self.buffer = ""

    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            self.running = True
            threading.Thread(target=self.listen_loop, daemon=True).start()
            print("[CLIENT] Connected to server")
            return True
        except Exception as e:
            print("[CLIENT] Failed to connect:", e)
            return False

    def listen_loop(self):
        try:
            while self.running:
                data = self.sock.recv(4096)
                if not data:
                    break

                self.buffer += data.decode("utf-8")

                while "\n" in self.buffer:
                    line, self.buffer = self.buffer.split("\n", 1)
                    if not line.strip():
                        continue

                    try:
                        msg = json.loads(line)
                        print("[CLIENT RECEIVED]", msg)
                        if self.on_server_message:
                            self.on_server_message(msg)
                    except json.JSONDecodeError:
                        print("[CLIENT] JSON parse error:", line)
        except:
            pass
        finally:
            self.running = False
            try:
                self.sock.close()
            except:
                pass

    def send_json(self, obj):
        try:
            print("[CLIENT SEND]", obj)
            s = json.dumps(obj) + "\n"
            self.sock.sendall(s.encode("utf-8"))
        except Exception as e:
            print("[CLIENT SEND ERROR]", e)

    def send_ready(self):
        self.send_json({"type":"ready"})

    def send_move(self, src, dst):
        self.send_json({
            "type": "move",
            "from": src,
            "to": dst,
            "timestamp": time.time()
        })

    def close(self):
        self.running = False
        try:
            self.sock.close()
        except:
            pass