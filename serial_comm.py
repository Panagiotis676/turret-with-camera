from typing import Optional
import time

try:
    import serial
except Exception:
    serial = None


class SerialController:
    """Simple CSV-based serial controller.

    Sends lines like: aim,dx,dy,fire\n
    If pyserial is not available or port is None, prints mock lines.
    """

    def __init__(self, port: Optional[str] = None, baud: int = 115200, timeout: float = 0.1):
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.ser = None
        if port and serial:
            try:
                self.ser = serial.Serial(port, baud, timeout=timeout)
                time.sleep(0.1)
            except Exception as e:
                print(f"Could not open serial port {port}: {e}")
                self.ser = None
        else:
            if port and not serial:
                print("pyserial not installed; serial disabled")

    def send_aim(self, dx: int, dy: int, fire: bool = False):
        line = f"aim,{int(dx)},{int(dy)},{1 if fire else 0}\n"
        if self.ser:
            try:
                self.ser.write(line.encode())
            except Exception as e:
                print("Serial write error:", e)
        else:
            print("SERIAL (mock):", line.strip())

    def close(self):
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass
