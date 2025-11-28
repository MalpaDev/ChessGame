import subprocess
import time
import sys
import os

def run():
    root_path = os.path.dirname(os.path.abspath(__file__))
    server_path = os.path.join(root_path, "server", "server.py")
    client_path = os.path.join(root_path, "client", "client_gui.py")

    print("[MAIN] Starting server...")
    server_proc = subprocess.Popen([sys.executable, server_path])

    time.sleep(1.2)

    print("[MAIN] Launching Client 1...")
    client1_proc = subprocess.Popen([sys.executable, client_path])
    time.sleep(0.5)

    print("[MAIN] Launching Client 2...")
    client2_proc = subprocess.Popen([sys.executable, client_path])

    print("\n[MAIN] Server + 2 clients launched successfully!")
    print("[MAIN] Close clients to exit, or press Ctrl+C here.\n")

    try:
        while True:
            time.sleep(1)
            if server_proc.poll() is not None:
                print("[MAIN] Server closed — shutting down clients...")
                client1_proc.terminate()
                client2_proc.terminate()
                break
            if client1_proc.poll() is not None and client2_proc.poll() is not None:
                print("[MAIN] Both clients closed — shutting down server...")
                server_proc.terminate()
                break
    except KeyboardInterrupt:
        print("[MAIN] CTRL+C detected — closing all processes...")
        server_proc.terminate()
        client1_proc.terminate()
        client2_proc.terminate()

if __name__ == "__main__":
    run()