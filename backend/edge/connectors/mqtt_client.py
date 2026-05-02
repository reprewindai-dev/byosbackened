"""MQTT connector used by the live protocol canary."""
from __future__ import annotations

import json
import threading
from typing import Any


class MQTTCanaryError(RuntimeError):
    """Raised when an MQTT canary publish or consume fails."""


def build_public_mqtt_payload() -> dict[str, Any]:
    """Return a harmless demo payload with no customer data."""
    return {
        "source": "mqtt-pump-demo",
        "temperature_c": 92,
        "vibration_index": 71,
    }


class MQTTCanaryClient:
    """Publish and consume a single message on the public broker."""

    def __init__(self, host: str, port: int = 1883, timeout: float = 4.0) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self._client = self._load_client()

    @staticmethod
    def _load_client():
        try:
            import paho.mqtt.client as mqtt
        except ModuleNotFoundError as exc:  # pragma: no cover - dependency optional
            raise MQTTCanaryError("paho-mqtt is not installed") from exc
        return mqtt

    def publish_and_consume(self, topic: str, payload: dict[str, Any]) -> dict[str, Any]:
        mqtt = self._client
        received = threading.Event()
        connected = threading.Event()
        consumed_payload: dict[str, Any] = {}
        errors: list[str] = []

        client = mqtt.Client()

        def on_connect(client, userdata, flags, rc, properties=None):  # noqa: ANN001, D401
            if rc not in (0, "0", None):
                errors.append(f"mqtt_connect_rc:{rc}")
                return
            connected.set()
            client.subscribe(topic, qos=1)

        def on_message(client, userdata, msg):  # noqa: ANN001, D401
            try:
                consumed_payload.update(json.loads(msg.payload.decode("utf-8")))
            except Exception:
                consumed_payload["raw"] = msg.payload.decode("utf-8", errors="ignore")
            received.set()

        client.on_connect = on_connect
        client.on_message = on_message
        client.connect(self.host, self.port, keepalive=max(15, int(self.timeout) * 2))
        client.loop_start()
        try:
            if not connected.wait(self.timeout):
                raise MQTTCanaryError("mqtt_connect_timeout")
            info = client.publish(topic, json.dumps(payload, sort_keys=True), qos=1)
            publish_ok = info.rc == mqtt.MQTT_ERR_SUCCESS
            if not publish_ok:
                raise MQTTCanaryError(f"mqtt_publish_rc:{info.rc}")
            info.wait_for_publish(timeout=self.timeout)
            if not info.is_published():
                raise MQTTCanaryError("mqtt_publish_timeout")
            if not received.wait(self.timeout):
                raise MQTTCanaryError("mqtt_consume_timeout")
            if errors:
                raise MQTTCanaryError(errors[0])
            return {
                "publish_ok": True,
                "consume_ok": True,
                "consumed_payload": consumed_payload,
            }
        finally:
            try:
                client.loop_stop()
            except Exception:
                pass
            try:
                client.disconnect()
            except Exception:
                pass
