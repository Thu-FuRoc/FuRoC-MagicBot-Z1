# Z1 训练方案对比分析

> 2026-05-21 | 基于 Isaac Lab 源码、社区最佳实践和当前项目实际训练数据分析

---

## 1. 三种方案概述

### 1.1 Legged_gym 官方方案（Isaac Lab 原生）

NVIDIA Isaac Lab 内置的 locomotion 训练框架，以 ANYmal C 四足为基准机器人，同时提供 H1/G1 人形配置。核心设计哲学是 **"简单起步、渐进增加难度"**——单次训练运行，通过 terrain curriculum 自动调整地形难度。

**关键特征：**
- 单阶段训练，无手动 phase 切分
- 仅用 `illegal_contact`（身体触地）+ `time_out` 作为终止条件
- 速度命令从训练一开始就是完整范围
- 地形 curriculum 自动推进，无需人工干预

### 1.2 当前 Pipeline 方案（Magicbot_Z1）

自研的 5-Phase 自动化训练流水线，由 orchestrator 调度。每个 phase 分 coarse/fine 两个子阶段，自动检测过拟合和回滚。

**关键特征：**
- 5 阶段：Flat 启动 → Flat 速度跟踪 → 渐进地形 → 粗糙地形 → 全地形精调
- 每阶段有独立的 PPO 超参和 reward 权重覆盖
- 自动过拟合检测（奖励下降 >25% 触发 LR 衰减）
- 速度命令范围随阶段渐进扩大

### 1.3 社区主流方案

综合 legged_gym 开源社区、Isaac Gym / Isaac Lab 讨论区的实践经验，人形机器人从零训练的通行做法：

**关键特征：**
- 单阶段或两阶段训练（flat → rough）
- 大幅降低初始难度：不使用 `bad_orientation` 终止，不使用外力推扰
- 人形专用 reward：`termination_penalty = -200` 替代硬件终止
- 人类观察 reward 曲线后手动决定是否推进

---

## 2. 核心配置逐项对比

### 2.1 终止条件

| 配置项 | Legged_gym 官方 (ANYmal) | Legged_gym 人形 (H1/G1) | 当前 Pipeline (Z1) | 社区推荐 |
|---|---|---|---|---|
| **time_out** | ✅ 20s | ✅ 20s | ✅ 20s | ✅ |
| **illegal_contact** | ✅ base 触地 (>1N) | ✅ torso 触地 (>1N) | ❌ 未使用 | ✅ 应使用 |
| **bad_orientation** | ❌ 不使用 | ❌ 不使用 | ✅ limit_angle=0.8 (~46°) | ❌ 冷启动不用 |
| **base_height** | ❌ 不使用 | ❌ 不使用 | ✅ min=0.2m | ❌ 冷启动不用 |
| **termination_penalty** | ❌ | ✅ reward=-200 | ❌ | ✅ 推荐 |

**核心差异：** Z1 是唯一在冷启动时使用 `bad_orientation` + `base_height` 双重终止的方案。Legged_gym 即使对 Cassie 双足也不使用方向终止，仅靠身体触地判断。

### 2.2 域随机化

| 配置项 | Legged_gym 官方 (ANYmal) | Legged_gym 人形 (H1/G1) | 当前 Pipeline (Z1) | 社区推荐 |
|---|---|---|---|---|
| **摩擦系数** | 固定 (0.8, 0.8) | 固定 (0.8, 0.8) | (0.1, 2.0) 极宽 | 起步固定或窄范围 |
| **质量随机** | ±5kg | ❌ 禁用 | scale (0.5, 1.5) 全身 | 禁用或极小范围 |
| **初始速度** | vel ±0.5 | 全零 | vel ±0.5 | 全零（人形） |
| **初始关节** | scale (0.5, 1.5) | scale (1.0, 1.0) 精确默认 | scale (1.0, 1.0) | 精确默认（人形） |
| **外力推扰** | 10-15s, ±0.5 m/s | ❌ 禁用 | 3-5s, ±1.0 m/s | 禁用（人形冷启动） |
| **外力（重置时）** | 无 | 无 | (-22, 22) N | 无 |

**核心差异：** Z1 的随机化强度远超所有人形参考实现。摩擦范围 20x 宽于官方，推扰频率 3x、幅度 2x。H1/G1 明确禁用了推扰和附加质量。

### 2.3 Reward 权重

| Reward 项 | Legged_gym (ANYmal) | Legged_gym 人形 (H1/G1) | 当前 Pipeline (Z1) |
|---|---|---|---|
| **track_lin_vel_xy** | 1.0 (exp) | 1.0 (exp) | 1.0 (L2) |
| **track_ang_vel_z** | 0.5 (exp) | 0.5~2.0 (exp) | 0.5 (L2) |
| **alive** | — | — | 0.15 |
| **termination_penalty** | — | **-200** | — |
| **flat_orientation_l2** | 0.0 (rough) / -5.0 (flat) | -1.0 | **-5.0** |
| **base_height_l2** | — | — | **-10.0** |
| **lin_vel_z** | -2.0 | -2.0 | -2.0 |
| **ang_vel_xy** | -0.05 | -0.05 | -0.05 |
| **dof_torques/energy** | -1e-5 | -1e-5 | -2e-5 (energy) |
| **dof_acc** | -2.5e-7 | -2.5e-7 | -5e-7 |
| **action_rate** | -0.01 (L2) | -0.01 (L2) | **-0.1 (L1)** |
| **dof_pos_limits** | 0.0 (禁用) | -1.0 (ankle) | **-5.0** |
| **joint_deviation (hip/roll/yaw)** | — | -0.2 | **-0.7** |
| **joint_deviation (hip_pitch/knee)** | — | — | **-1.0** |
| **stand_still** | — | — | **-3.5** |
| **feet_air_time** | 0.125~0.5 | 0.25 (biped) | — |
| **feet_contact_number** | — | — | 0.5 |
| **feet_clearance** | — | — | 1.0 |
| **feet_slide** | — | -0.25 | -0.2 |
| **undesired_contacts** | -1.0 | -1.0 | -1.0 |

**关键发现：**
- Z1 缺少 `termination_penalty`（H1/G1 用 -200 强烈惩罚摔倒）
- Z1 的 `base_height_l2` (-10.0) 和 `flat_orientation_l2` (-5.0) 同时施加了极强的姿态约束
- `action_rate` 权重是官方的 **10x**，可能过度抑制探索
- `dof_pos_limits` (-5.0) 是官方的四足方案的 **5x** 强度
- 缺少 `feet_air_time`（足部摆空时间奖励），改用 `feet_clearance`——功能类似但奖励结构不同

### 2.4 Curriculum 策略

| 特性 | Legged_gym 官方 | 当前 Pipeline | 社区推荐 |
|---|---|---|---|
| **地形 curriculum** | 自动（基于行走距离） | 5 阶段手动定义 | 自动或手动 |
| **速度命令 curriculum** | 无（从一开始全范围） | 有（随阶段扩大） | 人形建议有 |
| **阶段推进方式** | 无阶段 | orchestrator 自动 | 人工观察后决定 |
| **阶段间 model 加载** | 不适用 | 加载上一阶段 best model | 加载 best model |
| **RL 算法超参调整** | 不调整 | 每阶段降低 LR | 不调整或手动 |

### 2.5 仿真参数

| 参数 | Legged_gym (ANYmal) | Legged_gym 人形 (H1/G1) | Z1 |
|---|---|---|---|
| **dt** | 0.005s | 0.004s | 0.002s |
| **decimation** | 4 | 5 | 10 |
| **控制频率** | 50Hz | 50Hz | 50Hz |
| **episode_length** | 20s | 20s | 20s |
| **action_scale** | 0.5 | 0.25 | 0.25 |
| **num_envs** | 4096 | 4096 | 4096~16384 |

**注：** Z1 用更小的 dt (0.002s) 换取更精细的物理模拟，但需要 10 步 decimation 才能达到 50Hz，计算量更大。

---

## 3. 各方案优劣势分析

### 3.1 Legged_gym 官方方案

**优势：**
- 经过大规模验证（ANYmal、H1、G1 均可稳定收敛）
- 最简单的配置，最小化调试复杂度
- 自动 terrain curriculum，无需人工干预
- reward 设计简洁，权重保守

**劣势：**
- 速度命令无 curriculum，冷启动时随机探索范围大
- 对非标准机器人（如 Z1 双足）需要额外适配
- 无多阶段训练，可能在复杂地形上收敛慢

### 3.2 当前 Pipeline 方案

**优势：**
- 自动化程度最高，理论上无人值守
- 阶段间 reward 权重精细调整，理论上更精确
- 过拟合检测和自动回滚机制
- 速度命令 curriculum 减少早期探索空间

**劣势：**
- 配置复杂度极高，调试困难
- 阶段过渡可能过于激进（p2→p3 奖励从 38→18 骤降）
- 终止条件过于严格，冷启动几乎 100% 失败
- 域随机化过强，与终止条件组合形成"不可能完成的任务"
- 依赖自动指标判断，缺少人工直觉观察

### 3.3 社区主流方案

**优势：**
- 人形专用适配（termination_penalty、禁用推扰、零速度重置）
- 人类-in-the-loop 确保每次推进合理
- 经验证的最佳实践（多个开源项目验证）

**劣势：**
- 需要人工监控，无法全自动
- 没有统一的工具链，依赖经验判断
- 缺乏跨阶段参数管理

---

## 4. 当前 Curriculum 冷启动失败根因回顾

### 4.1 现象

| 指标 | 值 |
|---|---|
| mean reward | -0.63 ~ -1.95（6682 iterations 后仍在负值） |
| bad_orientation 终止率 | 99.98% ~ 100% |
| terrain curriculum level | 0.0（从未进展） |
| 速度命令范围 | ±0.1（最小范围，但仍然失败） |

### 4.2 根因链

```
bad_orientation limit=0.8 (46°) + base_height min=0.2m
        ↓
未训练策略 → 99.98% 立即终止 → episode 平均 <0.5s
        ↓
几乎没有有效学习信号 → reward 持续为负
        ↓
+ 摩擦(0.1~2.0) + 推扰3-5s/±1.0m/s + 重置外力±22N
        ↓
即使侥幸站立也被推倒 → 恶性循环
        ↓
terrain curriculum 永远在 level 0 → 无法推进
```

### 4.3 与成功方案的对比

H1 人形在 Isaac Lab 中的成功配置：
- **无 bad_orientation 终止** → 不因为姿态不佳而终止
- **无 base_height 终止** → 不因为高度不足而终止
- **无推扰** → 不会被外力干扰
- **零速度重置** → 每次从稳定状态开始
- **termination_penalty = -200** → 通过 reward（而非硬终止）鼓励存活
- **固定摩擦** → 减少初始不确定性

Z1 当前配置几乎在每一项上都与 H1 的成功实践相反。

### 4.4 Pipeline 方案的历史问题

Pipeline 阶段过渡中也暴露了类似问题：

| 阶段过渡 | 奖励变化 | 问题 |
|---|---|---|
| p2_fine → p3_coarse | 38.29 → 17.82 (-54%) | 地形引入过于突然 |
| p3_coarse → p3_fine | 失败 | rollback_exhausted |
| p4_fine (历史) | 1.26 | 几乎完全崩溃 |

---

## 5. 社区推荐的最佳实践

### 5.1 终止条件（最关键）

1. **冷启动只用 `illegal_contact`（身体触地）** + `time_out`
2. **禁用 `bad_orientation`**——即使 Cassie 双足也不用
3. **禁用 `base_height` 硬终止**——用 reward 软约束替代
4. **加入 `termination_penalty = -200`**——强烈的存活激励

### 5.2 域随机化（次关键）

1. **摩擦固定或窄范围**（如 0.8~1.0），逐步放宽
2. **禁用推扰**直到机器人能稳定行走
3. **零速度重置**——每次从静止站立开始
4. **禁用附加质量/外力**——减少早期混乱
5. **关节精确默认位**开始——scale=(1.0, 1.0)

### 5.3 Reward 设计

1. **`flat_orientation_l2` 在 rough terrain 设为 0**——官方 rough 配置直接禁用
2. **`base_height_l2` 降低权重或禁用**——-10.0 过于严格
3. **`action_rate` 降至 -0.01~0.02**——当前 -0.1 过度抑制探索
4. **`dof_pos_limits` 降至 -1.0**——当前 -5.0 过于激进
5. **保留 `alive` bonus** 但考虑加大权重
6. **添加 `feet_air_time`** 替代或补充 `feet_clearance`

### 5.4 Curriculum 策略

1. **先 flat 后 rough**——社区共识
2. **速度命令可从小范围开始**（Z1 已做到）
3. **地形 curriculum 自动推进**（基于行走距离）
4. **人工观察 reward 曲线** 后决定是否推进——不要完全自动化
5. **阶段过渡要平滑**——避免奖励骤降

### 5.5 推荐训练流程

```
Phase 1: Flat + 极简配置
  终止: illegal_contact + time_out
  随机: 固定摩擦, 无推扰, 零速度重置
  Reward: termination_penalty=-200, 禁用 orientation/height 硬终止
  目标: 学会站立和基本行走 (~5000-10000 iter)

Phase 2: Flat + 速度跟踪
  启用速度命令 curriculum
  加入温和 reward 约束 (orientation, height)
  目标: 稳定的速度跟踪 (~10000-15000 iter)

Phase 3: 渐进地形
  启用 terrain curriculum (difficulty 0→0.5)
  逐步加入推扰 (先低频弱推)
  目标: 在不平地面行走 (~15000-20000 iter)

Phase 4: 粗糙地形 + 完整随机
  全地形, difficulty 0→1.0
  完整域随机化 (摩擦, 质量, 推扰)
  考虑启用 bad_orientation (limit_angle=1.2 更宽松)
  目标: 鲁棒行走 (~20000-30000 iter)
```

---

## 6. 结论与建议

### 6.1 核心结论

当前 Pipeline 方案的训练失败 **不是算法问题，而是环境配置问题**。具体来说：

1. **终止条件过于严格**是失败的直接原因——99.98% 的 episode 在有用学习发生前就终止了
2. **域随机化过强**是加重因素——即使机器人侥幸站立也被随机化参数推倒
3. **缺少 `termination_penalty`** 导致机器人没有强烈的"活下去"的动机
4. **自动化流水线掩盖了问题**——在没有人工观察的情况下，系统持续在一个不可能成功的配置上训练

### 6.2 建议的行动方案

| 优先级 | 行动 | 预期效果 |
|---|---|---|
| P0 | 移除 `bad_orientation` 和 `base_height` 终止 | episode 不再立即结束 |
| P0 | 添加 `termination_penalty = -200` | 强烈的存活激励 |
| P1 | 固定摩擦到 (0.8, 1.0)，禁用推扰 | 减少初始不确定性 |
| P1 | 零速度重置，精确默认关节位 | 每次从稳定状态开始 |
| P2 | 降低 `action_rate` 到 -0.02 | 允许更多探索 |
| P2 | 降低 `base_height_l2` 到 -1.0 | 减少高度约束 |
| P3 | 重新设计 pipeline 阶段过渡 | 避免 reward 骤降 |

### 6.3 长期方向

- **先验证单阶段训练**：用社区推荐的简化配置跑一次完整训练，确认机器人能学会行走
- **再逐步加难度**：在确认收敛后，逐步加入地形、随机化、更严格的约束
- **最后恢复 pipeline**：在充分理解每个配置项的影响后，重新启用自动化流水线
- **保留人工检查点**：即使使用自动化，也应保留阶段间的人工确认环节

---

## 附录 A：参考配置文件路径

| 文件 | 路径 |
|---|---|
| Z1 环境配置 | `magiclab_rl_lab/source/.../z1/12dof/velocity_env_cfg.py` |
| Isaac Lab 基础 locomotion | `IsaacLab/source/isaaclab_tasks/.../velocity/velocity_env_cfg.py` |
| ANYmal C rough | `IsaacLab/source/isaaclab_tasks/.../velocity/config/anymal_c/rough_env_cfg.py` |
| ANYmal C flat | `IsaacLab/source/isaaclab_tasks/.../velocity/config/anymal_c/flat_env_cfg.py` |
| H1 humanoid | `IsaacLab/source/isaaclab_tasks/.../velocity/config/h1/rough_env_cfg.py` |
| G1 humanoid | `IsaacLab/source/isaaclab_tasks/.../velocity/config/g1/rough_env_cfg.py` |
| 终止函数实现 | `IsaacLab/source/isaaclab/isaaclab/envs/mdp/terminations.py` |
| Reward 函数实现 | `IsaacLab/source/isaaclab_tasks/.../velocity/mdp/rewards.py` |
| Terrain curriculum | `IsaacLab/source/isaaclab_tasks/.../velocity/mdp/curriculums.py` |

## 附录 B：Pipeline 历史训练数据

| 阶段 | 最佳 Reward | Time_out % | Bad_orientation % |
|---|---|---|---|
| p1_coarse | 16.34 | — | — |
| p1_fine | 6.19 | — | — |
| p2_coarse (旧) | 42.68 | — | — |
| p2_fine (旧) | 49.68 | — | — |
| p2_fine (新) | 38.29 | — | — |
| p3_coarse (旧) | 36.37 | 85.8% | 14.2% |
| p3_fine (旧) | 31.2 | 83.6% | 16.4% |
| p3_coarse (新) | 17.82 | — | — |
| p3_fine | ❌ 失败 | — | — |
| p4_fine (旧) | 1.26 | — | — |
