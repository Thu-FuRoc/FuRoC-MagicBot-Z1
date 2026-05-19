# Booster T1 RL / IL / Self-Play 路线

## 当前支持的高层路线

`RoboCupLab` 当前明确支持四条路线：

1. rule-based planning
2. imitation learning
3. reinforcement learning
4. multi-agent self-play reinforcement learning

## IL

IL 的作用是：

1. 从规则策略或录制数据中学习
2. 形成离线训练闭环
3. 快速迭代高层决策模型

常见脚本：

- `record_data.py`
- `inspect_dataset.py`
- `train_il.py`
- `evaluate.py`

## RL

RL 的重点是训练高层 PPO policy。

这里训练的不是 23 维关节策略，而是高层动作决策。

常见脚本：

- `train_rl.py`
- `evaluate_policy_rollout.py`

## Self-Play

`train_mappo.py` 对应的是 1v1 self-play 路线。

它适合研究：

1. 对抗策略
2. bootstrap opponent schedule
3. 多智能体竞争

## 当前值得保留的结论

`Booster T1` 的亮点不在“某次训练 reward 很高”，而在于：

1. rule / IL / RL / self-play 的入口都已经清晰
2. 高层动作接口统一
3. rollout 与 checkpoint 评估链路已经明确

