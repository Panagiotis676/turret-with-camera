# Turret vision — Laptop server + Arduino actuator

Quick start (prototype using your laptop as inference server and Arduino for motors):

1) Create a virtual environment and install deps:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

2) Put `yolov8n.pt` in the project root (already present) or update `src/main.py` to the model path.

3) Edit `src/main.py` and set `serial_port` to your Arduino COM port (e.g. `COM3`). Then run:

```bash
python -m src.main
```

4) Flash the Arduino sketch in `hardware/arduino/servo_controller.ino` to your Arduino (adjust servo pins as needed).

Notes
- The Python server sends simple CSV commands over serial like `aim,dx,dy,fire`.
- Arduino reads the line and moves servos proportionally. Adjust `scale` and mapping for your hardware.
- This is a prototype. Add safety interlocks before attaching any actuator.
