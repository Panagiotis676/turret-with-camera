# Turret Vision - Algorithm Improvements & Fixes

## 🔧 Issues Fixed

### 1. **PyCharm Import Error** ✅
**Problem**: `ModuleNotFoundError: No module named 'pkg_resources'`
**Solution**: Added `setuptools` to `requirements.txt` and reinstalled dependencies
**Status**: Fixed - YOLO imports successfully now

### 2. **Undefined Variables in main.py** ✅
**Problem**: Variables `dx`, `dy` referenced when `target` was `None`
**Solution**: Initialize `dx=0, dy=0` before the if-statement
**Status**: Fixed - Code now handles no-target scenario gracefully

---

## 🚀 Algorithm Improvements

### Old Algorithm (Simple Greedy)
- Picked the **largest person box** only
- No cross-frame tracking
- Lost target continuity when person moved slightly
- Could re-target same person multiple times

### New Algorithm (Centroid Tracker + Scoring) ✅
**Better because:**

1. **Persistent Tracking** - Assigns unique IDs to each person across frames
2. **Avoids Re-engagement** - Recently neutralized targets marked as "NEUTR" for 10 seconds
3. **Intelligent Prioritization** - Scores targets by:
   - **Area** (larger = closer)
   - **Distance penalty** (prefer targets near center)
   - Formula: `score = area - (distance * 50)`
4. **Graceful Handling** - Tracks persons who disappear for up to 30 frames

### Code Changes
- Imported `CentroidTracker` from `centroid_tracker.py`
- Replaced simple greedy selection with tracker
- Added scoring system for multi-target scenarios
- Better visual feedback (ID display, neutralized state)

---

## 📋 What to Do Next

1. **Test in PyCharm**: Run `python -m src.main` with your camera
2. **Update Serial Port**: Set `serial_port='COM3'` (or your Arduino port) in the main.py
3. **Verify Arduino Sketch**: Flash `hardware/arduino/servo_controller.ino`
4. **Fine-tune Parameters**:
   - `CENTER_TOLERANCE = 20` (pixels to trigger fire)
   - `FIRE_COOLDOWN = 2.0` (seconds between shots)
   - `max_distance=120` (CentroidTracker - max pixels to match detection)
   - `max_disappeared=30` (frames before forgetting a person)

---

## 📊 Algorithm Comparison Table

| Feature | Old (main.py) | New (main.py) |
|---------|-------|-------|
| Cross-frame Tracking | ❌ | ✅ |
| Target ID Persistence | ❌ | ✅ |
| Avoid Re-targeting | ❌ | ✅ |
| Multi-target Scoring | ❌ | ✅ |
| Center Preference | Simple | Weighted |
| Disappearance Handling | Instant forget | Graceful (30 frames) |


