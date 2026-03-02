from __future__ import annotations

from mvp.common.mqtt_client import JsonMqttClient
from mvp.common.schema import StatusMessage
from mvp.robot.navigator import NavigatorAdapter, Ros2Navigator


class RobotAgent:
    def __init__(self, robot_id: str, mqtt_client: JsonMqttClient, navigator: NavigatorAdapter | None = None):
        self.robot_id = robot_id
        self.mqtt_client = mqtt_client
        self.navigator = navigator or Ros2Navigator()

    @property
    def cmd_topic(self) -> str:
        return f"robot/{self.robot_id}/cmd/chassis"

    @property
    def status_topic(self) -> str:
        return f"robot/{self.robot_id}/status/nav"

    def on_command(self, cmd: dict) -> None:
        cmd_id = cmd["msg_id"]
        goal = cmd["payload"]["goal"]

        self.mqtt_client.publish_json(
            self.status_topic,
            StatusMessage.new(
                robot_id=self.robot_id,
                cmd_id=cmd_id,
                status="accepted",
                detail={"phase": "received", "action": cmd["payload"].get("action", "")},
            ).to_dict(),
        )

        result = self.navigator.send_nav_goal(goal)

        self.mqtt_client.publish_json(
            self.status_topic,
            StatusMessage.new(
                robot_id=self.robot_id,
                cmd_id=cmd_id,
                status="success" if result.ok else "failed",
                detail={"phase": "finished", "goal": goal, "message": result.message},
            ).to_dict(),
        )

    def run(self) -> None:
        self.mqtt_client.connect()
        self.mqtt_client.subscribe_json(self.cmd_topic, self.on_command, qos=1)
        self.mqtt_client.loop_forever()


if __name__ == "__main__":
    client = JsonMqttClient(client_id="robot-agent")
    RobotAgent(robot_id="RBT-001", mqtt_client=client).run()
