from typing import Optional
import time

try:
    import serial
except Exception:
    serial = None


class SerialController:
    """Simple CSV-based serial controller.

    Sends lines like: aim,dx,dy,fire\n
    If pyserial is not available or no port can be opened, prints mock lines.
    """

    def _list_available_ports(self):
        if not serial:
            return []
        try:
            from serial.tools import list_ports

            return list(list_ports.comports())
        except Exception:
            return []

    def _auto_detect_port(self) -> Optional[str]:
        """Return best-effort Arduino serial port candidate."""
        ports = self._list_available_ports()
        if not ports:
            return None

        # Prefer ports whose USB description hints Arduino-compatible boards.
        keywords = ("arduino", "ch340", "cp210", "usb serial", "ftdi")
        for p in ports:
            desc = f"{getattr(p, 'description', '')} {getattr(p, 'manufacturer', '')}".lower()
            if any(k in desc for k in keywords):
                return p.device

        # Fallback: first available COM/serial device.
        return ports[0].device

    def _describe_ports(self) -> str:
        ports = self._list_available_ports()
        if not ports:
            return "none"
        return ", ".join(f"{p.device} ({getattr(p, 'description', 'unknown')})" for p in ports)

    def _open_port_with_retry(self, port: str, retries: int = 4, retry_delay_s: float = 0.4):
        last_error = None
        for attempt in range(1, retries + 1):
            try:
                ser = serial.Serial(port, self.baud, timeout=self.timeout)
                time.sleep(0.1)
                return ser
            except Exception as e:
                last_error = e
                print(f"Serial open attempt {attempt}/{retries} failed on {port}: {type(e).__name__}: {e}")
                # Access denied is commonly transient if another app just released COM port.
                if attempt < retries:
                    time.sleep(retry_delay_s)
        raise last_error

    def __init__(
        self,
        port: Optional[str] = None,
        baud: int = 115200,
        timeout: float = 0.1,
        fallback_to_auto: bool = True,
    ):
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.ser = None

        requested = (port or "").strip()
        requested_lower = requested.lower()

        # Resolve initial port choice.
        if requested and requested_lower not in ("auto",):
            primary_port = requested
        else:
            primary_port = self._auto_detect_port()

        if not serial:
            print("pyserial not installed; serial disabled")
            return

        # Try primary selected port.
        if primary_port:
            try:
                self.ser = self._open_port_with_retry(primary_port)
                self.port = primary_port
                print(f"Serial connected on {primary_port} @ {baud}")
                return
            except Exception as e:
                print(f"Could not open serial port {primary_port}: {type(e).__name__}: {e}")
                print(f"Available ports: {self._describe_ports()}")

        # Optional fallback: if explicit COM failed, try auto-detected alternatives.
        if fallback_to_auto:
            fallback_port = self._auto_detect_port()
            if fallback_port and fallback_port != primary_port:
                try:
                    self.ser = self._open_port_with_retry(fallback_port)
                    self.port = fallback_port
                    print(f"Serial fallback connected on {fallback_port} @ {baud}")
                    return
                except Exception as e:
                    print(f"Fallback serial open failed on {fallback_port}: {type(e).__name__}: {e}")

        print("No usable serial port; running in mock mode")

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
