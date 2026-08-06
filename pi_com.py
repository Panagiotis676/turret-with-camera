import cv2
import socket
import struct
import pickle
import threading
import time

# Camera setup
camera = cv2.VideoCapture(0)  # or libcamera if needed
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

# Server settings
HOST = '0.0.0.0'
PORT = 5000
FRAME_SIZE = 320 * 240 * 3


def send_frames():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(1)

    print(f"[Pi] Waiting for connection on {PORT}...")
    client_socket, client_addr = server_socket.accept()
    print(f"[Pi] Connected to {client_addr}")

    while True:
        ret, frame = camera.read()
        if not ret:
            break

        # Send frame size + frame data
        frame_data = pickle.dumps(frame)
        message = struct.pack('Q', len(frame_data)) + frame_data

        try:
            client_socket.sendall(message)
        except:
            print("[Pi] Client disconnected")
            break

    client_socket.close()
    server_socket.close()
    camera.release()


if __name__ == '__main__':
    send_frames()