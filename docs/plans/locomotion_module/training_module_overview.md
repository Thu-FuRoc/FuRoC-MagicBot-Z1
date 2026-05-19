# Beyond Mimic 框架总览

`Beyond Mimic` 这条线，适合被理解成一个完整的动作模仿框架，而不是单个训练脚本。

## 它解决什么问题

目标不是纯粹学会走路，而是：

1. 接入参考动作
2. 把动作转成机器人可执行表示
3. 在仿真中验证动作
4. 训练一个能跟踪这些动作的策略
5. 把策略导出并在其他仿真器中继续验证

## 框架主链路

1. Motion Retarget
2. CSV -> NPZ
3. Replay Verify
4. PPO Train
5. Play / Export
6. MuJoCo Sim2Sim

## 关键入口脚本

| 环节 | 脚本 |
| --- | --- |
| 预处理 | `scripts/csv_to_npz_z1.py` |
| 回放 | `scripts/replay_npz_z1.py` |
| 训练 | `scripts/rsl_rl/train.py` |
| 播放与导出 | `scripts/rsl_rl/play.py` |
| MuJoCo 验证 | `scripts/sim2sim_mujoco.py` |

## 为什么这条线值得单独保留

1. 从数据到训练到回放是闭环的
2. 可以本地播放，也能继续往 sim-to-sim 走
3. 很适合做知识库中的“框架样例”

## 当前结论

这条线的重点不是“某个 reward 权重”，而是“整条动作模仿流水线已经可复现”。

