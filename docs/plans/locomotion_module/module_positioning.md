# Booster T1 总体框架

`Booster T1` 这一部分不应被当成单个训练实验，而应被当成一个已跑通系统的样例。

## 系统边界

当前能明确分成三层：

1. `robocup`
   负责真实比赛工作区、ROS2 节点、vision、brain、game controller
2. `robocup_lab`
   负责 Isaac Lab / Isaac Sim 中的单机任务、分层控制、IL / RL / self-play
3. `robocup_mujoco`
   负责把外部 `brain_node` 接到 MuJoCo，做比赛、回放和调试

## 为什么这条线重要

因为它不是只讲训练，而是讲：

- 真实工作区如何组织
- 高层策略接口如何统一
- 低层控制器如何复用
- 仿真比赛与回放如何落地

## 当前适合作为知识库里的什么

适合作为：

1. 一个“已跑通的系统样例”
2. 一个“RoboCup 单机任务平台”的样例
3. 一个“分层控制 + 多训练路线并存”的样例

## 不应再怎么写

不应继续写成：

1. 某一个 Z1 训练分支的延伸
2. locomotion 奖励参数专题
3. 只围绕某个 checkpoint 展开

## 一句话定位

`Booster T1` 应放在这里，作为一个已经能运行、能训练、能回放的整体平台样例。

