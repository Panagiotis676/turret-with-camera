# python
from ultralytics import YOLO
import cv2
import pyttsx3
import time
import math
import threading

from centroid_tracker import CentroidTracker

# =============================
# Text-to-speech (non-blocking)
# =============================
engine = pyttsx3.init()
engine.setProperty("rate", 150)

def speak_async(text):
    def _speak(t):
        try:
            engine.say(t)
            engine.runAndWait()
        except Exception:
            pass
    threading.Thread(target=_speak, args=(text,), daemon=True).start()

# =============================
# YOLO model
# =============================
model = YOLO("yolov8n.pt")

# =============================
# Global state
# =============================
tracker = CentroidTracker(max_disappeared=30, max_distance=120)
neutralized = {}      # id -> timestamp neutralized

last_fire_time = 0
last_detect_time = 0

CENTER_TOLERANCE = 10        # pixels
SPEECH_COOLDOWN = 3          # seconds
FIRE_COOLDOWN = 2            # seconds

CLEAR_INTERVAL = 10  # seconds
last_clear_time = time.time()

# =============================
# Main loop
# =============================
def run_webcam(camera_index=0):
    global last_fire_time, last_detect_time, last_clear_time, neutralized

    cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(camera_index)

    if not cap.isOpened():
        print("❌ Cannot open webcam")
        return

    print("✅ Webcam started — press Q to quit")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        h, w, _ = frame.shape
        frame_cx, frame_cy = w // 2, h // 2
        frame_out = frame.copy()

        # Run YOLO
        results = model(frame, verbose=False)
        boxes = results[0].boxes

        detections = []
        if boxes is not None:
            for box, cls in zip(boxes.xyxy, boxes.cls):
                if int(cls) == 0:
                    x1, y1, x2, y2 = map(int, box)
                    detections.append((x1, y1, x2, y2))

        tracked = tracker.update(detections)

        key = cv2.waitKey(1) & 0xFF
        now = time.time()

        # periodic clear of neutralized memory (keep recent only)
        if now - last_clear_time > CLEAR_INTERVAL:
            neutralized = {oid: ts for oid, ts in neutralized.items() if now - ts < CLEAR_INTERVAL}
            last_clear_time = now

        # Build prioritization: prefer largest and near center
        candidates = []
        for oid, (x1, y1, x2, y2, cx, cy) in tracked.items():
            area = (x2 - x1) * (y2 - y1)
            # skip if recently neutralized
            if oid in neutralized:
                color = (120, 120, 120)
                cv2.rectangle(frame_out, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame_out, f"NEUTR {oid}", (x1, y1 - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                continue
            dx, dy = cx - frame_cx, cy - frame_cy
            distance = math.hypot(dx, dy)
            # simple score: prefer large and near center
            score = area - (distance * 50)
            candidates.append((score, oid, x1, y1, x2, y2, cx, cy))

        candidates.sort(reverse=True, key=lambda x: x[0])
        target = candidates[0] if candidates else None

        # draw frame center
        cv2.circle(frame_out, (frame_cx, frame_cy), 6, (255, 0, 0), -1)

        if target:
            score, oid, x1, y1, x2, y2, cx, cy = target
            offset_x = cx - frame_cx
            offset_y = cy - frame_cy
            distance = math.hypot(offset_x, offset_y)
            centered = distance < CENTER_TOLERANCE

            # Draw target
            cv2.rectangle(frame_out, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame_out, f"ID:{oid}", (x1, y1 - 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)
            cv2.circle(frame_out, (cx, cy), 4, (0,0,255), -1)

            # non-blocking detection speech
            if now - last_detect_time > SPEECH_COOLDOWN:
                speak_async("target detected")
                last_detect_time = now

            fire_pressed = key == ord('f')
            if (centered or fire_pressed) and now - last_fire_time > FIRE_COOLDOWN:
                speak_async("fire")
                neutralized[oid] = now
                last_fire_time = now

        # UI and display
        cv2.putText(frame_out, "AUTO: CENTER | MANUAL: F", (10, h - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,0), 2)
        cv2.imshow("YOLO Turret Vision", frame_out)

        if key == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("🛑 Webcam closed")

if __name__ == "__main__":
    run_webcam(0)
