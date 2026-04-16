# Complete Testing Guide - Crash-Fixed Version

## Pre-Test Checklist

- [ ] Python venv activated: `.\.venv\Scripts\activate`
- [ ] Arduino connected to COM6
- [ ] Camera connected to laptop
- [ ] `yolov8n.pt` model file in root directory
- [ ] All Python packages installed: `pip install -r requirements.txt`

## Test 1: Verify Camera Works (2 minutes)

Run this first to ensure camera is working:

```bash
python test_camera.py
```

**Expected output:**
```
============================================================
CAMERA DETECTION & DIAGNOSIS
============================================================

🔍 Testing camera index 0...
   Attempting with CAP_DSHOW...
   ✅ SUCCESS with CAP_DSHOW!
   ✅ Frame captured! Size: (480, 640, 3)

✅ FOUND WORKING CAMERA: index=0, backend=CAP_DSHOW
```

✅ **If you see this**: Camera is working, continue to Test 2

❌ **If you see errors**: Camera not detected, check Device Manager

---

## Test 2: Verify YOLO Loads (3 minutes)

Run to verify the model loads:

```bash
python startup_test.py
sleep 3
type startup_log.txt
```

**Expected output in `startup_log.txt`:**
```
1. Starting
2. Importing cv2
   Done
3. Importing YOLO
   Done
4. Loading model
   Done (0.0s)
5. Testing inference
   Success: 1 detections
DONE
```

✅ **If you see this**: YOLO works, continue to Test 3

❌ **If you get an error**: Check error message, may need to reinstall ultralytics

---

## Test 3: Quick Stability Test (30 seconds)

Run the turret in headless mode:

```bash
python src/main_headless.py
```

**What you should see:**
```
✅ YOLO model loaded
✅ Serial controller initialized
✅ Tracker initialized
✅ Camera opened
✅ Turret running in HEADLESS mode — press Ctrl+C to quit

[     10] Targets: 0 | Neutralized: 0 | dx=-45.0° dy=+0.0° fire=0
[     20] Targets: 0 | Neutralized: 0 | dx=-30.0° dy=+0.0° fire=0
[     30] Targets: 0 | Neutralized: 0 | dx=-15.0° dy=+0.0° fire=0
```

**Status updates every 5 seconds**

⏱️ Let it run for **30 seconds** minimum

✅ **If it runs without crashing**: Fix works! Continue to Test 4

❌ **If it crashes**: Note the error message, check `CRASH_FIX_SUMMARY.md`

---

## Test 4: Verify Serial Communication (2 minutes)

Open **TWO terminals**:

**Terminal 1:**
```bash
python src/main.py
```

**Terminal 2:**
```bash
python monitor_serial.py
```

**Expected output in Terminal 2:**
```
==================================================
SERIAL PORT MONITOR
==================================================
Port: COM6
Baud Rate: 115200
Timeout: 5.0s

✅ Connected to COM6

[  1]    | aim | dx= -90° dy=  +0° | fire=0
[  2]    | aim | dx= -85° dy=  +0° | fire=0
[  3]    | aim | dx= -80° dy=  +0° | fire=0
...
```

✅ **If you see messages**: Serial communication working! 

❌ **If you see no messages**: Check COM6 port, verify Arduino is connected

---

## Test 5: Test With Person in View (5 minutes)

Run Test 4 again, but **walk in front of the camera**.

**Expected behavior:**
- Status line shows `Targets: 1` when you appear
- `dx` and `dy` values change to track you
- When you're centered, you should see `fire=1` (would fire if servos installed)
- When you leave, it goes back to surveillance mode (sweeping)

**Example output:**
```
[    100] Targets: 1 | Neutralized: 0 | dx= +12.5° dy= -3.2° fire=0
[    105] Targets: 1 | Neutralized: 0 | dx=  +8.0° dy= -2.1° fire=0
[    110] Targets: 1 | Neutralized: 0 | dx=  +0.5° dy= -0.5° fire=1  ← WOULD FIRE!
[    115] Targets: 0 | Neutralized: 1 | dx= -45.0° dy= +0.0° fire=0  ← Back to sweep
```

✅ **If this works**: Targeting logic is perfect!

❌ **If targeting doesn't work**: Check YOLO model, check `serial_debug.log`

---

## Test 6: Extended Stability Test (10+ minutes)

Run this without any intervention:

```bash
python src/main.py
```

Let it run for **at least 10 minutes**.

**What to watch for:**
- ✅ No crashes
- ✅ Consistent messages (if you look at `monitor_serial.py`)
- ✅ Smooth operation
- ✅ Memory usage stays low

**Press Ctrl+C to stop**

---

## Test 7: Debug Mode (If Something Goes Wrong)

If you want to see detailed logs:

```bash
python debug_turret_v2.py > debug_output.txt 2>&1
```

Wait 30 seconds, then:
```bash
type debug_output.txt
```

This will show all messages being sent and any errors.

---

## Test Results Template

Copy and fill this in:

```
Date: [TODAY]
Duration Tested: [TIME]
Crashes: YES / NO
Camera: WORKS / BROKEN
YOLO: WORKS / BROKEN
Serial: WORKS / BROKEN
Targeting: WORKS / BROKEN

Notes:
[Your observations here]
```

---

## Common Issues & Solutions

### Issue: "❌ Cannot open camera"
**Solution**: 
- Check Device Manager for camera
- Try disconnecting/reconnecting camera
- Restart Python

### Issue: "❌ Failed to load YOLO model"
**Solution**:
```bash
pip install --upgrade ultralytics
```

### Issue: "ModuleNotFoundError: No module named 'pyserial'"
**Solution**:
```bash
pip install pyserial
```

### Issue: "No serial messages in monitor_serial.py"
**Solution**:
- Verify Arduino is on COM6: `python test_arduino.py`
- Check Arduino is plugged in
- Try different COM port (change in main.py line 275)

### Issue: Still crashes after 5+ minutes
**Solution**:
- Use `src/main_stable.py` instead (has logging)
- Check error in console output
- Post error to GitHub Issues

---

## Performance Benchmarks

After running Test 6 (10 minutes), you should see:

| Metric | Good | Excellent |
|--------|------|-----------|
| Frame Rate | 20-30 FPS | 25-30 FPS |
| CPU Usage | <50% | <40% |
| Memory | Stable | Decreasing (gc collection) |
| Crashes | 0 | 0 |

---

## Next Steps After Passing All Tests

1. ✅ **If all tests pass**:
   - Connect servos to Arduino
   - Update Arduino firmware if needed
   - Test actual turret movement
   
2. ✅ **If some tests fail**:
   - Note which test failed
   - Check the error message carefully
   - Consult CRASH_FIX_SUMMARY.md
   
3. ✅ **If everything is stable**:
   - You can now start the turret with:
     ```bash
     python src/main.py
     ```
   - Leave it running for hours safely

---

## Success Criteria

Your crash fix is **successful** when:

- [x] No crashes after 10+ minutes
- [x] Camera continuously captures frames
- [x] Serial messages send at 20 Hz
- [x] Targets are detected and tracked
- [x] Auto-fire works (message shows fire=1)
- [x] Surveillance sweep works
- [x] No memory leaks (memory stays stable)

