# python - Turret Main Program (GUI + Async YOLO Stable Version)
import time
import math
import cv2
import gc
import sys
import os
import threading
import queue
import platform
from ultralytics import YOLO

# Add parent directory to path so we can import from root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from serial_comm import SerialController
from centroid_tracker import CentroidTracker

# Configuration
CENTER_TOLERANCE = 20
FIRE_COOLDOWN = 2.0
CLEAR_INTERVAL = 1000.0
SURVEILLANCE_SPEED = 15
DEG_PER_PIXEL = 0.08
SERIAL_RATE_HZ = 20
SERIAL_INTERVAL = 1.0 / SERIAL_RATE_HZ
STATUS_LOG_INTERVAL = 5.0

# Optimization settings
FRAME_SCALE_WIDTH = 640         # Downscale frames to this width for YOLO
YOLO_CONFIDENCE = 0.5           # Filter low-confidence detections
TRACKER_MAX_DISAPPEARED = 10    # Reduce tracker memory pressure
YOLO_INTERVAL = 1.0             # YOLO cadence in seconds

# Detect if running on Raspberry Pi
IS_RASPBERRY_PI = 'arm' in platform.machine().lower()
ENABLE_GUI = not IS_RASPBERRY_PI  # Disable GUI on Pi


def run(camera_index=0, serial_port=None, model_path="yolov8n.pt", headless=None):
    """Main turret control loop with optional GUI and async YOLO worker."""
    
    # Override headless mode if explicitly set
    headless_mode = headless if headless is not None else IS_RASPBERRY_PI

    # Resolve model path relative to project root when needed.
    if not os.path.isabs(model_path):
        candidate_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), model_path)
        if os.path.exists(candidate_root):
            model_path = candidate_root

    # Initialize components
    try:
        model = YOLO(model_path)
        print("✅ YOLO model loaded")
    except Exception as e:
        print(f"❌ Failed to load YOLO model: {e}")
        return

    try:
        ser = SerialController(serial_port)
        print("✅ Serial initialized")
    except Exception as e:
        print(f"❌ Failed to initialize serial: {e}")
        return

    try:
        tracker = CentroidTracker(max_disappeared=TRACKER_MAX_DISAPPEARED, max_distance=120)
        print("✅ Tracker initialized")
    except Exception as e:
        print(f"❌ Failed to initialize tracker: {e}")
        return

    # State variables
    neutralized = {}
    last_fire = 0.0
    last_clear = time.time()
    last_serial_send = time.time()
    last_status_log = time.time()

    surveillance_angle = 0.0
    surveillance_direction = 1
    last_surveillance_update = time.time()
    surveillance_range = 90

    # Async YOLO shared state
    yolo_input_queue = queue.Queue(maxsize=1)
    yolo_output_queue = queue.Queue(maxsize=1)
    yolo_stop_event = threading.Event()
    latest_detections = []  # cached person detections in original frame coords
    latest_detection_ts = 0.0

    def yolo_worker():
        """Background YOLO worker: receives scaled frames and returns person detections."""
        while not yolo_stop_event.is_set():
            try:
                item = yolo_input_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if item is None:
                break

            scaled_frame, scale_ratio, ts = item
            person_dets = []
            try:
                results = model(scaled_frame, verbose=False, conf=YOLO_CONFIDENCE)
                boxes = results[0].boxes
                if boxes is not None:
                    for box, cls in zip(boxes.xyxy, boxes.cls):
                        if int(cls) == 0:
                            x1, y1, x2, y2 = [int(v / scale_ratio) for v in box.tolist()]
                            person_dets.append((x1, y1, x2, y2))
            except Exception as e:
                # Keep worker alive; surface error via empty detections.
                print(f"❌ YOLO failed: {type(e).__name__}: {e}")

            # Keep only newest result.
            try:
                while True:
                    yolo_output_queue.get_nowait()
            except queue.Empty:
                pass
            yolo_output_queue.put((ts, person_dets))

    # Open camera
    try:
        # On Raspberry Pi, use camera index 0 (should be the Pi camera module)
        # On Windows/laptop, use CAP_DSHOW if available
        if IS_RASPBERRY_PI:
            cap = cv2.VideoCapture(camera_index)
            print(f"✅ Pi camera opened (index {camera_index})")
        else:
            cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap = cv2.VideoCapture(camera_index)
            print(f"✅ Laptop camera opened (index {camera_index})")
        
        if not cap.isOpened():
            print("❌ Cannot open camera")
            return

        # Reduce camera lag accumulation where backend supports it.
        try:
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass
        try:
            cap.set(cv2.CAP_PROP_FPS, 30)
        except Exception:
            pass
    except Exception as e:
        print(f"❌ Failed to open camera: {e}")
        return

    if headless_mode:
        print("✅ Turret started - HEADLESS mode (no GUI)")
    else:
        print("✅ Turret started - GUI mode enabled")

    worker_thread = threading.Thread(target=yolo_worker, daemon=True)
    worker_thread.start()

    frame_count = 0
    error_count = 0
    max_consecutive_errors = 5
    last_yolo_submit = 0.0
    manual_fire_requested = False

    # Main loop
    while True:
        try:
            # Periodic memory cleanup
            if frame_count % 300 == 0:
                gc.collect()

            # Read frame
            ret, frame = cap.read()
            if not ret:
                print("❌ Failed to read frame")
                break
            if frame is None or frame.size == 0:
                continue

            frame_count += 1
            error_count = 0

            h, w = frame.shape[:2]
            cx, cy = w // 2, h // 2
            now = time.time()

            # Submit frame to YOLO worker at fixed cadence (non-blocking).
            if now - last_yolo_submit >= YOLO_INTERVAL:
                try:
                    scale_ratio = FRAME_SCALE_WIDTH / w
                    scaled_frame = cv2.resize(frame, (FRAME_SCALE_WIDTH, int(h * scale_ratio)))
                    payload = (scaled_frame, scale_ratio, now)

                    # Replace queued stale input with newest frame.
                    try:
                        while True:
                            yolo_input_queue.get_nowait()
                    except queue.Empty:
                        pass
                    yolo_input_queue.put_nowait(payload)
                    last_yolo_submit = now
                except queue.Full:
                    pass
                except Exception as e:
                    print(f"⚠️ YOLO submit error: {type(e).__name__}: {e}")

            # Consume newest YOLO result (if available) and cache it.
            try:
                while True:
                    ts, dets = yolo_output_queue.get_nowait()
                    latest_detection_ts = ts
                    latest_detections = dets
            except queue.Empty:
                pass

            detections = latest_detections

            # Update tracker with cached/latest detections.
            try:
                tracked = tracker.update(detections)
            except Exception as e:
                print(f"❌ Tracker error: {e}")
                tracked = {}

            # Clear old neutralized targets
            try:
                if now - last_clear > CLEAR_INTERVAL:
                    neutralized = {oid: ts for oid, ts in neutralized.items() if now - ts < CLEAR_INTERVAL}
                    last_clear = now
            except Exception as e:
                print(f"⚠️ Clear error: {e}")

            # Find best target
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
                print(f"⚠️ Candidate error: {e}")

            candidates.sort(reverse=True, key=lambda x: x[0])
            target = candidates[0] if candidates else None

            # Calculate aim angles
            send_fire = False
            dx_deg = 0.0
            dy_deg = 0.0

            if target:
                try:
                    score, oid, x1, y1, x2, y2, cx_obj, cy_obj, dx_px, dy_px = target
                    distance = math.hypot(dx_px, dy_px)
                    aligned = distance <= CENTER_TOLERANCE

                    dx_deg = dx_px * DEG_PER_PIXEL
                    dy_deg = dy_px * DEG_PER_PIXEL

                    surveillance_angle = 0.0
                    surveillance_direction = 1
                    last_surveillance_update = time.time()

                    if (aligned or manual_fire_requested) and (now - last_fire) > FIRE_COOLDOWN:
                        send_fire = True
                        last_fire = now
                        neutralized[oid] = now
                        if manual_fire_requested and not aligned:
                            print(f"🎯 MANUAL FIRE at target ID:{oid}")
                        else:
                            print(f"🎯 AUTO-FIRE at target ID:{oid}")
                        manual_fire_requested = False
                except Exception as e:
                    print(f"⚠️ Target error: {e}")
            else:
                try:
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
                    print(f"⚠️ Surveillance error: {e}")

            # Display camera window with detections (only if not headless)
            if not headless_mode:
                try:
                    cv2.circle(frame, (cx, cy), 5, (255, 0, 0), -1)
                    if target:
                        _, _, _, _, _, _, cx_obj, cy_obj, _, _ = target
                        cv2.circle(frame, (cx_obj, cy_obj), 5, (0, 255, 0), -1)
                    # Draw all tracked objects lightly
                    for oid, (x1, y1, x2, y2, cx_obj, cy_obj) in tracked.items():
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (120, 120, 120), 1)
                        cv2.putText(frame, f"T:{oid}", (x1, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 160, 160), 1)

                    # Highlight selected target
                    if target:
                        score, oid, x1, y1, x2, y2, cx_obj, cy_obj, dx_px, dy_px = target
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.putText(frame, f"ID:{oid}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                    # Lightweight status overlay
                    cv2.putText(
                        frame,
                        f"Tracked:{len(tracked)} CachedDet:{len(latest_detections)}",
                        (10, 24),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 255),
                        2,
                    )

                    cv2.imshow("Turret Camera", frame)
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord("f"):
                        manual_fire_requested = True
                    if key == ord("q"):
                        break
                except Exception:
                    pass

            # Send serial command
            try:
                current_time = time.time()
                if current_time - last_serial_send >= SERIAL_INTERVAL:
                    ser.send_aim(int(round(dx_deg)), int(round(dy_deg)), send_fire)
                    last_serial_send = current_time
            except Exception as e:
                print(f"❌ Serial error: {e}")

            # Log status every 5 seconds
            if now - last_status_log >= STATUS_LOG_INTERVAL:
                fire_status = "1" if send_fire else "0"
                age_ms = int((now - latest_detection_ts) * 1000) if latest_detection_ts > 0 else -1
                print(
                    f"[status] targets={len(tracked)} cached_det={len(latest_detections)} "
                    f"det_age_ms={age_ms} fire={fire_status} "
                    f"aim=({int(round(dx_deg))},{int(round(dy_deg))}) frame={frame_count}"
                )
                last_status_log = now

        except KeyboardInterrupt:
            print("\n🛑 Interrupted by user")
            break
        except Exception as e:
            error_count += 1
            print(f"❌ Error (#{error_count}): {e}")
            if error_count >= max_consecutive_errors:
                print("❌ Too many errors, exiting")
                break
            time.sleep(0.1)
            continue

    # Cleanup
    try:
        yolo_stop_event.set()
        try:
            yolo_input_queue.put_nowait(None)
        except Exception:
            pass
        worker_thread.join(timeout=1.0)
    except Exception:
        pass

    try:
        ser.close()
        cap.release()
        if not headless_mode:
            cv2.destroyAllWindows()
    except Exception:
        pass

    print("✅ Turret shutdown complete")


if __name__ == "__main__":
    # Detect environment and set defaults
    headless = IS_RASPBERRY_PI
    serial_port = os.getenv("TURRET_PORT", "auto")
    
    # Use TURRET_COM_PORT=COMx to force a specific port on Windows
    if "TURRET_COM_PORT" in os.environ:
        serial_port = os.getenv("TURRET_COM_PORT")
    
    # Use TURRET_HEADLESS=0 to force GUI mode even on Pi
    if "TURRET_HEADLESS" in os.environ:
        headless = int(os.getenv("TURRET_HEADLESS")) != 0
    
    print(f"System: {'Raspberry Pi' if IS_RASPBERRY_PI else 'Windows/Laptop'}")
    print(f"Headless mode: {headless}")
    print(f"Serial port: {serial_port}")
    print()
    
    run(camera_index=0, serial_port=serial_port, model_path="yolov8n.pt", headless=headless)
