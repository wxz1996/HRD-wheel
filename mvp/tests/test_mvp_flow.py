from __future__ import annotations

from collections import defaultdict

from mvp.cloud.memory_store import StatusMemoryStore
from mvp.cloud.server import CloudServer
from mvp.robot.agent import RobotAgent
from mvp.robot.navigator import NavigationResult, NavigatorAdapter


class FakeBroker:
    def __init__(self):
        self.handlers = defaultdict(list)

    def subscribe(self, topic, handler):
        self.handlers[topic].append(handler)

    def publish(self, topic, payload):
        for h in self.handlers.get(topic, []):
            h(payload)


class FakeJsonClient:
    def __init__(self, broker: FakeBroker):
        self.broker = broker

    def connect(self):
        return None

    def loop_start(self):
        return None

    def loop_forever(self):
        return None

    def subscribe_json(self, topic, handler, qos=1):
        self.broker.subscribe(topic, handler)

    def publish_json(self, topic, payload, qos=1):
        self.broker.publish(topic, payload)


class OkNavigator(NavigatorAdapter):
    def send_nav_goal(self, goal):
        assert goal == {
            "frame_id": "map",
            "x": 0.1,
            "y": 0.0,
            "z": 0.0,
            "roll": 0.0,
            "pitch": 0.0,
            "yaw": 0.0,
        }
        return NavigationResult(ok=True, message="ok")


def test_cloud_robot_roundtrip(tmp_path):
    broker = FakeBroker()
    cloud_client = FakeJsonClient(broker)
    robot_client = FakeJsonClient(broker)
    store = StatusMemoryStore(db_path=str(tmp_path / "memory.db"))

    cloud = CloudServer("RBT-001", cloud_client, store)
    robot = RobotAgent("RBT-001", robot_client, navigator=OkNavigator())

    cloud_client.subscribe_json(cloud.status_topic, cloud.on_status)
    robot_client.subscribe_json(robot.cmd_topic, robot.on_command)

    cmd_id = cloud.send_forward_command(0.1)

    rows = store.list_statuses("RBT-001")
    assert len(rows) == 2
    assert rows[0][2] == cmd_id
    assert rows[0][4] == "accepted"
    assert rows[1][4] == "success"
