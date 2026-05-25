# Z1 训练方案索引

> 按训练方法论分类整理，记录每种方法的配置、效果、产物和关键教训。

---

## A 类：Legged Gym / Isaac Lab 社区方案

基于 Isaac Lab H1/G1 社区最佳实践的配置。核心哲学：**简单起步，靠 termination_penalty 软约束存活**。

### 配置要点
- 终止：仅 `illegal_contact` + `time_out`，**不用** `bad_orientation` / `base_height`
- `termination_penalty = -200`（强存活激励）
- 域随机化：固定摩擦、无推扰、零速度重置
- reward 权重保守：`action_rate = -0.01`, `flat_orientation = -1.0`
- `feet_air_time = 0.25`（步态奖励）
- 速度命令可从窄范围开始 curriculum

### 参考配置
- H1 rough: `IsaacLab/.../velocity/config/h1/rough_env_cfg.py`
- G1 rough: `IsaacLab/.../velocity/config/g1/rough_env_cfg.py`

### Z1 实验记录

| 实验 | Plan | 日期 | Best Reward | 状态 | 产物 |
|------|------|------|-------------|------|------|
| v2 4-phase (当前) | `z1_4phase_plan_v2.yaml` | 2026-05-21 | p1: 7.27, p2: 进行中 | 跑着 | p1: `model_3700.pt`, `policy.pt` |

### 教训
- **p1 的 `feet_air_time: 0.25` 与站立阶段矛盾**：鼓励抬脚，导致高抬腿+摔倒
- 站立阶段应设 `feet_air_time: 0.0`
- `feet_air_time` 只应在有速度追踪的阶段（p2+）启用

---

## B 类：自研 PPO Curriculum 方案

多阶段自动化流水线，由 orchestrator 调度。自动过拟合检测 + 回滚 + post-phase 录制。

### 配置要点
- 多阶段手动定义：flat → 速度追踪 → 渐进地形 → 粗糙地形
- 每阶段独立 PPO 超参（LR 递减）和 reward 权重
- 自动过拟合检测（reward 下降 >20%、action rate 恶化、std 坍缩等 5 条件）
- 自动回滚（best_reward < starting_reward × 0.95 → LR×0.5 重试）
- 阶段间 chain best checkpoint

### 参考配置
- v1 5-phase: `training_plans/z1_5phase_plan.yaml`
- orchestrator: `scripts/automation/phase_orchestrator.py`

### Z1 实验记录

| 实验 | Plan | 日期 | 最佳阶段 | Best Reward | 失败原因 |
|------|------|------|----------|-------------|----------|
| v1 5-phase | `z1_5phase_plan.yaml` | 2026-05-18~20 | p2_fine | 49.68 | p3 过渡 reward 骤降 54%，p4 崩溃至 1.26 |

### v1 失败根因
1. `bad_orientation` + `base_height` 双重硬终止 → 99.98% episode 立即终止
2. 域随机化过强（摩擦 0.1~2.0, 推扰 ±1.0m/s）
3. 缺少 `termination_penalty`，没有强存活激励
4. `action_rate = -0.1`（10x 官方值）→ 过度抑制探索

### 教训
- **冷启动不能同时用硬终止 + 强随机化**：两者组合 = 不可能任务
- **自动化流水线会掩盖问题**：系统持续在不可能成功的配置上训练
- **阶段过渡要平滑**：p2→p3 reward 骤降 54% 说明过渡太激进

---

## C 类：AMP / 模仿学习（计划中）

> 尚未开始。预留分类。

### 候选方案
- **AMP** (Adversarial Motion Priors): 需要参考动作数据（MoCap 或手工关键帧）
- **DeepMimic**: 类似 AMP，需要参考轨迹
- **Parkour / Distillation**: 先训练 teacher policy，再蒸馏到 student

### 预期优势
- 自然步态（不依赖 feet_air_time 等间接奖励）
- 更低的 sim2sim gap
- 更快的收敛速度

### 待解决
- Z1 的参考动作数据从哪来？（MoCap / 手工 / 从 B 类最佳 policy 提取）

---

## 产物分类总览

> **[A]** = Legged Gym 社区方案 (v2 4-phase) | **[B]** = 自研 PPO Curriculum (v1 5-phase) | **[C]** = AMP (计划中)

---

### 1. Models（本地无，全部在 RTX 服务器）

| 产物 | 类别 | Run 目录 | 说明 |
|------|------|----------|------|
| p2_coarse `policy.pt` | **[B]** | `2026-05-15_17-44-46_p2_coarse` | 1 checkpoint, JIT exported |
| **p2_fine `policy.pt`** ★ | **[B]** | `2026-05-18_19-35-30_p2_fine` | 32 checkpoints, **reward 49.68** (历史最高) |
| p3_coarse `policy.pt` | **[B]** | `2026-05-20_16-46-08_p3_coarse` | 最后一次 p3 尝试, JIT |
| p1 `model_3700.pt` + `policy.pt` | **[A]** | `2026-05-21_05-34-18_p1` | 46 checkpoints, reward 7.27 |
| p2 (进行中) | **[A]** | `2026-05-21_08-15-14_p2` | 66 checkpoints, iter ~7800 |

> ★ **当前最佳**: v1 p2_fine, reward 49.68。但 p3 过渡失败。
> v2 (A 类) 正在从头训练，p1 reward 7.27，配置更合理。

---

### 2. Videos

#### 本地 — 训练视频 (`videos/p/`)

| 文件 | 类别 | 大小 | 阶段 | 类型 |
|------|------|------|------|------|
| p1_coarse_model_2900_isaaclab.mp4 | **[B]** | 99M | p1 coarse | Isaac Sim |
| p1_coarse_model_2900_mujoco.mp4 | **[B]** | 892K | p1 coarse | MuJoCo |
| p1_fine_model_2800_isaaclab.mp4 | **[B]** | 99M | p1 fine | Isaac Sim |
| p1_fine_model_2800_mujoco.mp4 | **[B]** | 617K | p1 fine | MuJoCo |
| p2_coarse_model_4000_isaaclab.mp4 | **[B]** | 100M | p2 coarse | Isaac Sim |
| p2_coarse_model_4000_mujoco.mp4 | **[B]** | 909K | p2 coarse | MuJoCo |
| **p2_fine_model_4800_isaaclab.mp4** ★ | **[B]** | 98M | **p2 fine** | **Isaac Sim (最佳)** |
| p2_fine_model_4800_mujoco.mp4 | **[B]** | 870K | p2 fine | MuJoCo |
| p3_coarse_model_5000_isaaclab.mp4 | **[B]** | 99M | p3 coarse | Isaac Sim |
| p3_coarse_model_5000_mujoco.mp4 | **[B]** | 1.1M | p3 coarse | MuJoCo |
| z1_p1_mujoco_vx0.0.mp4 | **[A]** | 651K | v2 p1 | MuJoCo, vx=0.0 |
| z1_p1_mujoco.mp4 | **[A]** | 994K | v2 p1 | MuJoCo, vx=0.3 (超出分布) |

#### 本地 — Deploy 日志视频 (`logs/p/`)

| 文件 | 类别 | 说明 |
|------|------|------|
| p3_coarse/.../p3_coarse_m5000_local_tmp.mp4 | **[B]** | p3 coarse 实机日志回放 |
| p3_fine/.../p3_fine_m5500_local_tmp.mp4 | **[B]** | p3 fine 实机日志回放 |
| p3_fine/.../p3_fine_m5500_flat_tmp.mp4 | **[B]** | p3 fine flat 地形回放 |

#### 本地 — GitHub Demo (`docs/github_readme/`)

| 文件 | 类别 | 说明 |
|------|------|------|
| pipeline_p1p2_demo.gif | **[B]** | p1→p2 pipeline 演示 |
| p3_demo.gif | **[B]** | p3 地形演示 |
| p3_sim2sim_mujoco.gif | **[B]** | p3 sim2sim MuJoCo |
| p3_fine_sim2sim_broken.gif | **[B]** | p3 fine sim2sim 问题展示 |
| p3b_demo.gif | **[B]** | p3b 变体演示 |

#### RTX — Pipeline 视频 (`videos/phase_pipeline/`)

| 文件 | 类别 | 大小 | 说明 |
|------|------|------|------|
| p2_coarse_mujoco.mp4 | **[B]** | 459K | |
| p2_fine.mp4 | **[B]** | 20M | Isaac Sim |
| p2_fine_mujoco.mp4 | **[B]** | 460K | |
| p2_fine_symmetry_mujoco.mp4 | **[B]** | 500K | 对称性测试 |
| p3b_coarse_mujoco.mp4 | **[B]** | 399K | |
| p3b_fine_mujoco.mp4 | **[B]** | 401K | |
| p3b_fine_symmetry_mujoco.mp4 | **[B]** | 420K | |
| p3_coarse.mp4 | **[B]** | 21M | Isaac Sim |
| p3_coarse_mujoco.mp4 | **[B]** | 528K | |
| p3_fine_mujoco.mp4 | **[B]** | 394K | |
| p4_coarse_mujoco.mp4 | **[B]** | 328K | reward≈1.26 崩溃 |
| p4_fine_mujoco.mp4 | **[B]** | 494K | |
| p5_coarse_mujoco.mp4 | **[B]** | 474K | |
| p5_fine_mujoco.mp4 | **[B]** | 426K | |

---

### 3. Plots

#### 训练分析报告 (`plots/`)

| 文件 | 类别 | 说明 |
|------|------|------|
| p1_coarse/ | **[B]** | reward_trend, decomposition, termination, efficiency + PDF 报告 |
| p1_fine/ | **[B]** | 同上 |
| **p2_coarse/** | **[B]** | 同上 |
| **p2_fine/** ★ | **[B]** | 同上 (**最佳阶段**) |
| (p3+ 无) | — | v1 p3 失败，无报告 |

#### Deploy 分析图 (`logs/p/.../plots/`)

| 文件 | 类别 | 说明 |
|------|------|------|
| p2_fine/plots/ | **[B]** | trajectory, torques, histogram, joints, actions, vel_height (6 图) |
| p3_coarse/.../plots/ | **[B]** | 同上 6 图 |
| p3_fine/.../plots/ | **[B]** | 同上 6 图 (×2 批次: normal + flat) |

#### GitHub README 图 (`docs/github_readme/`)

| 文件 | 类别 | 说明 |
|------|------|------|
| curriculum_reward_trends.png | **[B]** | 全 curriculum reward 趋势 |
| reward_trend_p2_fine.png | **[B]** | p2 fine reward 趋势 |
| reward_trend_p3b_fine.png | **[B]** | p3b fine reward 趋势 |
| reward_trend_p3_fine.png | **[B]** | p3 fine reward 趋势 |
| reward_decomposition_p2_fine.png | **[B]** | p2 fine 奖励分解 |
| reward_decomposition_p3b_fine.png | **[B]** | p3b fine 奖励分解 |
| reward_decomposition_p3_fine.png | **[B]** | p3 fine 奖励分解 |
| joint_asymmetry_barplot.png | **[B]** | 关节不对称柱状图 |
| joint_asymmetry_p2_vs_p3.png | **[B]** | p2 vs p3 不对称对比 |

#### Plan 文档插图 (`docs/plans/`)

| 文件 | 类别 | 说明 |
|------|------|------|
| curriculum_reward_trends.png | **[B]** | 同 GitHub 版 |
| reward_decomposition_p3_fine.png | **[B]** | 同 GitHub 版 |
| locomotion_phase_map.png | **[B]** | 阶段地图 |
| module_landscape_map.png | **[B]** | 模块全景 |
| disturbance_strategy_map.png | **[B]** | 扰动策略图 |
| recovery_getup_map.png | **[B]** | 恢复起身图 |
| tuning_logic_map.png | **[B]** | 调参逻辑图 |

---

### 汇总

| 类别 | Models (JIT) | Videos | Plots | 最佳 Reward |
|------|-------------|--------|-------|-------------|
| **[A] Legged Gym** | 1 (p1) | 2 (MuJoCo) | 0 | p1: 7.27 (p2 进行中) |
| **[B] 自研 Curriculum** | 3 | 29 | 40+ | **p2_fine: 49.68** ★ |
| **[C] AMP** | 0 | 0 | 0 | — |

> **结论**: 本地所有产物几乎全是 **[B] 类**。[A] 类才刚开始，只有 2 个 MuJoCo 视频。
> p2_fine 是 [B] 类巅峰，但后续阶段全崩。v2 ([A]) 从头来，配置更稳但产出还很少。

---

## 配置详细对比

> 详见 [Z1_Training_Approaches_Comparison.md](./Z1_Training_Approaches_Comparison.md)
