from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MqttServiceSettings:
    host: str
    port: int
    username: str | None
    password: str | None
    client_id: str

    @classmethod
    def from_env(cls, *, default_client_id: str) -> "MqttServiceSettings":
        return cls(
            host=os.getenv("HRT_MQTT_HOST", "127.0.0.1"),
            port=int(os.getenv("HRT_MQTT_PORT", "1883")),
            username=os.getenv("HRT_MQTT_USERNAME"),
            password=os.getenv("HRT_MQTT_PASSWORD"),
            client_id=os.getenv("HRT_MQTT_CLIENT_ID", default_client_id),
        )


class MqttService:
    """Reusable MQTT client lifecycle for robot-facing gateway services."""

    def __init__(
        self,
        *,
        default_client_id: str,
        topic_env_var: str | None = None,
        default_topic: str | None = None,
    ) -> None:
        self.settings = MqttServiceSettings.from_env(default_client_id=default_client_id)
        self.topic = os.getenv(topic_env_var, default_topic) if topic_env_var else default_topic

        self._mqtt = None
        self._client = None
        self._running = False
        self._connected = False
        self._lock = threading.Lock()

        try:
            import paho.mqtt.client as mqtt  # type: ignore

            self._mqtt = mqtt
        except ImportError:
            self._mqtt = None

    @property
    def available(self) -> bool:
        return self._mqtt is not None

    @property
    def connected(self) -> bool:
        with self._lock:
            return self._connected

    def start(self) -> bool:
        if not self.available or self._running:
            return self.available

        mqtt = self._mqtt
        assert mqtt is not None

        client = mqtt.Client(client_id=self.settings.client_id)
        if self.settings.username:
            client.username_pw_set(self.settings.username, self.settings.password)
        client.on_connect = self._handle_connect
        client.on_disconnect = self._handle_disconnect
        client.on_message = self._handle_message

        client.connect_async(self.settings.host, self.settings.port, keepalive=30)
        client.loop_start()

        self._client = client
        self._running = True
        return True

    def stop(self) -> None:
        with self._lock:
            client = self._client
            self._client = None
            self._running = False
            self._connected = False
        if client:
            try:
                client.loop_stop()
                client.disconnect()
            except Exception:
                pass

    def publish(self, topic: str, payload: bytes | str, qos: int = 0, retain: bool = False) -> None:
        client = self._client
        if client is None:
            return
        client.publish(topic, payload=payload, qos=qos, retain=retain)

    def subscription_topics(self) -> list[tuple[str, int]]:
        if self.topic:
            return [(self.topic, 0)]
        return []

    def on_mqtt_connected(self, client: Any) -> None:
        for topic, qos in self.subscription_topics():
            client.subscribe(topic, qos=qos)

    def on_mqtt_disconnected(self, client: Any, rc: int) -> None:
        del client, rc

    def on_mqtt_message(self, topic: str, payload: bytes) -> None:
        del topic, payload

    def _handle_connect(self, client: Any, userdata: Any, flags: Any, rc: int, properties: Any = None) -> None:
        del userdata, flags, properties
        with self._lock:
            self._connected = rc == 0
        if rc == 0:
            self.on_mqtt_connected(client)

    def _handle_disconnect(
        self,
        client: Any,
        userdata: Any,
        rc: int,
        properties: Any = None,
    ) -> None:
        del userdata, properties
        with self._lock:
            self._connected = False
        self.on_mqtt_disconnected(client, rc)

    def _handle_message(self, client: Any, userdata: Any, message: Any) -> None:
        del client, userdata
        payload = message.payload
        if not payload:
            return
        self.on_mqtt_message(message.topic, payload)
