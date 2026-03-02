"""Small wrapper around paho mqtt client."""
from __future__ import annotations

import json
from typing import Callable


class JsonMqttClient:
    def __init__(self, client_id: str, broker_host: str = "localhost", broker_port: int = 1883):
        try:
            import paho.mqtt.client as mqtt
        except ModuleNotFoundError as exc:
            raise RuntimeError("paho-mqtt is required for real MQTT runtime") from exc

        self._client = mqtt.Client(client_id=client_id)
        self._host = broker_host
        self._port = broker_port

    def connect(self) -> None:
        self._client.connect(self._host, self._port, keepalive=60)

    def loop_start(self) -> None:
        self._client.loop_start()

    def loop_forever(self) -> None:
        self._client.loop_forever()

    def subscribe_json(self, topic: str, handler: Callable[[dict], None], qos: int = 1) -> None:
        def _on_message(_client, _userdata, msg):
            payload = json.loads(msg.payload.decode("utf-8"))
            handler(payload)

        self._client.subscribe(topic, qos=qos)
        self._client.message_callback_add(topic, _on_message)

    def publish_json(self, topic: str, payload: dict, qos: int = 1) -> None:
        self._client.publish(topic, json.dumps(payload, ensure_ascii=False), qos=qos)
