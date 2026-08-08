cat > ~/turret/src/pi_server.py << 'EOF'
#!/usr/bin/env python3
"""
Raspberry Pi Server - Camera Stream + Command Listener
Uses Picamera2 for Pi camera module
"""
import socket
import struct
import pickle
import threading
import time
import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to import SerialController but don't fail if missing
try:
    from serial_comm import SerialController
    SERIAL_AVAILABLE = True
except Exception as e:
    print(f"⚠️  SerialController import failed: {e}")
    SERIAL_AVAILABLE = False

# Import Picamera2
try:
    from picamera2 import Picamera2
    PICAMERA2_AVAILABLE = True
except Exception as e:
    print(f"⚠️  Picamera2 not available: {e}")
    PICAMERA2_AVAILABLE = False

CAMERA_PORT = 5000
COMMAND_PORT = 5001
SERIAL_PORT = "/dev/ttyACM0"

print("=" * 60)
print("🔫 TURRET PI SERVER")
print("=" * 60)
print()

# Try Arduino (optional)
ser = None
if SERIAL_AVAILABLE:
    try:
        ser = SerialController(SERIAL_PORT)
        print(f"✅ Arduino initialized on {SERIAL_PORT}")
    except Exception as e:
        print(f"⚠️  Arduino not available: {e}")
else:
    print("⚠️  SerialController module not available")

# Open camera using Picamera2
print(f"Opening Raspberry Pi Camera Module...")
picam2 = None
try:
    if not PICAMERA2_AVAILABLE:
        print("❌ Picamera2 not available")
        sys.exit(1)
    
    picam2 = Picamera2()
    
    camera_config = picam2.create_preview_configuration(
        main={
            "size": (640, 480),
            "format": "BGR888"
        }
    )
    
    picam2.configure(camera_config)
    picam2.start()
    time.sleep(2)
    
    frame = picam2.capture_array()
    if frame is None:
        print("❌ Cannot read frame from camera")
        sys.exit(1)
    
    print(f"✅ Camera opened successfully")
    print(f"   Frame shape: {frame.shape}")
    
except Exception as e:
    print(f"❌ Camera failed: {e}")
    traceback.print_exc()
    sys.exit(1)

stop_event = threading.Event()

def camera_server():
    """Stream camera frames to port CAMERA_PORT."""
    print("[CAM] Starting camera server...")
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind(("0.0.0.0", CAMERA_PORT))
        server_socket.listen(1)
        print(f"[CAM] ✅ Listening on port {CAMERA_PORT}")
    except Exception as e:
        print(f"[CAM] ❌ Failed to bind: {e}")
        return
    
    try:
        while not stop_event.is_set():
            server_socket.settimeout(1.0)
            try:
                client_socket, addr = server_socket.accept()
                print(f"[CAM] ✅ Client connected: {addr}")
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[CAM] ❌ Accept failed: {e}")
                continue
            
            frame_count = 0
            try:
                while not stop_event.is_set():
                    frame = picam2.capture_array()
                    if frame is None:
                        print(f"[CAM] ❌ Failed to read frame")
                        break
                    
                    try:
                        frame_data = pickle.dumps(frame)
                        message = struct.pack('Q', len(frame_data)) + frame_data
                        client_socket.sendall(message)
                        frame_count += 1
                        if frame_count % 30 == 0:
                            print(f"[CAM] Sent {frame_count} frames to {addr}")
                    except BrokenPipeError:
                        print(f"[CAM] Client {addr} disconnected")
                        break
                    except Exception as e:
                        print(f"[CAM] Send error: {e}")
                        break
            finally:
                try:
                    client_socket.close()
                except:
                    pass
                print(f"[CAM] Connection closed ({frame_count} frames sent)")
    finally:
        server_socket.close()
        print("[CAM] Camera server stopped")

def command_server():
    """Listen for servo commands on port COMMAND_PORT."""
    print("[CMD] Starting command server...")
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind(("0.0.0.0", COMMAND_PORT))
        server_socket.listen(1)
        print(f"[CMD] ✅ Listening on port {COMMAND_PORT}")
    except Exception as e:
        print(f"[CMD] ❌ Failed to bind: {e}")
        return
    
    try:
        while not stop_event.is_set():
            server_socket.settimeout(1.0)
            try:
                client_socket, addr = server_socket.accept()
                print(f"[CMD] ✅ Client connected: {addr}")
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[CMD] ❌ Accept failed: {e}")
                continue
            
            try:
                client_socket.settimeout(2.0)
                while not stop_event.is_set():
                    try:
                        data = client_socket.recv(1024).decode('utf-8').strip()
                        if not data:
                            break
                        
                        parts = data.split(',')
                        if len(parts) == 3:
                            pan = int(parts[0])
                            tilt = int(parts[1])
                            fire = int(parts[2])
                            
                            if ser:
                                try:
                                    ser.send_aim(pan, tilt, fire)
                                    print(f"[CMD] ✅ Sent to Arduino: pan={pan}, tilt={tilt}, fire={fire}")
                                except Exception as e:
                                    print(f"[CMD] ❌ Arduino send failed: {e}")
                            else:
                                print(f"[CMD] (No Arduino) pan={pan}, tilt={tilt}, fire={fire}")
                        else:
                            print(f"[CMD] Invalid format: {data}")
                    except socket.timeout:
                        continue
                    except Exception as e:
                        print(f"[CMD] Receive error: {e}")
                        break
            finally:
                client_socket.close()
                print(f"[CMD] Connection closed")
    finally:
        server_socket.close()
        print("[CMD] Command server stopped")

# Start servers
cam_thread = threading.Thread(target=camera_server, daemon=True)
cmd_thread = threading.Thread(target=command_server, daemon=True)
cam_thread.start()
cmd_thread.start()

print()
print("=" * 60)
print("🎯 TURRET PI SERVER RUNNING")
print("=" * 60)
print(f"Camera stream: port {CAMERA_PORT}")
print(f"Command listener: port {COMMAND_PORT}")
print("Press Ctrl+C to stop")
print()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n🛑 Shutting down...")
    stop_event.set()
    time.sleep(1)
    if picam2:
        picam2.stop()
    if ser:
        ser.close()
    print("✅ Shutdown complete")
EOF
