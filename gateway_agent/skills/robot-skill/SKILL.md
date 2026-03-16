---
name: robot-skill
description: 作为 HRD-wheel 机器人能力入口 skill 使用，在涉及视频监控、操作、运动、语音、视觉任一机器人子能力，或需要在这些 gateway 子能力之间路由和协调任务时触发。
---

# Robot Skill

## Overview

这是 `gateway_agent/skills` 下机器人能力的聚合入口。命中本 skill 后，先判断任务属于哪一类机器人能力，再只加载对应子 skill 的说明和代码，避免无关上下文进入当前任务。

## Routing Rules

- 先阅读 [references/subskills.md](references/subskills.md)，确定任务应落到哪个子能力。
- 只打开与当前任务直接相关的子 skill 文档和代码；不要默认把五个子 skill 全部读入上下文。
- 如果任务跨多个子能力，优先确认边界：
  - 视频采集与流输出归 `camera_monitor`
  - 机器人动作执行归 `manipulation` 或 `motion`
  - 语音输入输出归 `speech`
  - 识别、检测、跟踪与结构化视觉结果归 `vision`
- 只有在任务确实涉及跨能力协同时，才同时读取多个子 skill。

## Workflow

1. 判断请求是在改视频、运动、操作、语音还是视觉能力。
2. 根据 [references/subskills.md](references/subskills.md) 打开对应子 skill 的 `SKILL.md` 和必要代码文件。
3. 在对应模块内实现修改；如果是跨模块改动，明确输入输出接口、topic、API 或状态字段的责任归属。
4. 改完后验证受影响的入口是否仍然通畅，例如视频状态接口、动作接口、识别结果结构。

## Boundaries

- 本 skill 负责路由和选择上下文，不在这里重复维护五个子 skill 的具体细节。
- `camera_monitor` 当前已有明确实现入口；其余四个子 skill 目前主要是能力占位与规划说明。处理这些区域时，需要先确认是补齐实现，还是仅维护 skill 文档。
- 不要把 Web 前端展示逻辑混入机器人子 skill，除非任务明确要求同步调整前后端接口。

## Example Requests

- “用机器人 skill 看一下视频流为什么没有帧更新”
- “给机器人加一个底盘运动接口，并补安全限幅”
- “实现语音指令到底盘动作的映射”
- “把视觉识别结果透传到 gateway API”
- “去厨房监控燃气灶”

## Task Chaining

- 对于“去厨房监控燃气灶”这类复合任务，优先按 `point_navigation -> camera_monitor -> vision` 的链路编排。
- 对于“若烟雾过大则关闭燃气灶，否则继续监控”这类条件任务，优先按 `point_navigation -> camera_monitor -> vision -> conditional manipulation` 的链路编排。
- 如果网关已经提供高层任务入口，优先复用高层任务接口而不是在 skill 里重复发多个底层命令。
