import cv2
import socket
import struct
import pickle
import threading
from ultralytics import YOLO
import serial
import time

# YOLO setup (on laptop, torch works fine)
model = YOLO('yolov8n.pt')  # weighs file path

# Servo control via Arduino
arduino = serial.Serial('COM3', 9600, timeout=1)  # adjust COM port
time.sleep(2)

PI_HOST = '192.168.1.100'  # change to your Pi IP
PI_PORT = 5000


def receive_frames_and_infer():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((PI_HOST, PI_PORT))
    print(f"[Laptop] Connected to Pi at {PI_HOST}:{PI_PORT}")

    data = b''
    payload_size = struct.calcsize('Q')

    while True:
        while len(data) < payload_size:
            chunk = client_socket.recv(4096)
            if not chunk:
                return
            data += chunk

        # Extract frame size
        packed_msg_size = data[:payload_size]
        data = data[payload_size:]
        msg_size = struct.unpack('Q', packed_msg_size)[0]

        # Extract full frame
        while len(data) < msg_size:
            data += client_socket.recv(4096)

        frame_data = data[:msg_size]
        data = data[msg_size:]
        frame = pickle.loads(frame_data)

        # Run YOLO inference
        results = model(frame)

        # Extract detections and send servo commands
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = box.conf[0].cpu().numpy()

                if conf > 0.5:
                    center_x = (x1 + x2) / 2
                    center_y = (y1 + y2) / 2

                    # Simple servo control based on detection center
                    # Adjust these values based on your servo range
                    pan_angle = int(90 + (center_x - 160) * 0.3)  # 320/2 = 160
                    tilt_angle = int(90 + (center_y - 120) * 0.3)  # 240/2 = 120

                    # Send to Arduino (adjust format based on your servo_controller)
                    command = f"PAN:{pan_angle} TILT:{tilt_angle}\n"
                    arduino.write(command.encode())
                    print(f"Sent: {command.strip()}")

        # Optional: display on laptop
        annotated_frame = results[0].plot()
        cv2.imshow('YOLO Detection', annotated_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    client_socket.close()
    arduino.close()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    receive_frames_and_infer()