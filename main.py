import time
import math
import cv2
from ultralytics import YOLO
from src.serial_comm import SerialController
from centroid_tracker import CentroidTracker

CENTER_TOLERANCE = 20  # pixels
FIRE_COOLDOWN = 2.0    # seconds
CLEAR_INTERVAL = 10.0  # seconds
SURVEILLANCE_SPEED = 15  # degrees/second for surveillance sweep


def run(camera_index=0, serial_port=None, model_path="yolov8n.pt"):
    model = YOLO(model_path)
    ser = SerialController(serial_port)
    tracker = CentroidTracker(max_disappeared=30, max_distance=120)

    neutralized = {}    # id -> timestamp
    last_fire = 0
    last_clear = time.time()

    # Surveillance mode variables
    surveillance_pos = 0  # Current servo position (-90 to 90 degrees)
    surveillance_direction = 1  # 1 for right, -1 for left
    last_surveillance_update = time.time()
    surveillance_range = 90  # Sweep ±90 degrees

    cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print("❌ Cannot open camera")
        return

    print("✅ Webcam started — press Q to quit")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        h, w = frame.shape[:2]
        cx, cy = w // 2, h // 2

        # Run YOLO detection
        results = model(frame, verbose=False)
        boxes = results[0].boxes

        # Extract person detections (class 0)
        detections = []
        if boxes is not None:
            for box, cls in zip(boxes.xyxy, boxes.cls):
                if int(cls) == 0:
                    x1, y1, x2, y2 = [int(v) for v in box]
                    detections.append((x1, y1, x2, y2))

        # Update tracker with detections
        tracked = tracker.update(detections)

        # Periodic clear of neutralized targets
        now = time.time()
        if now - last_clear > CLEAR_INTERVAL:
            neutralized = {oid: ts for oid, ts in neutralized.items() if now - ts < CLEAR_INTERVAL}
            last_clear = now

        # Prioritize targets: prefer largest and near center
        candidates = []
        for oid, (x1, y1, x2, y2, cx_obj, cy_obj) in tracked.items():
            # Skip if recently neutralized
            if oid in neutralized:
                cv2.rectangle(frame, (x1, y1), (x2, y2), (120, 120, 120), 2)
                cv2.putText(frame, f"NEUTR {oid}", (x1, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (120, 120, 120), 2)
                continue

            area = (x2 - x1) * (y2 - y1)
            dx = cx_obj - cx
            dy = cy_obj - cy
            distance = math.hypot(dx, dy)

            # Score: prefer large targets near center
            score = area - (distance * 50)
            candidates.append((score, oid, x1, y1, x2, y2, cx_obj, cy_obj, dx, dy))

        candidates.sort(reverse=True, key=lambda x: x[0])
        target = candidates[0] if candidates else None

        # Draw frame center
        cv2.circle(frame, (cx, cy), 5, (255, 0, 0), -1)

        send_fire = False
        dx = 0
        dy = 0

        if target:
            # TARGET ACQUISITION MODE
            score, oid, x1, y1, x2, y2, cx_obj, cy_obj, dx, dy = target
            distance = math.hypot(dx, dy)
            aligned = distance <= CENTER_TOLERANCE

            # Draw target
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.circle(frame, (cx_obj, cy_obj), 4, (0, 255, 0), -1)
            cv2.line(frame, (cx, cy), (cx_obj, cy_obj), (255, 0, 0), 1)
            cv2.putText(frame, f"ID:{oid} | dx={int(dx)} dy={int(dy)}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (0, 255, 0), 2)
            cv2.putText(frame, "MODE: TARGETING", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                        (0, 255, 0), 2)

            # Fire when aligned
            if aligned and (now - last_fire) > FIRE_COOLDOWN:
                send_fire = True
                last_fire = now
                neutralized[oid] = now

            # Reset surveillance on target acquisition
            surveillance_pos = 0
            surveillance_direction = 1
        else:
            # SURVEILLANCE MODE - slowly sweep when no targets
            cv2.putText(frame, "MODE: SURVEILLANCE", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                        (0, 165, 255), 2)

            # Update surveillance position at constant speed
            time_delta = time.time() - last_surveillance_update
            if time_delta > 0:
                # Convert speed (degrees/second) to pixel offset
                # Using scale from Arduino: 1 pixel = 0.08 degrees
                # So: degrees/second / 0.08 = pixels/second
                pixels_per_second = SURVEILLANCE_SPEED / 0.08
                movement = pixels_per_second * time_delta * surveillance_direction

                surveillance_pos += movement

                # Bounce at limits
                if surveillance_pos >= surveillance_range:
                    surveillance_pos = surveillance_range
                    surveillance_direction = -1
                elif surveillance_pos <= -surveillance_range:
                    surveillance_pos = -surveillance_range
                    surveillance_direction = 1

                last_surveillance_update = time.time()

            # Convert surveillance position to dx offset for servo
            dx = int(surveillance_pos)
            dy = 0

            cv2.putText(frame, f"Sweep: {int(surveillance_pos):+d}°", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (0, 165, 255), 2)

        ser.send_aim(int(dx), int(dy), send_fire)

        cv2.imshow('turret', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break


    ser.close()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    # set `serial_port` to your Arduino COM port like 'COM3' on Windows
    run(camera_index=0, serial_port=None)
