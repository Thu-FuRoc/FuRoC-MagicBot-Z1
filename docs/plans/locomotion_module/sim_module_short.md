# Booster T1 MuJoCo 比赛与回放

`robocup_mujoco` 负责把外部真实 `brain_node` 接入 MuJoCo。

## 它负责什么

1. launcher
2. MuJoCo 仿真
3. 比赛状态机
4. 日志记录
5. 录制与回放
6. bridge 协议

## 当前稳定支持

1. 单机器人调试
2. 多机器人比赛
3. 录制包回放

## 常见入口

- `./scripts/build.sh`
- `./scripts/start_match.sh`
- `./scripts/start_single.sh`
- `./scripts/play_match.sh`
- `./scripts/stop.sh`

## 日志结构

比赛模式默认会写出：

- `logs/<run>/sim.log`
- `logs/<run>/recording/`
- `logs/<run>/blue_*/brain.log`
- `logs/<run>/red_*/brain.log`

## 为什么这部分值得单独做页

因为它说明：

1. 已跑通的不是单个策略，而是完整比赛回放链路
2. 可以从日志、录像、回放三个角度去验证系统
3. 很适合作为“系统级样例”

