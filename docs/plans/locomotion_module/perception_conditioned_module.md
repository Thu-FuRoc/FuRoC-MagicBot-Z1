# Perception-Conditioned Locomotion 模块样例

## 一、模块目标

这个模块主要关注：

- 将视觉、深度、高度图或地形先验接入 locomotion
- 从“盲走”升级到“看着走”
- 提高复杂环境中的前瞻能力

## 二、它和当前 Locomotion 样例的关系

当前样例更多是：

- command-conditioned
- terrain curriculum-conditioned

而 perception-conditioned 模块会引入额外感知输入。

## 三、推荐整理内容

1. 感知输入类型
2. 感知与策略的耦合方式
3. 感知噪声与鲁棒性
4. 高度图 / 视觉先验如何影响 locomotion
5. 感知失效时的退化行为

## 四、适合作为后续样例的内容

- blind locomotion vs perception-conditioned locomotion
- 高度图输入样例
- 感知延迟与策略稳定性对比

## 五、模块定位

这是把 locomotion 从“样例课程”扩展到“复杂环境能力”的关键模块。
