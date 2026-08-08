#!/usr/bin/env python3
"""
Raspberry Pi Server - Camera Stream + Command Listener
Runs on the Pi and:
1. Streams camera frames on port 5000 (to laptop)
2. Listens for servo commands on port 5001 (from laptop)
3. Forwards servo commands to Arduino via serial
"""
import cv2
import socket
import struct
import pickle
import threading
import time
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from serial_comm import SerialController

# Configuration
CAMERA_PORT = 5000
COMMAND_PORT = 5001
CAMERA_INDEX = 0
SERIAL_PORT = "/dev/ttyACM0"  # Arduino serial port on Pi

print("=" * 60)
print("🔫 TURRET PI SERVER - Camera Stream + Command Listener")
print("=" * 60)
print()

# Initialize Arduino serial
try:
    ser = SerialController(SERIAL_PORT)
    print(f"✅ Arduino initialized on {SERIAL_PORT}")
except Exception as e:
    print(f"❌ Failed to initialize Arduino: {e}")
    sys.exit(1)

# Open camera
try:
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("❌ Cannot open camera")
        sys.exit(1)
    print(f"✅ Camera opened (index {CAMERA_INDEX})")
except Exception as e:
    print(f"❌ Failed to open camera: {e}")
    sys.exit(1)

stop_event = threading.Event()

def camera_server():
    """Stream camera frames to port CAMERA_PORT."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("0.0.0.0", CAMERA_PORT))
    server_socket.listen(1)
    print(f"✅ Camera server listening on port {CAMERA_PORT}")
    
    client_socket = None
    try:
        while not stop_event.is_set():
            try:
                # Accept connection (blocking, but we'll check stop_event after timeout)
                server_socket.settimeout(1.0)
                try:
                    client_socket, addr = server_socket.accept()
                except socket.timeout:
                    continue
                
                print(f"[CAM] Client connected from {addr}")
                
                while not stop_event.is_set():
                    ret, frame = cap.read()
                    if not ret:
                        print("[CAM] Failed to read frame")
                        break
                    
                    # Pickle and send frame
                    frame_data = pickle.dumps(frame)
                    message = struct.pack('Q', len(frame_data)) + frame_data
                    
                    try:
                        client_socket.sendall(message)
                    except Exception as e:
                        print(f"[CAM] Client disconnected: {e}")
                        break
                
                client_socket.close()
            except Exception as e:
                print(f"[CAM] Error: {e}")
                if client_socket:
                    try:
                        client_socket.close()
                    except:
                        pass
                time.sleep(0.5)
    finally:
        server_socket.close()
        print("[CAM] Camera server closed")

def command_server():
    """Listen for servo commands on port COMMAND_PORT."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("0.0.0.0", COMMAND_PORT))
    server_socket.listen(1)
    print(f"✅ Command server listening on port {COMMAND_PORT}")
    
    client_socket = None
    try:
        while not stop_event.is_set():
            try:
                # Accept connection
                server_socket.settimeout(1.0)
                try:
                    client_socket, addr = server_socket.accept()
                except socket.timeout:
                    continue
                
                print(f"[CMD] Client connected from {addr}")
                client_socket.settimeout(5.0)
                
                while not stop_event.is_set():
                    try:
                        # Receive command line: "pan,tilt,fire\n"
                        data = client_socket.recv(1024).decode('utf-8').strip()
                        if not data:
                            print("[CMD] Client disconnected (empty data)")
                            break
                        
                        # Parse command
                        parts = data.split(',')
                        if len(parts) == 3:
                            pan = int(parts[0])
                            tilt = int(parts[1])
                            fire = int(parts[2])
                            
                            # Send to Arduino
                            ser.send_aim(pan, tilt, fire)
                            print(f"[CMD] Received: pan={pan}, tilt={tilt}, fire={fire}")
                        else:
                            print(f"[CMD] Invalid command format: {data}")
                    
                    except socket.timeout:
                        print("[CMD] Command receive timeout")
                        break
                    except ValueError as e:
                        print(f"[CMD] Parse error: {e}")
                        break
                    except Exception as e:
                        print(f"[CMD] Error: {e}")
                        break
                
                client_socket.close()
            except Exception as e:
                print(f"[CMD] Error: {e}")
                if client_socket:
                    try:
                        client_socket.close()
                    except:
                        pass
                time.sleep(0.5)
    finally:
        server_socket.close()
        print("[CMD] Command server closed")

# Start both servers in background threads
cam_thread = threading.Thread(target=camera_server, daemon=True)
cmd_thread = threading.Thread(target=command_server, daemon=True)

cam_thread.start()
cmd_thread.start()

print()
print("🎯 Turret Pi Server Running")
print("   Camera stream on port 5000")
print("   Command listener on port 5001")
print("   Press Ctrl+C to stop")
print()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n🛑 Shutting down...")
    stop_event.set()
    cam_thread.join(timeout=2)
    cmd_thread.join(timeout=2)
    cap.release()
    ser.close()
    print("✅ Shutdown complete")

