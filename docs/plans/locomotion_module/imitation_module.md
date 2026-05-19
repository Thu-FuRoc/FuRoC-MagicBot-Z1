# 本地播放、在线 Rollout 与评估

## Beyond Mimic 这边

已有两类直接可看的结果：

1. replay 参考动作
2. play 训练后的 checkpoint

常见入口：

- `scripts/replay_npz_z1.py`
- `scripts/rsl_rl/play.py`
- `scripts/sim2sim_mujoco.py`

## Booster T1 这边

已有明确的 online rollout 与离线评估入口：

- `evaluate.py`
- `evaluate_policy_rollout.py`

## 本地播放适合回答什么

1. 模型能不能跑起来
2. 控制输出是否合理
3. 画面上动作是否符合预期

## 与训练页的关系

这类页面的重点不是“怎么训”，而是“怎么证明它真的能跑”。

## 当前建议

知识库里要把：

1. 训练入口
2. checkpoint 评估入口
3. 本地播放入口

分开写，不混成一页。

