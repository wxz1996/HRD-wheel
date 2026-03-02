from __future__ import annotations

from mvp.cloud.memory_store import StatusMemoryStore
from mvp.common.mqtt_client import JsonMqttClient
from mvp.common.schema import CommandMessage


class CloudServer:
    def __init__(self, robot_id: str, mqtt_client: JsonMqttClient, store: StatusMemoryStore):
        self.robot_id = robot_id
        self.mqtt_client = mqtt_client
        self.store = store

    @property
    def cmd_topic(self) -> str:
        return f"robot/{self.robot_id}/cmd/chassis"

    @property
    def status_topic(self) -> str:
        return f"robot/{self.robot_id}/status/nav"

    def on_status(self, msg: dict) -> None:
        self.store.save_status(msg)
        print(f"[cloud] stored status: {msg['status']} cmd={msg['cmd_id']}")

    def send_forward_command(self, x: float = 0.1) -> str:
        command = CommandMessage.new(robot_id=self.robot_id, x=x)
        self.mqtt_client.publish_json(self.cmd_topic, command.to_dict(), qos=1)
        print(f"[cloud] sent action command {command.msg_id}: goal.x={x}")
        return command.msg_id

    def run(self, send_demo: bool = True) -> None:
        self.mqtt_client.connect()
        self.mqtt_client.subscribe_json(self.status_topic, self.on_status, qos=1)
        self.mqtt_client.loop_start()

        if send_demo:
            self.send_forward_command(0.1)

        import time

        while True:
            time.sleep(1)


if __name__ == "__main__":
    client = JsonMqttClient(client_id="cloud-server")
    store = StatusMemoryStore()
    CloudServer(robot_id="RBT-001", mqtt_client=client, store=store).run(send_demo=True)
