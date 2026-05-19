# Sim-to-Real 模块样例

## 一、模块目标

这个模块主要关注：

- 域随机化
- 参数不确定性
- 接触与质量差异
- 真实部署前的泛化准备

## 二、它和当前 Locomotion 样例的关系

当前 `Locomotion` 样例里已经有一些：

- friction randomization
- mass randomization

但这还不是完整的 sim-to-real 专题。

## 三、推荐整理内容

1. 质量、摩擦、惯量随机化
2. 观测噪声与时延
3. actuator mismatch
4. 真实机器人部署前检查项
5. sim-to-sim / sim-to-real 验证流程

## 四、适合作为后续样例的内容

- 随机化配置表
- 仿真与实机差异列表
- 验证 checklist

## 五、模块定位

这是把训练从“会走”推进到“能落地”的关键并列模块。
