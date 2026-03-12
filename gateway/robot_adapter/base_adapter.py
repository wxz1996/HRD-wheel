class RobotAdapterBase:
    """Adapter mode skeleton for real robot integration."""

    async def connect(self) -> None:
        raise NotImplementedError

    async def read_state(self):
        raise NotImplementedError

    async def read_logs(self):
        raise NotImplementedError

    async def read_vision(self):
        raise NotImplementedError

    async def send_control(self, control: dict):
        raise NotImplementedError
