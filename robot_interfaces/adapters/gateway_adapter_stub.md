# Gateway Adapter Stub

目标：后续将 `gateway/robot_adapter/base_adapter.py` 对接到 ROS2 Topic/Service。

- 订阅：`/hrt/robot/state`, `/hrt/vision/results`, `/hrt/robot/logs`
- 发布：`/hrt/control/base_joystick`, `/hrt/control/recognition_toggle`, `/hrt/control/selection`
- 可选调用：`/hrt/service/select_target_action`

当前为接口声明阶段，未做真实驱动。
