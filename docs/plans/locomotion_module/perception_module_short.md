# 如何把一个已跑通框架整理成知识模块

## 当前整理原则

如果一个项目已经能跑通，不应该只记录零散命令，而应该拆成几个稳定层次：

1. 框架定位
2. 数据与训练链路
3. 控制与接口
4. 播放与评估
5. 录制与素材

## Beyond Mimic 适合怎么整理

适合按流水线整理：

- motion source
- preprocessing
- replay
- training
- playback
- sim2sim

## Booster T1 适合怎么整理

适合按系统层次整理：

- robocup
- robocup_lab
- robocup_mujoco
- rule / IL / RL / self-play
- logs / replay / match package

## 为什么要去掉旧的 Z1 内容

因为这组页面现在的目标已经变了：

1. 不再服务于某个 locomotion 实验
2. 要服务于“框架知识沉淀”
3. 要保留能复现、能播放、能展示的主线

## 一句话总结

知识库里最该保留的，不是一次训练的局部参数，而是“别人能不能顺着结构把整条链复现出来”。

