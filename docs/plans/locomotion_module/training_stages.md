# Beyond Mimic 数据与训练流水线

## 流水线分阶段

### 1. Motion Retarget

先把人类动作或外部动作数据，转成机器人能接受的关节表示。

这里的重点不是训练，而是动作源如何进入系统。

### 2. CSV -> NPZ

用 `csv_to_npz_z1.py` 把预处理后的关节和 root pose，转成可用于训练和回放的 `npz`。

这一步是动作数据标准化。

### 3. Replay Verify

在 Isaac Sim 里先 kinematic replay。

这一步的目的：

1. 检查动作本身是否合理
2. 检查 retarget 结果是否错位
3. 在进入 PPO 前就发现问题

### 4. PPO Training

训练入口是 `scripts/rsl_rl/train.py`。

这一步开始才进入策略学习。

### 5. Playback / Export

训练后的 checkpoint 可以通过 `play.py` 回放，并导出到 `ONNX`。

### 6. MuJoCo Sim-to-Sim

用 `sim2sim_mujoco.py` 在 MuJoCo 中继续验证。

这一步的意义是：

1. 检查观测与动作约定
2. 检查 PD 执行效果
3. 做跨仿真器的一致性验证

## 这条流水线的特点

1. 数据格式明确
2. 每一步都有单独入口脚本
3. 每一步都能独立检查

## 为什么它比“直接开训”更适合作为知识页

因为它让读者理解的是整条链路，而不是只盯住训练阶段。

