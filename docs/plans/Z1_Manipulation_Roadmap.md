# Z1 Manipulation Roadmap — 从 Locomotion 到手部操控

> 生成时间: 2026-05-11 基于 MagiclabRobotics GitHub 组织仓库分析 

---

## 1. 仓库资源总览
````````````

| 仓库 | 用途 | 与 Z1 关系 |
| --- | --- | --- |
| magiclab_rl_lab | RL 训练框架 (IsaacLab 2.3.0 + IsaacSim 5.1.0) | 当前在用，locomotion |
| magiclab_deploy | Sim2Real 部署 | 部署阶段使用 |
| magiclab_mujoco | Sim2Sim 验证 (MuJoCo) | sim2sim 验证 |
| magicbot-gen1_pi0_demo | Gen1 双臂灵巧操作 (pi0 VLA 模型) | 参考架构，需适配 |
| magicbot-gen1_description | Gen1 URDF/MJCF (含灵巧手版本) | 手部模型参考 |
| magicbot-z1_sdk | Z1 SDK (C++ + Python) | 已有 arm/hand 控制接口 |

---

## 2. URDF 现状对比
**** ``**** ``**** ````**** ``**** ``**** **** ``**** 

| 版本 | 来源 | 可动关节数 | 手指 |
| --- | --- | --- | --- |
| Z1 本地 URDF | magicbot-z1_description | 14 (12腿 + 2肩pitch，其余全fixed) | 无，J_HAND_L/R 是 fixed |
| Z1 23DOF URDF | magiclab_rl_lab GitHub (feature/z1_12dof 分支) | 23 (12腿 + 1腰 + 10臂 + 1头) | 无，hand_palm_joint 是 fixed |
| Gen1 无手 URDF | magicbot-gen1_description | 30 (12腿 + 2腰 + 2头 + 14臂) | 无 |
| Gen1 带手 URDF | magicbot-gen1_description | 57 (上面 + 22手) | 有！5指灵巧手 (拇指3DOF + 其余各2DOF) |

---

## 3. 关键发现：Z1 硬件有手，但 URDF 没有建模

从 SDK 头文件 `magic_type.h`：

```
constexpr uint8_t kHandJointNum = 6;   // 每只手 6 个关节
constexpr uint8_t kHandNum = 2;        // 左右手

```

SDK 测试代码中每只手实际用了 **7 个 pos 值**，说明 Z1 的灵巧手大约 **6-7 DOF/手**。

SDK 提供的完整手部控制 API： - `PublishHandCommand` — 发布手部控制命令 - `SubscribeHandState` — 订阅手部状态 - `PublishArmCommand` / `SubscribeArmState` — 手臂控制

**结论：Z1 硬件支持灵巧手控制，但所有 URDF 都没有手指关节建模。**

---

## 4. Z1 上做手部操控的可行路线
**** **** ``**** ``**** 

| 路线 | 方法 | 工作量 |
| --- | --- | --- |
| A. 获取 Z1 手部 URDF | 向 Magiclab 要，或基于 SDK 关节数自己建模 | 中 |
| B. 借用 Gen1 手部模型 | 从 MAGICBOT_with_hand.urdf 提取灵巧手部分，适配到 Z1 的 wrist_yaw 末端 | 中，需调整尺寸/质量 |
| C. RL 手部控制 | 在 magiclab_rl_lab 框架上扩展 manipulation task，用 23DOF + 手 URDF 做 RL 训练 | 大，需写 env/reward |
| D. pi0 模仿学习 | 参考 Gen1 的 pi0 pipeline，采集 Z1 遥操作数据，用 LeRobot 训练 | 大，需数据采集硬件 |

---

## 5. 建议优先级

- **获取 Z1 灵巧手 URDF** — 问 Magiclab 或参考 Gen1 手部结构自己建 
- **用 23DOF URDF 先做 locomotion + arm reaching 的 RL 训练** — 在现有框架上扩展 
- **扩展到手部 RL 或 pi0 模仿学习** — 有了 URDF 和 arm 控制基础后再做 

---

## 6. Gen1 灵巧手结构参考 (from `MAGICBOT_with_hand.urdf`)

Gen1 每只手 11 DOF，5 指结构：

```
hand_palm
├── thumb (3 DOF): thumb_joint1 → thumb_joint2 → thumb_joint3
├── forefinger (2 DOF): forefinger_joint1 → forefinger_joint2
├── middle (2 DOF): middle_joint1 → middle_joint2
├── ring (2 DOF): ring_joint1 → ring_joint2
└── little (2 DOF): little_joint1 → little_joint2

```

Z1 灵巧手约 6-7 DOF/手，预计是简化版（可能减少指头数或每指 DOF）。

---

## 7. Route C 详细实施方案：RL 手部控制

### 7.1 可行性判断

**结论：完全可行。** 原因：

- **IsaacLab 已有 manipulation 基础设施** — 内置 `ManagerBasedRLEnv` 支持 manipulation task，包含 Allegro Hand (16DOF)、Shadow Hand (24DOF) 等灵巧手示例 
- **现有 locomotion 框架可复用** — `magiclab_rl_lab` 的配置模式（env_cfg → actions → observations → rewards → terminations）可直接迁移到 manipulation 
- **SDK 确认硬件支持** — `kHandJointNum = 6`，`PublishHandCommand` / `SubscribeHandState` 已就绪 
- **PPO 可处理高维动作空间** — 手部 6DOF + 手臂 10DOF = 16DOF 动作空间，PPO 完全能处理 

### 7.2 前置条件（必须先完成）

- [ ] **获取 Z1 带灵巧手的 URDF** — 路线 A 或 B，这是唯一的硬性依赖 
- [ ] 将 URDF 放到 `data/robots/magicbot-Z1/urdf/MagicBotZ1_30dof.urdf`（假设 12腿 + 1腰 + 10臂 + 1头 + 6手 = 30DOF） 

### 7.3 实施步骤

#### Step 1: 创建 manipulation task 目录结构

在 `source/magiclab_rl_lab/magiclab_rl_lab/tasks/` 下新增：

```
tasks/
├── locomotion/                    # 已有
│   └── robots/z1/12dof/...
└── manipulation/                  # 新增
    ├── __init__.py                # gym.register 注册
    ├── agents/
    │   ├── __init__.py
    │   └── rsl_rl_ppo_cfg.py     # PPO 超参配置
    ├── mdp/
    │   ├── __init__.py
    │   ├── observations.py        # 手部 + 物体观测
    │   ├── rewards.py             # reaching / grasping / lifting 奖励
    │   ├── terminations.py        # 成功 / 失败条件
    │   └── commands.py            # 目标物体位置指令
    └── robots/
        ├── __init__.py
        └── z1/
            ├── __init__.py
            └── 30dof/
                ├── __init__.py
                └── grasp_env_cfg.py    # 主环境配置

```

#### Step 2: 注册环境 (`manipulation/__init__.py`)

```
import gym
from isaaclab_tasks.utils import register_task

gym.register(
    id="Magiclab-Z1-30dof-Grasp-v0",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": f"{__name__}.robots.z1.30dof.grasp_env_cfg:GraspEnvCfg",
        "rsl_rl_cfg_entry_point": f"{__name__}.agents.rsl_rl_ppo_cfg:ManipPPORunnerCfg",
    },
)

```

#### Step 3: 环境配置 (`grasp_env_cfg.py`)

核心配置类，复用 locomotion 的模式：

```
@configclass
class GraspEnvCfg(ManagerBasedRLEnvCfg):
    """Z1 30DOF 灵巧手抓取环境"""

    # 场景：机器人 + 桌子 + 目标物体
    scene: GraspSceneCfg = GraspSceneCfg(num_envs=4096, env_spacing=2.5)

    # 动作空间：手臂 10DOF + 左手 6DOF + 右手 6DOF = 22DOF
    actions: ActionsCfg = ActionsCfg()

    # 观测空间
    observations: ObservationsCfg = ObservationsCfg()

    # 指令：目标物体的位置
    commands: CommandsCfg = CommandsCfg()

    # 奖励
    rewards: RewardsCfg = RewardsCfg()

    # 终止条件
    terminations: TerminationsCfg = TerminationsCfg()

    # 随机化事件
    events: EventCfg = EventCfg()

```

#### Step 4: 动作空间定义

```
@configclass
class ActionsCfg:
    """22DOF 动作：手臂 + 灵巧手"""
    arm_hand_action = mdp.JointPositionActionCfg(
        asset_name="robot",
        joint_names=[
            # 左臂 (5)
            "left_shoulder_pitch_joint", "left_shoulder_roll_joint",
            "left_shoulder_yaw_joint", "left_elbow_joint", "left_wrist_yaw_joint",
            # 右臂 (5)
            "right_shoulder_pitch_joint", "right_shoulder_roll_joint",
            "right_shoulder_yaw_joint", "right_elbow_joint", "right_wrist_yaw_joint",
            # 左手 (6) — 具体名称取决于 URDF
            "left_hand_joint1", "left_hand_joint2", "left_hand_joint3",
            "left_hand_joint4", "left_hand_joint5", "left_hand_joint6",
            # 右手 (6)
            "right_hand_joint1", "right_hand_joint2", "right_hand_joint3",
            "right_hand_joint4", "right_hand_joint5", "right_hand_joint6",
        ],
        scale=0.5,
        use_default_offset=True,
    )

```

#### Step 5: 观测空间定义

```
@configclass
class ObservationsCfg:
    @configclass
    class PolicyCfg(ObsGroup):
        # --- 手臂关节状态 ---
        arm_joint_pos = ObsTerm(func=mdp.joint_pos_rel)
        arm_joint_vel = ObsTerm(func=mdp.joint_vel_rel)

        # --- 手部关节状态 ---
        hand_joint_pos = ObsTerm(func=mdp.joint_pos_rel)  # 手指关节
        hand_joint_vel = ObsTerm(func=mdp.joint_vel_rel)

        # --- 末端执行器（手掌）位置 ---
        left_ee_pos = ObsTerm(func=mdp.ee_pos, params={"ee_name": "left_hand_palm"})
        right_ee_pos = ObsTerm(func=mdp.ee_pos, params={"ee_name": "right_hand_palm"})

        # --- 目标物体状态 ---
        object_position = ObsTerm(func=mdp.object_position)
        object_orientation = ObsTerm(func=mdp.object_orientation)
        object_velocity = ObsTerm(func=mdp.object_velocity)

        # --- 指令 ---
        target_position = ObsTerm(func=mdp.generated_commands, params={"command_name": "object_pose"})

        def __post_init__(self):
            self.history_length = 3
            self.enable_corruption = True

    policy: PolicyCfg = PolicyCfg()

```

#### Step 6: 奖励函数设计（分阶段课程学习）

```
@configclass
class RewardsCfg:
    # === 阶段1: Reaching — 手掌接近物体 ===
    reach_distance = RewTerm(
        func=mdp.finger_tip_distance,   # 末端到物体的距离
        weight=2.0,
        params={"object_name": "cube", "threshold": 0.05},
    )

    # === 阶段2: Grasping — 手指合拢抓住物体 ===
    grasp_success = RewTerm(
        func=mdp.grasp_success_reward,
        weight=5.0,
        params={"object_name": "cube", "contact_threshold": 0.01},
    )

    # === 阶段3: Lifting — 抬起物体 ===
    lift_height = RewTerm(
        func=mdp.object_height_reward,
        weight=3.0,
        params={"object_name": "cube", "target_height": 0.2},
    )

    # === 阶段4: Transport — 移到目标位置 ===
    transport_distance = RewTerm(
        func=mdp.object_to_target_distance,
        weight=2.0,
        params={"target_name": "target_marker"},
    )

    # --- 正则化惩罚 ---
    joint_vel = RewTerm(func=mdp.joint_vel_l2, weight=-0.001)     # 关节速度
    joint_torque = RewTerm(func=mdp.joint_torque_l2, weight=-1e-5) # 力矩
    action_rate = RewTerm(func=mdp.action_rate_l2, weight=-0.01)    # 动作平滑

```

#### Step 7: 终止条件

```
@configclass
class TerminationsCfg:
    time_out = DoneTerm(func=mdp.time_out, time_out=True)

    # 物体掉落
    object_fallen = DoneTerm(
        func=mdp.root_height_below_minimum,
        params={"minimum_height": -0.05, "asset_name": "cube"},
    )

    # 成功：物体到达目标位置
    success = DoneTerm(
        func=mdp.object_at_target,
        params={"target_name": "target_marker", "threshold": 0.05},
    )

```

#### Step 8: 课程学习策略

分 3 个阶段，每个阶段 focus 不同：
**** **** **** 

| 阶段 | 任务 | 奖励权重 | 难度递增 |
| --- | --- | --- | --- |
| Phase 1: Reach | 手掌接近物体 | reach_distance 高 | 物体距离: 近→远 |
| Phase 2: Grasp | 抓住并抬起 | grasp_success + lift_height 高 | 物体大小: 大→小 |
| Phase 3: Transport | 抓起放到目标位置 | transport_distance 高 | 目标距离: 近→远 |

可通过 `CurriculumCfg` 自动调整物体位置范围、大小、摩擦系数等。

### 7.4 训练启动命令

```
# 单卡训练
python scripts/rsl_rl/train.py \
    --task Magiclab-Z1-30dof-Grasp-v0 \
    --num_envs 4096 \
    --headless

# 多卡训练 (4x GPU)
torchrun --nproc_per_node=4 scripts/rsl_rl/train.py \
    --task Magiclab-Z1-30dof-Grasp-v0 \
    --num_envs 16384

```

### 7.5 与 locomotion 的关键差异

| 维度 | Locomotion (当前) | Manipulation (新增) |
| --- | --- | --- |
| 动作空间 | 12DOF (腿部) | 22DOF (手臂10 + 手12) |
| 观测重点 | IMU、关节、足底 | 末端位置、物体状态、接触力 |
| 奖励信号 | 速度跟踪、姿态保持 | 距离、抓取成功、抬升高度 |
| 场景元素 | 地形 | 桌子 + 物体 |
| 课程学习 | 速度→地形难度 | reach → grasp → lift → transport |
| Episode 长度 | ~20s | ~5-10s (抓取更快结束) |

### 7.6 预估工作量

| 任务 | 时间 | 备注 |
| --- | --- | --- |
| 获取/制作 Z1 带手 URDF | 1-2 周 | 硬依赖，可并行 |
| 搭建 manipulation task 框架 | 3-5 天 | 复用 locomotion 模式 |
| 编写 observation/reward 函数 | 3-5 天 | 参考 IsaacLab Allegro Hand 示例 |
| 调试 + 第一轮训练 | 1-2 周 | 需反复调 reward 权重 |
| 课程学习 + 收敛 | 2-3 周 | reach → grasp → lift 渐进 |

**总计约 1.5-2 个月**（URDF 获取后计算）

### 7.7 注意事项

- **先做手臂再加速度** — 不要一上来就训 22DOF，先固定手部只训 arm reaching (10DOF)，确认能 reach 后再加手 
- **参考 IsaacLab 自带示例** — `Isaac-Lift-Cube-Franka-v0` 和 `Kuka-Allegro-Lift` 是最佳参考 
- **sim2real gap** — RL 训出的抓取策略在真机上可能需要大量调参，接触力/摩擦的随机化很重要 
- **与 locomotion 的协调** — 如果要做"边走边抓"，最终需要 whole-body control，动作空间会更大 (12腿 + 10臂 + 12手 = 34DOF)，这是更远期的目标 
Generated from Z1_Manipulation_Roadmap.md