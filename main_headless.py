# python
"""
Turret Main - Headless Version (No GUI)
Better for testing and server environments
"""
import time
import math
import cv2
import gc
from ultralytics import YOLO
from src.serial_comm import SerialController
from centroid_tracker import CentroidTracker

CENTER_TOLERANCE = 20
FIRE_COOLDOWN = 2.0
CLEAR_INTERVAL = 1000.0
SURVEILLANCE_SPEED = 15
DEG_PER_PIXEL = 0.08

# Rate limiting to prevent serial buffer overflow
SERIAL_RATE_HZ = 20
SERIAL_INTERVAL = 1.0 / SERIAL_RATE_HZ  # ~50ms between messages


def run_headless(camera_index=0, serial_port=None, model_path="yolov8n.pt", runtime_seconds=None):
    """Run turret without GUI display - better for stability"""

    try:
        model = YOLO(model_path)
        print("✅ YOLO model loaded")
    except Exception as e:
        print(f"❌ Failed to load YOLO model: {e}")
        return

    try:
        ser = SerialController(serial_port)
        print("✅ Serial controller initialized")
    except Exception as e:
        print(f"❌ Failed to initialize serial: {e}")
        return

    try:
        tracker = CentroidTracker(max_disappeared=30, max_distance=120)
        print("✅ Tracker initialized")
    except Exception as e:
        print(f"❌ Failed to initialize tracker: {e}")
        return

    neutralized = {}
    last_fire = 0
    last_clear = time.time()
    last_serial_send = time.time()
    last_status_print = time.time()

    # Surveillance mode variables
    surveillance_angle = 0.0
    surveillance_direction = 1
    last_surveillance_update = time.time()
    surveillance_range = 90

    try:
        cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            print("❌ Cannot open camera")
            return
        print("✅ Camera opened")
    except Exception as e:
        print(f"❌ Failed to open camera: {e}")
        return

    print("✅ Turret running in HEADLESS mode — press Ctrl+C to quit\n")

    frame_count = 0
    error_count = 0
    max_consecutive_errors = 5
    start_time = time.time()

    while True:
        try:
            # Check runtime limit
            if runtime_seconds and (time.time() - start_time) > runtime_seconds:
                print(f"\n✅ Runtime limit ({runtime_seconds}s) reached")
                break

            # Periodic garbage collection
            if frame_count % 300 == 0:
                gc.collect()

            ret, frame = cap.read()
            if not ret:
                print("❌ Failed to read frame")
                break

            # Validate frame
            if frame is None or frame.size == 0:
                print("⚠️  Empty frame received")
                continue

            frame_count += 1
            error_count = 0

            h, w = frame.shape[:2]
            cx, cy = w // 2, h // 2

            # Run YOLO detection with error handling
            try:
                results = model(frame, verbose=False)
                boxes = results[0].boxes
            except Exception as e:
                print(f"⚠️  YOLO detection failed: {e}")
                boxes = None

            # Extract person detections (class 0)
            detections = []
            try:
                if boxes is not None:
                    for box, cls in zip(boxes.xyxy, boxes.cls):
                        if int(cls) == 0:
                            x1, y1, x2, y2 = [int(v) for v in box]
                            detections.append((x1, y1, x2, y2))
            except Exception as e:
                print(f"⚠️  Error processing detections: {e}")

            # Update tracker with detections
            try:
                tracked = tracker.update(detections)
            except Exception as e:
                print(f"⚠️  Tracker update failed: {e}")
                tracked = {}

            # Periodic clear of neutralized targets
            now = time.time()
            try:
                if now - last_clear > CLEAR_INTERVAL:
                    neutralized = {oid: ts for oid, ts in neutralized.items() if now - ts < CLEAR_INTERVAL}
                    last_clear = now
            except Exception as e:
                print(f"⚠️  Error clearing neutralized targets: {e}")

            # Prioritize targets: prefer largest and near center
            candidates = []
            try:
                for oid, (x1, y1, x2, y2, cx_obj, cy_obj) in tracked.items():
                    if oid in neutralized:
                        continue

                    area = (x2 - x1) * (y2 - y1)
                    dx = cx_obj - cx
                    dy = cy_obj - cy
                    distance = math.hypot(dx, dy)

                    score = area - (distance * 50)
                    candidates.append((score, oid, x1, y1, x2, y2, cx_obj, cy_obj, dx, dy))
            except Exception as e:
                print(f"⚠️  Error processing candidates: {e}")

            candidates.sort(reverse=True, key=lambda x: x[0])
            target = candidates[0] if candidates else None

            send_fire = False
            dx_deg = 0
            dy_deg = 0

            if target:
                try:
                    # TARGET ACQUISITION MODE
                    score, oid, x1, y1, x2, y2, cx_obj, cy_obj, dx_px, dy_px = target
                    distance = math.hypot(dx_px, dy_px)
                    aligned = distance <= CENTER_TOLERANCE

                    # convert pixel offsets to degrees for servos
                    dx_deg = dx_px * DEG_PER_PIXEL
                    dy_deg = dy_px * DEG_PER_PIXEL

                    # Reset surveillance on target acquisition
                    surveillance_angle = 0.0
                    surveillance_direction = 1
                    last_surveillance_update = time.time()
                except Exception as e:
                    print(f"⚠️  Error in target acquisition: {e}")
            else:
                try:
                    # SURVEILLANCE MODE
                    time.sleep(10 / 1000)

                    time_delta = time.time() - last_surveillance_update
                    if time_delta > 0:
                        surveillance_angle += SURVEILLANCE_SPEED * time_delta * surveillance_direction
                        if surveillance_angle >= surveillance_range:
                            surveillance_angle = surveillance_range
                            surveillance_direction = -1
                        elif surveillance_angle <= -surveillance_range:
                            surveillance_angle = -surveillance_range
                            surveillance_direction = 1
                        last_surveillance_update = time.time()

                    dx_deg = surveillance_angle
                    dy_deg = 0.0
                except Exception as e:
                    print(f"⚠️  Error in surveillance: {e}")

            # Fire logic (only if we have a target)
            if target:
                try:
                    score, oid, x1, y1, x2, y2, cx_obj, cy_obj, dx_px, dy_px = target
                    distance = math.hypot(dx_px, dy_px)
                    aligned = distance <= CENTER_TOLERANCE

                    # Fire when automatically aligned (no manual fire in headless mode)
                    if aligned and (now - last_fire) > FIRE_COOLDOWN:
                        send_fire = True
                        last_fire = now
                        neutralized[oid] = now
                        print(f"🎯 AUTO-FIRE at target ID:{oid}")
                except Exception as e:
                    print(f"⚠️  Error in fire logic: {e}")

            # Send aim in degrees with rate limiting
            try:
                current_time = time.time()
                if current_time - last_serial_send >= SERIAL_INTERVAL:
                    ser.send_aim(int(round(dx_deg)), int(round(dy_deg)), send_fire)
                    last_serial_send = current_time
            except Exception as e:
                print(f"⚠️  Error sending serial: {e}")

            # Periodic status report
            if now - last_status_print > 5.0:
                print(f"[{frame_count:6d}] Targets: {len(tracked)} | Neutralized: {len(neutralized)} | dx={dx_deg:+6.1f}° dy={dy_deg:+6.1f}° fire={int(send_fire)}")
                last_status_print = now

        except KeyboardInterrupt:
            print("\n\n🛑 User interrupted")
            break
        except Exception as e:
            error_count += 1
            print(f"❌ Error in main loop (#{error_count}): {e}")
            import traceback
            traceback.print_exc()

            if error_count >= max_consecutive_errors:
                print(f"❌ Too many errors, exiting...")
                break

            time.sleep(0.1)
            continue

    # Cleanup
    print("\nCleaning up...", end="")
    try:
        ser.close()
        cap.release()
    except:
        pass

    print(" ✅ Done")
    print(f"Total frames processed: {frame_count}")


if __name__ == "__main__":
    # set `serial_port` to your Arduino COM port like `COM3` on Windows
    # runtime_seconds: optional limit (e.g., 60 for 60 second test)
    run_headless(camera_index=0, serial_port='COM6', runtime_seconds=None)

