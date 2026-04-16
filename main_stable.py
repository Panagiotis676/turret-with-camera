#!/usr/bin/env python
"""
Turret Main with Logging - Most Stable Version
"""
import time
import math
import cv2
import gc
import logging
import sys

# Setup logging FIRST before importing YOLO
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('turret.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

logger.info("Starting Turret...")

try:
    from ultralytics import YOLO
    logger.info("✅ YOLO imported")
except Exception as e:
    logger.error(f"❌ Failed to import YOLO: {e}")
    sys.exit(1)

try:
    from src.serial_comm import SerialController
    logger.info("✅ SerialController imported")
except Exception as e:
    logger.error(f"❌ Failed to import SerialController: {e}")
    sys.exit(1)

try:
    from centroid_tracker import CentroidTracker
    logger.info("✅ CentroidTracker imported")
except Exception as e:
    logger.error(f"❌ Failed to import CentroidTracker: {e}")
    sys.exit(1)

CENTER_TOLERANCE = 20
FIRE_COOLDOWN = 2.0
CLEAR_INTERVAL = 1000.0
SURVEILLANCE_SPEED = 15
DEG_PER_PIXEL = 0.08
SERIAL_RATE_HZ = 20
SERIAL_INTERVAL = 1.0 / SERIAL_RATE_HZ


def run(camera_index=0, serial_port=None, model_path="yolov8n.pt"):
    """Main turret run loop with logging"""

    logger.info(f"Initializing with camera={camera_index}, port={serial_port}, model={model_path}")

    try:
        logger.info("Loading YOLO model...")
        model = YOLO(model_path)
        logger.info("✅ YOLO model loaded")
    except Exception as e:
        logger.error(f"❌ Failed to load YOLO: {e}")
        return

    try:
        logger.info("Initializing serial...")
        ser = SerialController(serial_port)
        logger.info("✅ Serial initialized")
    except Exception as e:
        logger.error(f"❌ Failed to init serial: {e}")
        return

    try:
        logger.info("Initializing tracker...")
        tracker = CentroidTracker(max_disappeared=30, max_distance=120)
        logger.info("✅ Tracker initialized")
    except Exception as e:
        logger.error(f"❌ Failed to init tracker: {e}")
        return

    neutralized = {}
    last_fire = 0
    last_clear = time.time()
    last_serial_send = time.time()

    surveillance_angle = 0.0
    surveillance_direction = 1
    last_surveillance_update = time.time()
    surveillance_range = 90

    try:
        logger.info("Opening camera...")
        cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            logger.error("❌ Cannot open camera")
            return
        logger.info("✅ Camera opened")
    except Exception as e:
        logger.error(f"❌ Failed to open camera: {e}")
        return

    logger.info("✅ Turret running")

    frame_count = 0
    error_count = 0

    while True:
        try:
            # Periodic garbage collection
            if frame_count % 300 == 0:
                gc.collect()

            ret, frame = cap.read()
            if not ret:
                logger.error("Failed to read frame")
                break

            if frame is None or frame.size == 0:
                logger.warning("Empty frame")
                continue

            frame_count += 1
            error_count = 0

            h, w = frame.shape[:2]
            cx, cy = w // 2, h // 2

            # YOLO detection
            try:
                results = model(frame, verbose=False)
                boxes = results[0].boxes
            except Exception as e:
                logger.warning(f"YOLO failed: {e}")
                boxes = None

            # Extract detections
            detections = []
            if boxes is not None:
                try:
                    for box, cls in zip(boxes.xyxy, boxes.cls):
                        if int(cls) == 0:
                            x1, y1, x2, y2 = [int(v) for v in box]
                            detections.append((x1, y1, x2, y2))
                except Exception as e:
                    logger.warning(f"Detection error: {e}")

            # Update tracker
            try:
                tracked = tracker.update(detections)
            except Exception as e:
                logger.warning(f"Tracker error: {e}")
                tracked = {}

            # Clear neutralized targets
            now = time.time()
            if now - last_clear > CLEAR_INTERVAL:
                neutralized = {oid: ts for oid, ts in neutralized.items() if now - ts < CLEAR_INTERVAL}
                last_clear = now

            # Find best target
            candidates = []
            for oid, (x1, y1, x2, y2, cx_obj, cy_obj) in tracked.items():
                if oid in neutralized:
                    continue
                area = (x2 - x1) * (y2 - y1)
                dx = cx_obj - cx
                dy = cy_obj - cy
                distance = math.hypot(dx, dy)
                score = area - (distance * 50)
                candidates.append((score, oid, x1, y1, x2, y2, cx_obj, cy_obj, dx, dy))

            candidates.sort(reverse=True, key=lambda x: x[0])
            target = candidates[0] if candidates else None

            send_fire = False
            dx_deg = 0
            dy_deg = 0

            if target:
                score, oid, x1, y1, x2, y2, cx_obj, cy_obj, dx_px, dy_px = target
                distance = math.hypot(dx_px, dy_px)
                aligned = distance <= CENTER_TOLERANCE

                dx_deg = dx_px * DEG_PER_PIXEL
                dy_deg = dy_px * DEG_PER_PIXEL

                if aligned and (now - last_fire) > FIRE_COOLDOWN:
                    send_fire = True
                    last_fire = now
                    neutralized[oid] = now
                    logger.info(f"🎯 FIRE at target {oid}")

                surveillance_angle = 0.0
                surveillance_direction = 1
                last_surveillance_update = time.time()
            else:
                time.sleep(0.01)
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

            # Send serial
            current_time = time.time()
            if current_time - last_serial_send >= SERIAL_INTERVAL:
                try:
                    ser.send_aim(int(round(dx_deg)), int(round(dy_deg)), send_fire)
                    last_serial_send = current_time
                except Exception as e:
                    logger.warning(f"Serial error: {e}")

            if frame_count % 100 == 0:
                logger.info(f"Frame {frame_count}: targets={len(tracked)}, neutralized={len(neutralized)}")

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            break
        except Exception as e:
            error_count += 1
            logger.error(f"Error #{error_count}: {e}")
            if error_count >= 10:
                logger.error("Too many errors, exiting")
                break
            time.sleep(0.1)

    # Cleanup
    logger.info("Shutting down...")
    try:
        ser.close()
        cap.release()
    except:
        pass

    logger.info(f"Done. Processed {frame_count} frames")


if __name__ == "__main__":
    run(camera_index=0, serial_port='COM6')

