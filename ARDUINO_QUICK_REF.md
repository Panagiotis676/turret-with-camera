# 🎯 Arduino Testing - Quick Reference Card

**Print this or keep it open while testing!**

---

## 📋 Testing Order

```
1. Find COM Port          → python test_arduino.py --find-ports
2. Upload Arduino Code    → Use Arduino IDE
3. Test Communication     → python test_arduino.py
4. Wire Servos           → Follow ARDUINO_TESTING.md
5. Test with Servos      → python test_arduino.py
6. Full System Test      → python -m src.main
```

---

## 🔌 Quick Wiring

```
Servo 1 (Pan/X):         Servo 2 (Tilt/Y):
├─ Signal → Pin 9       ├─ Signal → Pin 10
├─ VCC → 5V             ├─ VCC → 5V
└─ GND → GND            └─ GND → GND
```

**Colors**: 🟠 Signal | 🔴 Power | 🟤 Ground

---

## 💻 Test Commands (Arduino Serial Monitor)

```
aim,0,0,0      → Center position
aim,45,0,0     → Pan right 45°
aim,-45,0,0    → Pan left 45°
aim,0,30,0     → Tilt up 30°
aim,0,-30,0    → Tilt down 30°
aim,0,0,1      → Fire command
```

Baud Rate: **115200**

---

## 🐛 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| Port not found | Check Device Manager, close Arduino IDE |
| Permission denied | Close other programs, replug USB |
| Servos don't move | Check wiring, verify upload |
| Servos jitter | Need external power supply |
| Python can't connect | Set correct COM port in code |

---

## 📝 Update These Files

1. **test_arduino.py** line 13:
   ```python
   ARDUINO_PORT = 'COM3'  # ← YOUR PORT
   ```

2. **src/main.py** line 176:
   ```python
   run(camera_index=0, serial_port='COM3')  # ← YOUR PORT
   ```

---

## ✅ Success Checklist

- [ ] COM port identified: COM____
- [ ] Arduino sketch uploaded
- [ ] Serial test passes
- [ ] Servos wired correctly
- [ ] Servos move smoothly
- [ ] Full system runs
- [ ] Camera tracks targets
- [ ] Servos follow camera
- [ ] Manual fire works (F key)

---

## 📚 Full Docs

- **ARDUINO_TESTING.md** - Complete testing guide
- **TODO.md** - Task list
- **README.md** - Project overview

---

**Need help?** See ARDUINO_TESTING.md for detailed instructions!

