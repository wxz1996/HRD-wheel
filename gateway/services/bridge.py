from mock import data


class RobotBridgeService:
    """Mode-aware service facade for mock or adapter mode."""

    def __init__(self, mode: str = 'mock') -> None:
        self.mode = mode

    def get_state(self):
        return data.tick_state()

    def get_vision(self):
        return data.vision_targets() if data.recognition_enabled else []

    def toggle_recognition(self, enabled: bool):
        data.recognition_enabled = enabled
        return enabled

    def select_target(self, target_id: str):
        data.selected_target_id = target_id
        return next((t for t in data.vision_targets() if t.id == target_id), None)
