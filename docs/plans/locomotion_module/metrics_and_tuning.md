# Beyond Mimic 控制、观测与奖励

## 控制对象

当前这条线里，策略关注的是“动作跟踪”，而不是传统 locomotion 的速度命令跟踪。

## 观测空间

该策略的观测布局核心包括：

1. reference motion command
2. anchor orientation
3. base angular velocity
4. relative joint position
5. relative joint velocity
6. last action

这说明它是一个强参考驱动的 tracking policy。

## 控制输出

策略输出最终仍然会被映射到机器人的关节控制上，并通过 PD 与 actuator 约定执行。

## 奖励理解方式

这一类框架更适合按“跟踪质量”理解奖励，而不是按传统 locomotion 的：

- `track_lin_vel_xy`
- `stand_still`
- `feet_clearance`

去理解。

它的核心关注点通常是：

1. 参考动作跟踪误差
2. 姿态与身体部位对齐
3. 动作平滑性
4. 执行稳定性

## 调参重点

在这条线里，调参重点通常不是课程阶段切换，而是：

1. 动作数据质量
2. replay 是否正确
3. observation / action 约定是否一致
4. sim2sim 是否对齐

## 一句话总结

`Beyond Mimic` 的难点，更偏“动作表示和执行一致性”，不偏“terrain locomotion 奖励雕刻”。

