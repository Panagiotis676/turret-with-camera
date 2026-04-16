# 🎯 Turret Vision - To-Do List

## 🔴 CRITICAL - DO FIRST

### Hardware Bring-Up
- [ ] **Upload Arduino Sketch** - Flash `hardware/arduino/servo_controller/servo_controller.ino` to the board
- [ ] **Confirm COM Port Access** - Make sure no other app is holding the Arduino port open before running Python
- [ ] **Run Full System Test** - Start `python -m src.main` with camera + Arduino connected
- [ ] **Verify Servo Direction** - Confirm X/Y axes move in the expected direction
- [ ] **Verify Servo Travel Is Safe** - Check the current mapping does not hit mechanical stops
- [ ] **Calibrate `DEG_PER_PIXEL`** - Tune `DEG_PER_PIXEL = 0.08` in `src/main.py` to match real hardware response
- [ ] **Calibrate `INPUT_RANGE_DEG`** - Tune `INPUT_RANGE_DEG = 45` in the Arduino sketch for the amount of servo movement you want

### Safety
- [ ] **Add Emergency Stop** - Keyboard shortcut that immediately stops aim output and disables fire
- [ ] **Safe Mode on Startup** - Require an explicit enable step before any firing logic is active
- [ ] **Physical Safety Interlocks** - Add a hardware kill switch before mounting any actuator

---

## 🟡 HIGH PRIORITY - DO SOON

### Active Runtime Work
- [ ] **Test `FIRE_COOLDOWN`** - Current `2.0s`; verify it feels right with real hardware
- [ ] **Tune `CENTER_TOLERANCE`** - Current `20px`; confirm alignment accuracy
- [ ] **Adjust `SURVEILLANCE_SPEED`** - Current `15°/s`; test smoothness during idle sweep
- [ ] **Verify `surveillance_range`** - Current `±90°`; ensure it stays within safe mechanical range
- [ ] **Add Serial Readback Diagnostics** - Show incoming Arduino acknowledgements/status while testing
- [ ] **Add FPS Counter** - Display live performance on screen for easier troubleshooting

### Visual / Control Polish
- [ ] **Restore Clear Mode Indicator** - Show larger `TARGETING` / `SURVEILLANCE` text in the camera window
- [ ] **Better Crosshair** - Improve the center reticle overlay
- [ ] **Target Lock Indicator** - Stronger visual feedback when the target is aligned and ready
- [ ] **Neutralized Count Display** - Show how many targets were marked neutralized

---

## 🟢 MEDIUM PRIORITY - NICE TO HAVE

### Performance / Robustness
- [x] **Keep `cv2.imshow()` Always On** - Camera window stays active in `src/main.py`
- [x] **Move YOLO Off the UI Loop** - Detection runs in a background worker thread
- [x] **Reuse Cached Detection Results** - Latest YOLO output is reused between inference intervals
- [x] **Reduce Per-Frame Overhead** - Logging is throttled and hot-path work is minimized
- [x] **Reduce Camera Buffer Lag** - Camera buffer/FPS guardrails are applied where supported
- [ ] **Profile Runtime** - Measure CPU/RAM use with camera + Arduino attached
- [ ] **Optimize Model Backend** - Consider ONNX / TensorRT only if needed after profiling
- [ ] **Optional Frame Skipping** - Add a fallback mode if performance is still poor on weaker hardware

### Features
- [ ] **Logging System** - Log fire events with timestamp, target ID, and aim offset
- [ ] **Config File** - Move tuneable parameters out of `src/main.py`
- [ ] **Ammo Counter** - Track and display shots fired
- [ ] **Recording Mode** - Save annotated video for debugging/testing

---

## 🔵 LOW PRIORITY - FUTURE IDEAS

### Advanced Tracking
- [ ] **Kalman Filter** - Predict and smooth target motion
- [ ] **Velocity Estimation** - Track direction and speed of movement
- [ ] **Threat Scoring** - Prioritize more dangerous / closer targets better
- [ ] **Occlusion Handling** - Improve multi-object tracking when people cross paths

### Intelligence / Expansion
- [ ] **Friend/Foe Recognition** - Custom model or additional filtering before fire logic
- [ ] **Face Recognition** - Remember and skip known friendly faces
- [ ] **Sound Detection** - Audio-triggered surveillance cues
- [ ] **Multi-Camera Array** - Expand field of view beyond one camera
- [ ] **Web Dashboard** - Remote monitoring / control
- [ ] **Mobile App Control** - Smartphone-based controls
- [ ] **Edge TPU Support** - Hardware acceleration for inference
- [ ] **Predictive Aiming** - Lead moving targets
- [ ] **Auto-Calibration** - Automatically estimate field-of-view / degrees-per-pixel
- [ ] **Night Vision** - IR camera support for low-light environments

---

## 🛠️ CODE QUALITY - TECHNICAL DEBT

### Testing
- [ ] **Unit Tests** - Test `CentroidTracker` matching behavior
- [ ] **Integration Tests** - Mock serial I/O and validate command flow
- [ ] **Performance Tests** - Benchmark responsiveness with different YOLO intervals/models

### Documentation
- [ ] **Docstrings Coverage** - Fill in missing docstrings across the codebase
- [ ] **Architecture Diagram** - Visual overview of camera, tracker, YOLO, and serial flow
- [ ] **Serial Protocol Note** - Document the `aim,dx,dy,fire` message format clearly

### Code Style
- [ ] **Type Hints** - Expand type annotations through the main control flow
- [ ] **Linting** - Run and fix linter warnings
- [ ] **Formatting** - Apply consistent formatting across Python files

---

## ✅ COMPLETED

- [x] **PyCharm Import Fix** - `setuptools`/`pkg_resources` issue addressed in the environment setup
- [x] **Centroid Tracker** - Persistent ID tracking is in place
- [x] **Neutralized Memory** - Avoids re-targeting neutralized IDs for a long interval
- [x] **Surveillance Mode** - Constant-speed sweep when idle
- [x] **Manual Fire Key** - `F` requests a fire action on the current target
- [x] **Fix Self-Firing Bug** - Fire is no longer tied to stray key-read logic
- [x] **Degree-Based Control** - Python sends degree offsets instead of raw pixel deltas
- [x] **Single Camera Window Path** - One display/update path in `src/main.py`
- [x] **Target Scoring** - Chooses a best target using area and center distance
- [x] **Arduino Degree Mapping** - Arduino sketch maps incoming degree offsets into servo angles
- [x] **Mock Serial Fallback** - Project can run without an available serial device

---

## 📌 QUICK REFERENCE

### How to Run
```bash
.venv\Scripts\activate
python -m src.main
```

### Key Bindings
- **Q** - Quit program
- **F** - Manual fire request for the currently tracked target

### Main Files
- `src/main.py` - Main GUI/runtime loop
- `hardware/arduino/servo_controller/servo_controller.ino` - Arduino servo control
- `centroid_tracker.py` - Tracking algorithm
- `src/serial_comm.py` - Serial communication

### Serial Message Format
- Python sends: `aim,dx,dy,fire`
- Example: `aim,12,-4,0`

---

**Last Updated**: March 17, 2026
