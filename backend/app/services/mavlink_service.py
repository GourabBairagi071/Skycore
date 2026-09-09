import threading
import time

from pymavlink import mavutil


class MAVLinkService:
    def __init__(
        self,
        connection_string: str = "udpin:127.0.0.1:14561",
        baudrate: int = 57600,
    ):
        self.connection_string = connection_string
        self.baudrate = baudrate

        self.connection = None

        self.running = False
        self.thread = None

    def connect(self):
        print(
            f"[MAVLink] Connecting to "
            f"{self.connection_string}"
        )

        self.connection = mavutil.mavlink_connection(
            self.connection_string,
            source_system=255,
        )

        print("[MAVLink] Waiting for heartbeat...")

        self.connection.wait_heartbeat()

        print(
            "[MAVLink] Heartbeat received "
            f"from system "
            f"{self.connection.target_system}, "
            f"component "
            f"{self.connection.target_component}"
        )

    def start(self):
        if self.running:
            print("[MAVLink] Service already running")
            return

        self.connect()

        self.running = True

        self.thread = threading.Thread(
            target=self._receive_loop,
            daemon=True,
        )

        self.thread.start()

        print("[MAVLink] Service started")

    def stop(self):
        self.running = False

        if self.thread:
            self.thread.join(timeout=2)

        if self.connection:
            self.connection.close()

        print("[MAVLink] Service stopped")

    def _receive_loop(self):
        while self.running:

            message = self.connection.recv_match(
                blocking=True,
                timeout=1,
            )

            if message is None:
                continue

            message_type = message.get_type()

            if message_type == "BAD_DATA":
                continue

            try:
                self._handle_message(message)
            except Exception as exc:
                print(
                    f"[MAVLink] Error processing "
                    f"{message_type}: {exc}"
                )

    def _handle_message(self, message):
        message_type = message.get_type()

        if message_type == "GLOBAL_POSITION_INT":
            self._handle_position(message)

        elif message_type == "ATTITUDE":
            self._handle_attitude(message)

        elif message_type == "VFR_HUD":
            self._handle_speed(message)

        elif message_type == "SYS_STATUS":
            self._handle_system_status(message)

        elif message_type == "HEARTBEAT":
            self._handle_heartbeat(message)

    def _handle_heartbeat(self, message):
        mode = mavutil.mode_string_v10(message)

        print(
            "[MAVLink][HEARTBEAT] "
            f"system={message.get_srcSystem()} "
            f"component={message.get_srcComponent()} "
            f"mode={mode}"
        )

    def _handle_position(self, message):
        latitude = message.lat / 1e7
        longitude = message.lon / 1e7
        altitude = message.relative_alt / 1000

        print(
            "[MAVLink][GPS] "
            f"lat={latitude:.7f} "
            f"lon={longitude:.7f} "
            f"alt={altitude:.2f}m"
        )

    def _handle_attitude(self, message):
        print(
            "[MAVLink][ATTITUDE] "
            f"roll={message.roll:.3f} "
            f"pitch={message.pitch:.3f} "
            f"yaw={message.yaw:.3f}"
        )

    def _handle_speed(self, message):
        print(
            "[MAVLink][SPEED] "
            f"ground={message.groundspeed:.2f} "
            f"air={message.airspeed:.2f}"
        )

    def _handle_system_status(self, message):
        battery_percentage = message.battery_remaining

        voltage = None
        if message.voltage_battery != 65535:
            voltage = message.voltage_battery / 1000

        current = None
        if message.current_battery != -1:
            current = message.current_battery / 100

        print(
            "[MAVLink][BATTERY] "
            f"voltage={voltage}V "
            f"current={current}A "
            f"remaining={battery_percentage}%"
        )


if __name__ == "__main__":
    service = MAVLinkService(
        connection_string="udpin:127.0.0.1:14561",
    )

    try:
        service.start()

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[MAVLink] Shutting down...")

    finally:
        service.stop()