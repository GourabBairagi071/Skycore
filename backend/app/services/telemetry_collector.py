import math
import os
import threading
import time
from datetime import datetime

from pymavlink import mavutil

from app.core.database import SessionLocal
from app.models.telemetry import Telemetry


class TelemetryCollector:
    """
    SkyCore MAVLink telemetry collector.

    Responsibilities:
    1. Receive MAVLink messages at full available frequency.
    2. Maintain the latest vehicle state in memory.
    3. Persist telemetry to PostgreSQL at a controlled rate.

    This separates real-time telemetry ingestion from database persistence.
    """

    def __init__(
        self,
        connection_string: str = "udpin:127.0.0.1:14561",
        vehicle_id: str = "SKYCORE-001",
        persistence_hz: float = 5.0,
    ):
        self.connection_string = connection_string
        self.vehicle_id = vehicle_id

        self.persistence_hz = persistence_hz
        self.persistence_interval = 1.0 / persistence_hz

        self.connection = None

        self.running = False

        self.receive_thread = None
        self.persistence_thread = None

        self.lock = threading.Lock()

        self.telemetry = {
            "vehicle_id": self.vehicle_id,
            "timestamp": None,
            "latitude": None,
            "longitude": None,
            "altitude": None,
            "ground_speed": None,
            "air_speed": None,
            "battery_voltage": None,
            "battery_current": None,
            "battery_percentage": None,
            "roll": None,
            "pitch": None,
            "yaw": None,
            "flight_mode": None,
        }

    # ------------------------------------------------------------------
    # MAVLink CONNECTION
    # ------------------------------------------------------------------

    def connect(self):
        print(
            f"[Collector] Connecting to "
            f"{self.connection_string}"
        )

        self.connection = mavutil.mavlink_connection(
            self.connection_string,
            source_system=255,
        )

        print("[Collector] Waiting for heartbeat...")

        self.connection.wait_heartbeat()

        print(
            "[Collector] Heartbeat received "
            f"system={self.connection.target_system} "
            f"component={self.connection.target_component}"
        )

    # ------------------------------------------------------------------
    # START / STOP
    # ------------------------------------------------------------------

    def start(self):
        if self.running:
            print("[Collector] Already running")
            return

        self.connect()

        self.running = True

        self.receive_thread = threading.Thread(
            target=self._receive_loop,
            daemon=True,
            name="skycore-mavlink-receiver",
        )

        self.persistence_thread = threading.Thread(
            target=self._persistence_loop,
            daemon=True,
            name="skycore-telemetry-persistence",
        )

        self.receive_thread.start()
        self.persistence_thread.start()

        print(
            "[Collector] Started "
            f"(database persistence: {self.persistence_hz:.1f} Hz)"
        )

    def stop(self):
        if not self.running:
            return

        print("[Collector] Stopping...")

        self.running = False

        if self.receive_thread:
            self.receive_thread.join(timeout=2)

        if self.persistence_thread:
            self.persistence_thread.join(timeout=2)

        if self.connection:
            self.connection.close()

        print("[Collector] Stopped")

    # ------------------------------------------------------------------
    # MAVLink RECEIVE LOOP
    # ------------------------------------------------------------------

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
                self._process_message(message)

            except Exception as exc:
                print(
                    f"[Collector] Error processing "
                    f"{message_type}: {exc}"
                )

    # ------------------------------------------------------------------
    # MESSAGE PROCESSING
    # ------------------------------------------------------------------

    def _process_message(self, message):
        message_type = message.get_type()

        with self.lock:

            if message_type == "GLOBAL_POSITION_INT":
                self._process_position(message)

            elif message_type == "ATTITUDE":
                self._process_attitude(message)

            elif message_type == "VFR_HUD":
                self._process_speed(message)

            elif message_type == "SYS_STATUS":
                self._process_battery(message)

            elif message_type == "HEARTBEAT":
                self._process_heartbeat(message)

            else:
                return

            self.telemetry["timestamp"] = datetime.utcnow()

    # ------------------------------------------------------------------
    # MAVLink DATA PARSERS
    # ------------------------------------------------------------------

    def _process_position(self, message):
        self.telemetry["latitude"] = message.lat / 1e7
        self.telemetry["longitude"] = message.lon / 1e7
        self.telemetry["altitude"] = message.relative_alt / 1000.0

    def _process_attitude(self, message):
        self.telemetry["roll"] = math.degrees(message.roll)
        self.telemetry["pitch"] = math.degrees(message.pitch)
        self.telemetry["yaw"] = math.degrees(message.yaw)

    def _process_speed(self, message):
        self.telemetry["ground_speed"] = message.groundspeed
        self.telemetry["air_speed"] = message.airspeed

    def _process_battery(self, message):
        if message.voltage_battery != 65535:
            self.telemetry["battery_voltage"] = (
                message.voltage_battery / 1000.0
            )

        if message.current_battery != -1:
            self.telemetry["battery_current"] = (
                message.current_battery / 100.0
            )

        if message.battery_remaining != -1:
            self.telemetry["battery_percentage"] = (
                message.battery_remaining
            )

    def _process_heartbeat(self, message):
        self.telemetry["flight_mode"] = (
            mavutil.mode_string_v10(message)
        )

    # ------------------------------------------------------------------
    # DATABASE PERSISTENCE LOOP
    # ------------------------------------------------------------------

    def _persistence_loop(self):
        """
        Persist the latest telemetry state at a fixed rate.

        MAVLink reception remains independent from database writes.
        """

        print(
            f"[Database] Persistence loop started "
            f"at {self.persistence_hz:.1f} Hz"
        )

        while self.running:

            start_time = time.monotonic()

            try:
                self._save_to_database()

            except Exception as exc:
                print(
                    f"[Database] Persistence error: {exc}"
                )

            elapsed = time.monotonic() - start_time

            sleep_time = max(
                0.0,
                self.persistence_interval - elapsed,
            )

            time.sleep(sleep_time)

        print("[Database] Persistence loop stopped")

    def _save_to_database(self):
        with self.lock:
            data = self.telemetry.copy()

        if data["timestamp"] is None:
            return

        db = SessionLocal()

        try:
            telemetry_record = Telemetry(**data)

            db.add(telemetry_record)
            db.commit()

        except Exception as exc:
            db.rollback()

            print(
                f"[Database] Error saving telemetry: {exc}"
            )

        finally:
            db.close()

    # ------------------------------------------------------------------
    # LATEST TELEMETRY
    # ------------------------------------------------------------------

    def get_latest(self):
        with self.lock:
            return self.telemetry.copy()


# ======================================================================
# STANDALONE EXECUTION
# ======================================================================

if __name__ == "__main__":

    connection_string = os.getenv(
        "MAVLINK_CONNECTION",
        "udpin:127.0.0.1:14561",
    )

    vehicle_id = os.getenv(
        "SKYCORE_VEHICLE_ID",
        "SKYCORE-001",
    )

    persistence_hz = float(
        os.getenv(
            "TELEMETRY_PERSISTENCE_HZ",
            "5.0",
        )
    )

    collector = TelemetryCollector(
        connection_string=connection_string,
        vehicle_id=vehicle_id,
        persistence_hz=persistence_hz,
    )

    try:

        collector.start()

        while True:
            time.sleep(2)

            data = collector.get_latest()

            print(
                "\n========== SKYCORE TELEMETRY =========="
            )

            for key, value in data.items():
                print(f"{key}: {value}")

    except KeyboardInterrupt:

        print(
            "\n[Collector] Shutting down..."
        )

    finally:

        collector.stop()
