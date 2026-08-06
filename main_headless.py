# python
"""
Turret Headless - Network Camera + Local Servo Control
Runs on Raspberry Pi:
  1. Captures camera frames and streams them over TCP
  2. Receives detection commands from laptop (dx, dy, fire)
  3. Sends servo commands to Arduino
"""
import time
import math
import cv2
import gc
import socket
import struct
import pickle
import threading
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from serial_comm import SerialController

# Configuration
SERIAL_RATE_HZ = 20
SERIAL_INTERVAL = 1.0 / SERIAL_RATE_HZ

# Network settings
CAMERA_STREAM_PORT = 5000
COMMAND_LISTEN_PORT = 5001
BUFFER_SIZE = 1024


def run_headless(camera_index=0, serial_port=None, model_path="yolov8n.pt", runtime_seconds=None):
    """
    Run turret on Raspberry Pi:
    - Stream camera frames over TCP port 5000
    - Listen for servo commands over TCP port 5001
    - Send servo commands to Arduino
    """
    
    print("✅ Turret Pi Mode - Camera streaming + Command receiver")
    
    # Initialize serial (Arduino)
    try:
        ser = SerialController(serial_port)
        print("✅ Serial controller initialized")
    except Exception as e:
        print(f"❌ Failed to initialize serial: {e}")
        return

    # Open camera
    try:
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            print("❌ Cannot open camera")
            return
        try:
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except:
            pass
        try:
            cap.set(cv2.CAP_PROP_FPS, 30)
        except:
            pass
        print("✅ Camera opened")
    except Exception as e:
        print(f"❌ Failed to open camera: {e}")
        return

    # Shared state for servo commands
    latest_command = {"dx": 0, "dy": 0, "fire": False}
    command_lock = threading.Lock()
    last_serial_send = time.time()
    start_time = time.time()
    frame_count = 0
    
    # Command receiver thread
    def command_receiver():
        """Listen on port 5001 for servo commands from laptop."""
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(('0.0.0.0', COMMAND_LISTEN_PORT))
            server.listen(1)
            print(f"[CMD] Listening for commands on port {COMMAND_LISTEN_PORT}...")
            
            while True:
                try:
                    client, addr = server.accept()
                    print(f"[CMD] Laptop connected from {addr}")
                    
                    while True:
                        try:
                            data = client.recv(BUFFER_SIZE)
                            if not data:
                                break
                            
                            # Parse: "dx,dy,fire\n"
                            msg = data.decode().strip()
                            parts = msg.split(',')
                            if len(parts) >= 3:
                                dx = int(parts[0])
                                dy = int(parts[1])
                                fire = int(parts[2]) != 0
                                
                                with command_lock:
                                    latest_command["dx"] = dx
                                    latest_command["dy"] = dy
                                    latest_command["fire"] = fire
                                
                                print(f"[CMD] Received: dx={dx}, dy={dy}, fire={fire}")
                        except Exception as e:
                            print(f"[CMD] Client error: {e}")
                            break
                    client.close()
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"[CMD] Accept error: {e}")
        finally:
            try:
                server.close()
            except:
                pass
    
    # Camera stream thread
    def camera_streamer():
        """Stream camera frames over port 5000."""
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(('0.0.0.0', CAMERA_STREAM_PORT))
            server.listen(1)
            print(f"[CAM] Streaming camera on port {CAMERA_STREAM_PORT}...")
            
            while True:
                try:
                    client, addr = server.accept()
                    print(f"[CAM] Laptop connected from {addr}")
                    
                    while True:
                        ret, frame = cap.read()
                        if not ret:
                            break
                        
                        # Serialize and send frame
                        frame_data = pickle.dumps(frame)
                        message = struct.pack('Q', len(frame_data)) + frame_data
                        
                        try:
                            client.sendall(message)
                        except:
                            print("[CAM] Client disconnected")
                            break
                    
                    client.close()
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"[CAM] Error: {e}")
        finally:
            try:
                server.close()
            except:
                pass
    
    # Start background threads
    cmd_thread = threading.Thread(target=command_receiver, daemon=True)
    cam_thread = threading.Thread(target=camera_streamer, daemon=True)
    cmd_thread.start()
    cam_thread.start()
    
    print("✅ Turret running - waiting for laptop connection...")
    print()
    
    # Main loop - read commands and send to Arduino
    try:
        while True:
            # Check runtime limit
            if runtime_seconds and (time.time() - start_time) > runtime_seconds:
                print(f"\n✅ Runtime limit ({runtime_seconds}s) reached")
                break
            
            # Send servo command to Arduino at fixed rate
            now = time.time()
            if now - last_serial_send >= SERIAL_INTERVAL:
                with command_lock:
                    dx = latest_command["dx"]
                    dy = latest_command["dy"]
                    fire = latest_command["fire"]
                
                try:
                    ser.send_aim(dx, dy, fire)
                    last_serial_send = now
                except Exception as e:
                    print(f"❌ Serial error: {e}")
            
            # Periodic status
            frame_count += 1
            if frame_count % 50 == 0:
                with command_lock:
                    print(f"[{frame_count:6d}] Last command: dx={latest_command['dx']:+4d} dy={latest_command['dy']:+4d} fire={int(latest_command['fire'])}")
            
            time.sleep(0.01)
    
    except KeyboardInterrupt:
        print("\n\n🛑 User interrupted")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nCleaning up...")
        try:
            ser.close()
            cap.release()
        except:
            pass
        print("✅ Done")


if __name__ == "__main__":
    run_headless(camera_index=0, serial_port='/dev/ttyACM0', runtime_seconds=None)

