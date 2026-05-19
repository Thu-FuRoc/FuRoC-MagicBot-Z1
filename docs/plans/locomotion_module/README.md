# Beyond Mimic 与 Booster T1 模块

本页不再介绍 `Z1 locomotion`。

当前这个知识节点改为两条已经有明确进展的主线：

1. `Beyond Mimic` 框架本身怎么组织
2. `Booster T1` 在 RoboCup / Isaac Lab / MuJoCo 这条链路上已经跑通了什么

## 这个总览页的定位

这页现在是：

1. 一个框架入口页
2. 一个样例导航页
3. 一个把“可复现框架”和“已跑通系统”放在一起的总览页

它不再是：

1. `Z1` 当前训练状态说明
2. `Locomotion` 奖励调参记录
3. 某个单一 locomotion 课程的继续整理页

## 当前保留的两条主线

### A. Beyond Mimic

关注的是一条完整的动作模仿与跟踪流水线：

- motion retarget
- CSV 到 NPZ
- replay verify
- PPO training
- checkpoint playback
- MuJoCo sim-to-sim

这条线的价值在于：

1. 已经成功复现
2. 数据、训练、播放、导出链路清楚
3. 很适合作为“动作模仿框架”的讲解样例

### B. Booster T1

关注的是一条已经能工作的完整系统路线：

- RoboCup ROS2 工作区
- RoboCupLab 分层控制
- 高层 rule / IL / RL / self-play
- 低层 walk / dribble / kick 控制器
- MuJoCo 比赛与回放

这条线的价值在于：

1. 不是只讲训练，而是讲整个系统怎么跑
2. 已经有明确的脚本入口、结构文档和控制接口
3. 适合当作“已跑通平台”的样例

## 页面结构

### A. Beyond Mimic

1. [Beyond Mimic 框架总览](training_module_overview.md)
2. [Beyond Mimic 数据与训练流水线](training_stages.md)
3. [Beyond Mimic 控制、观测与奖励](metrics_and_tuning.md)

### B. Booster T1

1. [Booster T1 总体框架](module_positioning.md)
2. [Booster T1 RoboCupLab 分层控制](robustness_strategies.md)
3. [Booster T1 RL / IL / Self-Play 路线](recovery_getup.md)
4. [Booster T1 MuJoCo 比赛与回放](sim_module_short.md)

### C. 播放、录制与整理

1. [本地播放、在线 Rollout 与评估](imitation_module.md)
2. [远程 Isaac Lab 录制、回传与 GIF](terrain_module_short.md)
3. [如何把一个已跑通框架整理成知识模块](perception_module_short.md)

## 当前原则

这组页面只保留：

- `Beyond Mimic` 的框架与成功复现链路
- `Booster T1` 的系统结构与已跑通能力
- 视频、回放、GIF 和素材回传方式

这组页面移除：

- `Z1` 当前 checkpoint 说明
- `Locomotion` 奖励、惩罚、terrain 课程细节
- 旧的 locomotion 模块树叙事

## 一句话总结

这里现在介绍的是：

“一个已经复现成功的动作模仿框架” 和 “一个已经跑通的 Booster T1 系统样例”。

