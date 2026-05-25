# Z1 新训练方案 v2 — 对齐 H1/G1 社区最佳实践

## 1. 设计理念

### 核心原则
1. **从极简开始** — Phase 1 仅保留站立+平衡，不加任何干扰
2. **对齐 H1/G1** — 终止条件、reward 权重、events 配置参照 Isaac Lab 官方 H1/G1 人形配置
3. **渐进加难度** — 每个 phase 仅新增 1-2 个难度维度
4. **关键运动关节放开** — hip_pitch / knee 不加偏差惩罚，让策略自由探索步态

### 旧方案失败根因
| 问题 | 旧方案 | 新方案 |
|------|--------|--------|
| bad_orientation(0.8 rad) 过早终止 | p3 99.98% bad_orientation 终止 | 禁用 bad_orientation，仅用 illegal_contact |
| alive=0.15 激励不足 | 终止后无额外惩罚 | termination_penalty=-200（对齐 H1） |
| 域随机化过强 | 摩擦(0.1,2.0)，质量(0.5,1.5) | Phase 1-2 固定摩擦，无质量随机 |
| 推扰过早 | p3 就开始 3-5s 推扰 | Phase 1-2 完全禁用推扰 |
| action_rate 过强 | -0.1 | -0.01（10x 降低） |
| hip_pitch/knee 被约束 | deviation = -1.0 | **weight = 0.0**（完全放开） |
| base_height reward 太强 | -10.0 | -1.0 → -3.0（渐进） |

---

## 2. 4 阶段训练计划

### Phase 1: Flat — 站立与平衡 (8000 iter)
**目标**：机器人能在平地上站稳，不掉倒

| 配置 | 值 | 说明 |
|------|-----|------|
| 终止 | illegal_contact(pelvis, 1N) + time_out | 无 bad_orientation，无 base_height |
| termination_penalty | -200 | 对齐 H1/G1 |
| 地形 | flat plane | 无地形生成器 |
| 摩擦 | 固定 (0.8, 1.0) | 不随机化 |
| 质量随机 | 禁用 | |
| 推扰 | 禁用 | |
| 重置速度 | 全零 (0.0, 0.0) | 精确默认位 |
| 速度命令 | lin_x=[-0.1, 0.1], ang_z=[-0.1, 0.1] | 极小范围 |
| alive | 0.5 | 站立奖励 |
| track_lin/ang | 0.0 | 暂不跟踪速度 |
| flat_orientation | -1.0 | 温和姿态惩罚 |
| base_height reward | -1.0 | 温和高度约束 |
| action_rate | -0.01 | H1 标准 |
| dof_pos_limits | -1.0 | H1 标准 |
| joint_deviation_legs | -0.2 | H1 hip deviation |
| joint_deviation_hip_knee | 0.0 | **放开** |
| feet_air_time | 0.25 | 双足步态奖励 |
| feet_slide | -0.25 | 脚滑惩罚 |
| energy | -1e-5 | 温和能耗惩罚 |
| LR | 1e-3 | |

### Phase 2: Flat — 速度跟踪 (15000 iter)
**目标**：学会跟踪速度命令，前后行走

| 配置 | 值 | 变化 |
|------|-----|------|
| 终止 | 同 Phase 1 | 不变 |
| termination_penalty | -200 | 不变 |
| 速度命令 | lin_x=[0.0, 0.8], ang_z=[-0.5, 0.5] | 扩大 |
| track_lin_vel_xy | 1.0 | **启用** |
| track_ang_vel_z | 0.5 | **启用** |
| alive | 0.3 | 降低 |
| stand_still | -1.0 | **加入**静立惩罚 |
| feet_air_time | 0.25 | 保留 |
| LR | 5e-4 | 降低 |

### Phase 3: 渐进地形 (20000 iter)
**目标**：在简单地形上行走

| 配置 | 值 | 变化 |
|------|-----|------|
| 终止 | 同 Phase 1 | 不变 |
| termination_penalty | -200 | 不变 |
| 地形 | 80% flat + 20% random_grid (diff 0-0.25) | **引入**简单地形 |
| terrain curriculum | 启用 | 自动推进 |
| 摩擦 | (0.6, 1.2) | 开始轻微随机 |
| 推扰 | 每 8-12s, ±0.3 m/s | **极温和**推扰 |
| 速度命令 | lin_x=[0.0, 1.0], ang_z=[-1.0, 1.0] | 对齐 H1 |
| flat_orientation | -2.0 | 增强 |
| base_height | -2.0 | 增强 |
| undesired_contacts | -1.0 | **加入**非期望接触惩罚 |
| feet_clearance | 0.5 | **加入**抬脚奖励 |
| LR | 3e-4 | 降低 |

### Phase 4: 粗糙地形 (30000 iter)
**目标**：全地形鲁棒行走

| 配置 | 值 | 变化 |
|------|-----|------|
| 终止 | illegal_contact + time_out + bad_orientation(1.2 rad) | **可选加入**宽松方向终止 |
| termination_penalty | -200 | 不变 |
| 地形 | 完整混合地形, difficulty 0-1.0 | 全地形 |
| 摩擦 | (0.3, 1.5) | 加宽随机 |
| 质量随机 | scale (0.8, 1.2) | **温和**随机 |
| 推扰 | 每 4-6s, ±0.8 m/s | 中等推扰 |
| 重置速度 | 全零 | 仍从零开始 |
| flat_orientation | -3.0 | 更强 |
| base_height | -3.0 | 更强 |
| action_rate | -0.02 | 适度增加 |
| dof_pos_limits | -2.0 | 增强 |
| stand_still | -2.5 | 增强 |
| undesired_contacts | -1.5 | 增强 |
| feet_slide | -0.3 | 增强 |
| LR | 1e-4 | 最终降低 |

---

## 3. config_generator 所需改动

### 3a. 终止条件可配置化
- YAML 可指定 `terminations.bad_orientation: null` → 删除整个 term
- YAML 可指定 `terminations.base_height: null` → 删除 term
- YAML 可指定 `terminations.illegal_contact: {threshold: 1.0}` → 新增 term
- 默认保留 `time_out`

### 3b. 新增 Reward 定义
- `termination_penalty`: `mdp.is_terminated`, 无 params
- `feet_air_time`: `mdp.feet_air_time_positive_biped`, 带 command/threshold/sensor_cfg

### 3c. Events 可配置化
- `startup.physics_material.friction_range` → 覆盖摩擦范围
- `startup.add_base_mass: null` → 禁用质量随机
- `startup.randomize_others_mass: null` → 禁用
- `reset.reset_robot_joints.velocity_range` → 零速度重置
- `push_robot: null` → 禁用推扰
- `base_external_force_torque: null` → 禁用外力

---

## 4. 执行步骤

### Step 1: 准备
```bash
# SSH 到服务器
ssh phh@192.168.120.155
cd ~/magiclab_rl_lab

# 确保代码已更新
git pull  # 或手动同步修改后的文件
```

### Step 2: 备份旧配置
```bash
# 备份当前 velocity_env_cfg.py
cp source/magiclab_rl_lab/magiclab_rl_lab/tasks/locomotion/robots/z1/12dof/velocity_env_cfg.py \
   source/magiclab_rl_lab/magiclab_rl_lab/tasks/locomotion/robots/z1/12dof/velocity_env_cfg.py.bak_v1

# 删除旧的 .orig 备份（让 generator 从当前状态重新创建）
rm -f source/magiclab_rl_lab/magiclab_rl_lab/tasks/locomotion/robots/z1/12dof/velocity_env_cfg.py.orig
```

### Step 3: Dry-run 验证
```bash
cd scripts
python -m automation.phase_orchestrator \
    --plan training_plans/z1_4phase_plan_v2.yaml --dry-run
```

### Step 4: 启动训练
```bash
# 从 Phase 1 开始全新训练
python -m automation.phase_orchestrator \
    --plan training_plans/z1_4phase_plan_v2.yaml --fresh --num-gpus 4

# 或从某个阶段恢复
python -m automation.phase_orchestrator \
    --plan training_plans/z1_4phase_plan_v2.yaml --start-from p2 --num-gpus 4
```

---

## 5. 验证方法

### 5.1 Phase 1 成功标准
- bad_orientation 终止率 < 5%（理想 < 1%）
- Episode 长度接近 20s（time_out 比例 > 80%）
- Reward 曲线平稳上升，无骤降
- illegal_contact 终止 < 20%

### 5.2 Phase 2 成功标准
- 速度跟踪 RMSE < 0.3 m/s
- 前向行走速度达到 0.5 m/s
- 无明显侧倾

### 5.3 Phase 3 成功标准
- 简单地形上行走速度 > 0.3 m/s
- 推扰恢复率 > 70%

### 5.4 Phase 4 成功标准
- 粗糙地形行走速度 > 0.2 m/s
- 全地形完成率 > 50%

---

## 6. 关键差异对照

| 维度 | 旧方案 (v1) | 新方案 (v2) |
|------|-------------|-------------|
| 终止条件 | bad_orientation(0.8) + base_height(0.2) | illegal_contact(pelvis) + time_out |
| 存活激励 | alive=0.15 | termination_penalty=-200 |
| 初始难度 | 摩擦(0.1~2.0), 推扰3-5s | 固定摩擦(0.8,1.0), 无推扰 |
| action_rate | -0.1 | -0.01 (10x 降低) |
| base_height reward | -10.0 | -1.0 → -3.0 (渐进) |
| dof_pos_limits | -5.0 | -1.0 → -2.0 (渐进) |
| hip_pitch/knee | 偏差惩罚 -1.0 | **完全放开 (weight=0)** |
| feet_air_time | 无 | 0.25（双足步态奖励） |
| 阶段结构 | 5 phase × 2 sub-phase | 4 phase（不拆 coarse/fine） |
| 总迭代数 | ~200,000 | ~73,000 |
