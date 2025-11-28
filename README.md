# Multiplayer Chess Simulation
This project is a **multiplayer chess simulation** built in **Python**, featuring a Tkinter graphical interface, synchronized multiplayer communication using sockets, and distributed-systems time correction using **Cristian’s Algorithm**.

The project begins with **standard chess** and later expands to include the custom **North Sea Chess** variant inspired by *A Returner’s Magic Should Be Special*.

---

## 📌 Features

### ✔ Graphical User Interface (Tkinter)
- Interactive 8×8 chessboard  
- Click-based piece selection and movement  
- Shape-based chess pieces (triangles, squares, L-shapes, diamonds, etc.)  
- Turn-based system (White → Black)  
- Highlighted selection indicator  
- Local gameplay suitable for the first demo  

---

### ✔ Multiplayer Networking (Localhost)
- Server handles two client connections  
- Clients send moves to server as JSON messages  
- Server broadcasts ordered actions to both players  
- Uses `localhost` / `127.0.0.1` for easy local testing  
- Networking code kept separate from GUI  

---

### ✔ Clock Drift & Synchronization
This project simulates time inconsistencies found in distributed systems:

- Each client runs its own **drifting local clock**  
- Clients periodically request server time  
- Server uses **Cristian’s Algorithm** to provide corrected time  
- Clients adjust their clocks to maintain fairness  
- Server orders moves according to synchronized timestamps  

---

### ✔ Latency Simulation
- Optional artificial network delay  
- Shows how ordering is preserved even with connection lag  
- Useful for demonstrating fairness in multiplayer systems  

---