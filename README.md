# Turret Vision — Laptop Server + Arduino Actuator

**Smart tracking turret using YOLOv8 person detection with intelligent target prioritization and autonomous surveillance.**

## 🎯 Features

- **🎥 Real-time Person Detection** - YOLOv8n for fast, accurate detection
- **🔍 Persistent Tracking** - Centroid tracker maintains target IDs across frames
- **🎯 Smart Targeting** - Prioritizes threats by size and center proximity
- **🚫 No Re-engagement** - Remembers neutralized targets for 1000 seconds
- **👁️ Surveillance Mode** - Constant-speed sweep patrol when no targets detected
- **🎮 Manual Control** - Press 'F' for manual fire override
- **📡 Serial Communication** - Degree-based commands to Arduino servo controller
- **⚙️ Configurable** - Easy parameter tuning for different setups

## 🚀 Quick Start

### 1. Setup Python Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Serial Port

Edit `src/main.py` line 166:
```python
run(camera_index=0, serial_port='COM3')  # Change COM3 to your Arduino port
```

### 3. Run the Program

```bash
# With Arduino connected
python -m src.main

# Test mode (no hardware, uses text-to-speech)
python test1.py
```

### 4. Flash Arduino

Upload `hardware/arduino/servo_controller.ino` to your Arduino board.

> ⚠️ **Note**: Arduino code needs updating for degree-based protocol. See TODO.md

## 🎮 Controls

| Key | Action |
|-----|--------|
| **F** | Manual fire at locked target |
| **Q** | Quit program |

## 📊 Current Status

✅ **Working**:
- Person detection and tracking
- Target prioritization algorithm
- Surveillance sweep mode
- Serial communication (mock mode)
- Manual fire control

⚠️ **Needs Testing**:
- Arduino integration (requires hardware)
- Servo calibration
- Degree-to-pixel conversion tuning

🔴 **To Do**:
- Update Arduino code for new protocol
- Add safety interlocks
- Hardware testing

## 📁 Project Structure

```
turret/
├── src/
│   ├── main.py              # Main control loop (production)
│   ├── serial_comm.py       # Serial communication wrapper
│   └── yolov8n.pt           # YOLO model
├── hardware/
│   └── arduino/
│       └── servo_controller.ino  # Arduino servo control
├── centroid_tracker.py      # Persistent ID tracking algorithm
├── test1.py                 # Test mode (text-to-speech, no hardware)
├── requirements.txt         # Python dependencies
├── README.md                # This file
├── TODO.md                  # Prioritized task list
├── IMPROVEMENTS.md          # Algorithm details and fixes
└── CHANGELOG.md             # Version history
```

## ⚙️ Configuration

Key parameters in `src/main.py`:

```python
CENTER_TOLERANCE = 20        # Pixels - fire when within this distance
FIRE_COOLDOWN = 2.0          # Seconds between shots
CLEAR_INTERVAL = 1000.0      # Seconds before forgetting neutralized targets
SURVEILLANCE_SPEED = 15      # Degrees/second for patrol sweep
DEG_PER_PIXEL = 0.08         # Degrees per pixel (tune to your camera FOV)
surveillance_range = 90      # Sweep ±90 degrees
```

CentroidTracker parameters:
```python
max_disappeared = 30         # Frames before forgetting lost target
max_distance = 120           # Max pixels to match detection to track
```

## 📡 Serial Protocol

Python → Arduino: `aim,dx_deg,dy_deg,fire\n`

- `dx_deg`: Horizontal angle in degrees
- `dy_deg`: Vertical angle in degrees  
- `fire`: 1 to fire, 0 otherwise

Example: `aim,15,-5,0\n` = Aim 15° right, 5° down, don't fire

## 🎨 Visual Indicators

| Color | Meaning |
|-------|---------|
| 🟢 Green box | Active target (tracking) |
| ⚪ Gray box | Neutralized target (skip) |
| 🔵 Blue circle | Frame center (aim point) |
| 🔴 Red line | Aim vector to target |

**Mode Display**:
- `MODE: TARGETING` (green) - Locked on target
- `MODE: SURVEILLANCE` (orange) - Patrol sweep

## 🔧 Troubleshooting

### PyCharm Import Errors
```bash
# If you see: ModuleNotFoundError: No module named 'pkg_resources'
pip install setuptools
```

### Camera Won't Open
```bash
# Try different camera index
run(camera_index=1, serial_port=None)  # Try 1, 2, etc.
```

### Serial Port Issues
- **Windows**: Check Device Manager for COM port (COM3, COM4, etc.)
- **Linux**: Usually `/dev/ttyUSB0` or `/dev/ttyACM0`
- **Mac**: Usually `/dev/cu.usbserial-*`

## 📚 Documentation

- **[TODO.md](TODO.md)** - Prioritized task list with detailed action items
- **[IMPROVEMENTS.md](IMPROVEMENTS.md)** - Algorithm comparison and technical details
- **[CHANGELOG.md](CHANGELOG.md)** - Complete version history

## ⚠️ Safety Warning

This is a **prototype system** for educational purposes.

**Before connecting any actuator**:
- ✅ Implement physical kill switch
- ✅ Add software emergency stop
- ✅ Test extensively in safe environment
- ✅ Follow all local laws and regulations
- ✅ Never aim at people or animals

## 📝 Notes

- YOLOv8n model (`yolov8n.pt`) must be in project root or `src/` folder
- Uses DirectShow backend for camera (Windows) with fallback to default
- Mock serial mode automatically activates if pyserial not installed or port is None
- Centroid tracker may assign new IDs after long occlusions (>30 frames)

## 🤝 Contributing

This is a personal project. Feel free to fork and adapt for your own use.

## 📄 License

For educational and research purposes. Use responsibly.

---

**Version**: 1.2.0  
**Last Updated**: February 24, 2026  
**Status**: Development (Hardware testing pending)

