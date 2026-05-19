# Terrain Robustness 模块样例

## 一、模块目标

这个模块主要关注：

- 复杂地形通过能力
- terrain curriculum
- 外扰下的稳定行走
- 足端接触与滑移控制

## 二、它和当前 Locomotion 样例的关系

当前 Z1 的 `P3 -> P5` 已经部分覆盖 terrain robustness，但它仍然可以单独作为模块继续整理。

也就是说：

- 当前样例是入口
- terrain robustness 可以进一步独立成专题

## 三、推荐整理内容

1. 地形类型划分
2. terrain curriculum 推进逻辑
3. 足端相关 reward
4. 扰动与地形如何耦合
5. 常见失败模式

## 四、适合作为后续样例的内容

- flat -> gentle -> rough -> full terrain
- feet slide / clearance / contact 的对比
- terrain level curriculum 曲线

## 五、模块定位

这是当前 `Locomotion` 样例之后最适合独立扩展的下一个模块。
