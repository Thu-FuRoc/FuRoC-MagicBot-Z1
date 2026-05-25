# Sim2Sim 指南：Isaac Lab → MuJoCo 策略验证

训练在 Isaac Lab (PhysX) 完成，部署前需要在 MuJoCo 中验证策略鲁棒性。 本文档记录 sim2sim 完整流程、参数匹配清单、已知问题和改进方向。

---

## 1. 整体流程

```
┌─────────────────────────────────────────────────────────┐
│                    Isaac Lab (训练侧)                     │
│                                                         │
│  URDF ──→ PhysX 解析 ──→ 强化学习训练 ──→ 输出 .pt 模型   │
│  (12 DOF, fixed arms)    (隐式PD)         (policy weights)│
│                                                         │
│  关键配置文件:                                            │
│  magiclab.py → 定义 Kp/Kd, armature, init_state 等       │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │  sim2sim 迁移 (本文档重点)
                       │  需要匹配的参数见 §3
                       ▼
┌─────────────────────────────────────────────────────────┐
│                   MuJoCo (验证/部署侧)                    │
│                                                         │
│  MJCF ──→ MuJoCo 解析 ──→ 加载 .pt 模型 ──→ 播放策略      │
│  (12 DOF, fixed arms)    (显式PD)                        │
│                                                         │
│  关键文件:                                               │
│  MAGICBOTZ1.xml → 机器人模型定义                          │
│  mujoco_deploy.py / mujoco_sim2sim.py → 部署脚本         │
└─────────────────────────────────────────────────────────┘

```

三步核心工作： 1. **URDF → MJCF 模型转换** — 确保自由度、质量惯量、关节限位一致 2. **参数匹配** — Kp/Kd、armature、初始角度、观测缩放等逐一校核 3. **sim2sim 迁移验证** — 在 MuJoCo 中加载策略，检查行走效果

---

## 2. 自由度 (DOF) 对比

### 2.1 URDF (`MagicBotZ1_12dof_arm_ready_pos.urdf`)

```
自由关节 (revolute):  12 个 (仅腿部)
  ├─ 左腿: hip_pitch, hip_roll, hip_yaw, knee, ankle_pitch, ankle_roll
  └─ 右腿: hip_pitch, hip_roll, hip_yaw, knee, ankle_pitch, ankle_roll

固定关节 (fixed):     14 个 (手臂+腰部+头部)
  ├─ waist_yaw                                          ← fixed
  ├─ head_yaw                                           ← fixed
  ├─ 左臂: shoulder_pitch/roll/yaw, elbow, wrist_yaw   ← 全部 fixed
  └─ 右臂: shoulder_pitch/roll/yaw, elbow, wrist_yaw   ← 全部 fixed

总 DOF = 12 (腿部)

```

### 2.2 MJCF (`MAGICBOTZ1.xml`) — 当前状态

```
自由关节 (revolute):  12 个 (仅腿部)  ← 和 URDF 一致
固定 (无joint元素):   14 个 (手臂+腰部+头部)  ← 和 URDF 一致

总 DOF = 12
浮动基座 (free joint) = +6 (位置 xyz + 姿态 quat)
总广义坐标维度 = 12 + 7 (quat) = 19

```

### 2.3 手臂 fixed 修复 (2026-05-06)

URDF 中手臂关节全部是 `type="fixed"`，但原 MJCF 中是 revolute。 sim2sim 脚本只控制 12 个腿部关节，手臂在 MuJoCo 中无控自由摆动，导致质心偏移。

**修复**：移除 MJCF 中手臂/腰部/头部的 `<joint>` 元素，将 URDF fixed joint 的 rpy 烘烤到 MJCF body 的 `euler` 属性。
````````

| Body | URDF rpy | MJCF euler | 含义 |
| --- | --- | --- | --- |
| link_la1 / link_ra1 | (0, 0.2, 0) | euler="0 0.2 0" | 肩俯仰 11.5° |
| link_la2 | (0.15, 0, 0) | euler="0.15 0 0" | 左肩侧摆 8.6° |
| link_ra2 | (-0.15, 0, 0) | euler="-0.15 0 0" | 右肩侧摆 -8.6° |
| link_la4 / link_ra4 | (0, 1, 0) | euler="0 1 0" | 肘弯曲 57° |

---

## 3. 参数匹配清单

所有物理/观测参数从 Isaac Lab 训练配置 `magiclab.py` 中逐一对应搬运到 MuJoCo 脚本。

### 3.1 已对齐的参数
**** **** ``````**** ````**** ````**** ````**** ````**** ````**** ````**** ``**** ``````**** **** ````**** ``**** ``**** **** ``

| 类别 | 参数 | Isaac Lab 来源 | MuJoCo 对齐 | 匹配方式 |
| --- | --- | --- | --- | --- |
| 自由度 | 12 revolute + fixed arms | URDF joint type | MJCF 无 joint body | 删 joint 元素 |
| 初始角度 | [-0.35, 0, 0, 0.7, -0.35, 0] ×2 | init_state.joint_pos | reset_sim() 设置 qpos | 手动搬运 |
| 初始高度 | z = 0.69 | init_state.pos | data.qpos[2] = 0.69 | 手动搬运 |
| 质量/惯量 | 各 link 的 mass, inertia | URDF <inertial> | MJCF <inertial> | 直接复制 |
| Kp (stiffness) | [100,100,100,150,60,60]×2 | IdealPDActuator.stiffness | 代码显式 PD | 手动搬运 |
| Kd (damping) | [4,4,4,5,3,3]×2 | IdealPDActuator.damping | 代码显式 PD | 手动搬运 |
| Armature (hip/knee) | 0.02863 | IdealPDActuator.armature | model.dof_armature | 代码设置 |
| Armature (ankle) | 0.01503 | IdealPDActuator.armature | model.dof_armature | 代码设置 |
| 关节阻尼 | 默认 0 | Isaac Lab 默认 | model.dof_damping = 0 | 代码清零 |
| 力矩限制 | [120,120,120,120,50,50]×2 | effort_limit | np.clip(tau, -limit, limit) | 手动搬运 |
| Action scale | 0.25 | 环境配置 | 0.25 | 手动搬运 |
| Timestep | 0.002 (500 Hz) | sim_cfg.dt | MJCF timestep=0.002 | 直接一致 |
| Decimation | 10 → 50 Hz 控制 | 环境配置 | DECIMATION=10 | 手动一致 |
| Obs 缩放 | ang_vel=0.2, joint_vel=0.05 | ObservationCfg | 脚本中对应 | 手动搬运 |
| Obs history | 5 帧，per-term interleaving | 训练配置 | 一致 | 手动搬运 |
| Action clipping | [-1, 1] | 训练配置 | np.clip(act, -1, 1) | 手动搬运 |

### 3.2 参数来源路径

```
Isaac Lab 侧:
  magiclab.py
  └─ MAGICLAB_Z1_12DOF_CFG
      ├─ init_state.joint_pos    → 默认关节角
      ├─ init_state.pos          → 初始高度 (0.69)
      ├─ actuators["legs"]       → Kp, Kd, armature (hip/knee)
      └─ actuators["feet"]       → Kp, Kd, armature (ankle)

MuJoCo 侧:
  mujoco_sim2sim.py
  ├─ Z1RobotConfig              → Kp, Kd, armature, tau_limit
  ├─ Z1ContactConfig            → 接触参数 (friction, solref, solimp)
  └─ Z1ObsConfig                → 观测缩放、gait 参数

  MAGICBOTZ1.xml
  └─ <inertial>                 → 质量/惯量 (与 URDF 一致)
  └─ <body pos="...">           → 连杆长度/偏移 (与 URDF 一致)
  └─ <joint range="...">        → 关节限位 (与 URDF 一致)

```

### 3.3 已修复的差异（2026-05-06 v2）
**** **** **** 

| 项目 | 修复前 | 修复后 | 影响 |
| --- | --- | --- | --- |
| PD 控制频率 | 计算一次，保持 10 步 | 每个物理子步重新计算 | 大幅缩小动态响应差异 |
| 接触参数 | MJCF 默认 solref/solimp | 校准为更硬的接触 | 更接近 PhysX 刚体接触 |
| 摩擦系数 | MJCF 默认 1.0 | 匹配训练随机化中值 0.65 | 更接近训练分布 |

### 3.4 仍存在的差异（物理引擎级别，无法消除）
**** ````**** **** 

| 项目 | Isaac Lab (PhysX) | MuJoCo | 影响 |
| --- | --- | --- | --- |
| PD 公式 | 隐式: τ = Kp*(tgt - q_next) - Kd*dq_next | 显式: τ = Kp*(tgt - q_cur) - Kd*dq_cur | 稳定性边界不同 |
| 接触求解器 | TGS (Technical Gauss-Seidel) | Newton 解析 | 足端接触力分布不同 |
| 积分方式 | PhysX 隐式积分 | MuJoCo 半隐式 Euler | 高频动态不同 |

---

## 4. 隐式 vs 显式 PD — 核心差异详解

这是 sim2sim gap 的根本来源。即使 PD 每步重新计算，隐式/显式的数学差异仍存在。

### 4.1 Isaac Lab (隐式 PD)

```
Isaac Lab 使用 IdealPDActuatorCfg，把 Kp/Kd 作为约束参数传给 PhysX

公式: τ = Kp * (target - q_next) - Kd * dq_next
       其中 q_next, dq_next 是未知量，被 PhysX 隐式求解

特性:
  - 无条件稳定（即使高增益）
  - 等效阻尼包含求解器的数值阻尼
  - 策略会学会利用这种隐含的稳定性

```

### 4.2 MuJoCo (显式 PD)

```
sim2sim 代码每个物理子步重新计算力矩:
  τ = Kp * (target - q_current) - Kd * dq_current
  然后把 τ 传给 MuJoCo 的 motor actuator

特性:
  - 物理上更直观
  - 高增益时可能震荡（不如隐式 PD 稳定）
  - 同样的 Kp/Kd 值产生不同的动态响应

```

### 4.3 关键洞察：Humanoid-Gym 的做法

Humanoid-Gym **不是**用隐式 PD 训练再转到显式 MuJoCo。它采用的做法是： - **训练侧和部署侧都使用显式 PD**：在 Isaac Gym 中手动计算 τ 并通过 `set_dof_actuation_force_tensor` 注入 - 这样两侧的 PD 公式完全一致，消除了最大的 sim2sim gap 来源 - 配合大量 domain randomization（摩擦 0.1–2.0、质量 ±5kg、动作噪声/延迟）使策略对残余差异鲁棒

**启示**：如果要根本消除 PD 差异，需要在 Isaac Lab 中也切换到显式 PD（见 §8.3）。

---

## 5. 当前 Sim2Sim 脚本
**** ``**** **** ``

| 版本 | 脚本 | 风格 | 参数 | 状态 |
| --- | --- | --- | --- | --- |
| Manual | sim2sim/mujoco_manual.py | OOP 类 | Kd+30%, 硬接触, PD/子步 | 调优版 (部署用) |
| Humanoid-Gym | sim2sim/mujoco_humanoid_gym.py | 配置类 | 原始训练值 | 基准对比用 |

### Manual 版（推荐，包含 sim2sim gap 缓解措施）

```
python sim2sim/mujoco_manual.py \
    --mjcf ~/magicbot-z1_description/mjcf/MAGICBOTZ1.xml \
    --policy logs/rsl_rl/<run>/exported/policy.pt \
    --keyboard --num_steps 10000

```

- Kd 增加 ~30% 补偿隐式 PD 的数值阻尼 
- 接触参数校准 (solref=`-3000 -300`, friction=`0.65`) 
- PD 力矩每个物理子步重新计算 
- 支持 JIT `.pt` 和 ONNX 模型 
- 支持键盘实时控制速度指令 

### Humanoid-Gym 版（基准，使用原始训练参数）

```
python sim2sim/mujoco_humanoid_gym.py --sim MuJoCo \
    --mjcf ~/magicbot-z1_description/mjcf/MAGICBOTZ1.xml \
    --checkpoint logs/rsl_rl/<run>/model_NNNN.pt \
    --record /tmp/video.mp4 --duration 20 --vel_x 0.5 --headless

```

- 配置类架构 (`Z1SimConfig`, `Z1RobotConfig`, `Z1ObsConfig`) 
- 使用与训练完全一致的 Kp/Kd/接触参数 
- 支持 EGL 录制 + 键盘实时控制 
- 可与 Manual 版对比验证调优效果 

---

## 6. 已修复的 Bug：Fall Detection

MuJoCo 四元数布局：`qpos[3:7] = (w, x, y, z)`，归一化约束 `w² + x² + y² + z² = 1`。
````````**** ````````

| 脚本 | 检测条件 | 等价于 | 直立时 (w≈1) | 状态 |
| --- | --- | --- | --- | --- |
| mujoco_record_video.py（旧版，已删除） | qpos[3]² + qpos[4]² + qpos[5]² | w² + x² + y² = 1 - z² | 1.0 > 0.5 → 永远 True | BUG |
| mujoco_sim2sim.py | qpos[4]² + qpos[5]² + qpos[6]² | x² + y² + z² = 1 - w² | 0 < 0.5 → False | 正确 |

旧 Bug 导致每步触发 reset，机器人从未真正运行超过 1 个控制步。已于 2026-05-06 修复。

---

## 7. Sim2Sim Gap 分析

### 7.1 已应用的缓解措施
**** **** **** **** **** 

| 措施 | 效果 | 状态 |
| --- | --- | --- |
| PD 每物理子步重新计算 | 修复力矩保持问题，接近隐式 PD 的更新频率 | 已应用 |
| 接触参数校准 (solref/solimp) | MuJoCo 接触更硬，更接近 PhysX 刚体穿透 | 已应用 |
| 摩擦系数匹配训练中值 (0.65) | 接近训练域随机化的均值 | 已应用 |
| 手臂 fixed | 消除手臂无控摆动导致的质心偏移 | 已应用 |
| Fall detection 修复 | 允许正确运行和摔倒检测 | 已应用 |

### 7.2 剩余 Gap 根因

| 优先级 | 根因 | 说明 |
| --- | --- | --- |
| 1 | 隐式 vs 显式 PD | 公式本质不同，见 §4。显式 PD 高增益时等效刚度/阻尼不同 |
| 2 | 接触模型差异 | PhysX 刚体穿透 vs MuJoCo 软约束，接触力分布和断开时机不同 |
| 3 | 策略过拟合 PhysX | RL 策略利用了隐式 PD 的无条件稳定性 |

---

## 8. 改进计划与实验记录

**测试条件**：s2_gentle best model (`model_9900.pt` / exported `policy.pt`)，vel_x=0.5，1000 control steps (20s)

### 8.1 实验对比表

**测试条件**：s2_gentle model_9900 (`exported/policy.pt`)，vel_x=0.5，1000 control steps (20s)
````````

| # | 实验 | 参数变更 | 20s 摔倒 | 视频文件夹 |
| --- | --- | --- | --- | --- |
| 02 | Kd×1.3 + 硬接触 + PD/子步 | Kd+30%, solref=-3000-300, friction=0.65 | 14 | s_model_9900_exp02_kd13/ |
| A | Kd×1.5 | Kd+50% (vs 训练值), 其余同 02 | 14 | s_model_9900_expA_kd15/ |
| B | 动作平滑 EMA | action EMA α=0.7, 其余同 02 | 14 | s_model_9900_expB_ema07/ |
| C | 摩擦 1.0 | friction=1.0 (匹配PhysX), 其余同 02 | 14 | s_model_9900_expC_friction10/ |

> 视频路径：`Magicbot_Z1/videos/sim2sim_experiments/<视频文件夹>/mujoco_manual.mp4` 每个视频右上角已烧录标签（run name + model + falls + params） 

**结论**：A/B/C 三项调参均无效，摔倒次数与 02 完全相同（14 次）。 说明 sim2sim gap 的瓶颈不在 Kd/动作平滑/摩擦，而是**隐式 vs 显式 PD 的根本差异**（§4）。 靠部署侧调参已到极限，Step 3（训练侧切换显式 PD）是唯一出路。

### 8.2 Step 1：增大 Kd ~30%（已应用）

```
# mujoco_manual.py DEFAULT_KD
# 原始: [4, 4, 4, 5, 3, 3] × 2
# 调优: [5.2, 5.2, 5.2, 6.5, 3.9, 3.9] × 2  (+30%)

```

### 8.3 Step 2：更硬的接触参数（已应用）

```
# MJCF 默认:  solref = (-500, -800)
# 调优后:     solref = (-3000, -300)
# 摩擦:       0.65 (训练随机化 0.3–1.0 中值)
# solimp:     (0.9, 0.99, 0.001, 0.5, 2)

```

### 8.4 后续可尝试的调参（在 mujoco_manual.py 中修改）
**** ``**** ``**** ``**** ``**** ``**** 

| # | 调整项 | 修改方式 | 原理 |
| --- | --- | --- | --- |
| A | Kd 加大到 ×1.5 或 ×2.0 | DEFAULT_KD 乘以 1.5/2.0 | 更强阻尼抑制显式 PD 震荡 |
| B | 动作平滑 (EMA) | step() 中 action = α*new + (1-α)*prev，α=0.7 | 模仿隐式 PD 的平滑响应，减少策略抖动 |
| C | 更高摩擦 | CONTACT_FOOT_FRICTION = (1.0, ...) | PhysX 训练用 static=1.0，当前用中值 0.65 可能偏低 |
| D | 更硬接触 | CONTACT_FOOT_SOLREF = (-5000, -500) | 更接近 PhysX 刚体穿透 |
| E | 降低 Kp 10% | DEFAULT_KP * 0.9 | 显式 PD 高增益容易震荡，略降 Kp 换稳定性 |
| F | 重力补偿前馈 | 在 PD 力矩上叠加静态重力补偿项 | 减少关节负担，让 PD 只负责动态跟踪 |

### 8.5 Step 3：训练侧切换到显式 PD（需重新训练）

Step 1+2 验证后效果有限，**Step 3 是根本解决方案**。

```
# magiclab.py 修改
from isaaclab.actuators import ExplicitActuatorCfg

actuators={
    "legs": ExplicitActuatorCfg(
        joint_names_expr=[".*"], effort_limit=120,
        stiffness=100.0, damping=4.0,
    ),
}

```

配合增加 domain randomization： - 摩擦范围 0.1–2.0（当前 0.3–1.0 太窄） - 动作延迟（0–0.5 timestep）+ 动作噪声 - 随机推力扰动

### 8.6 正弦波校准法（辅助）

- 给关节输入正弦波 `q_ref = A*sin(2πft)`
- 对比 Isaac Lab 和 MuJoCo 关节响应 
- 调 Kd/solref 直到轨迹重合 

---

## 9. 参考资料

- [Humanoid-Gym sim2sim 实现](https://github.com/roboterax/humanoid-gym/blob/main/humanoid/scripts/sim2sim.py) — 注意：该项目两侧都用显式 PD，消除了隐式/显式差异 
- [Isaac Lab Newton Sim2Sim 文档](https://isaac-sim.github.io/IsaacLab/main/source/experimental-features/newton-physics-integration/sim-to-sim.html) 
- [NVIDIA Blog: Newton + Isaac Lab](https://developer.nvidia.com/blog/train-a-quadruped-locomotion-policy-and-simulate-cloth-manipulation-with-nvidia-isaac-lab-and-newton/) 
Generated from Sim2Sim_Guide.md