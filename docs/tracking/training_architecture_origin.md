# Z1 训练架构与 Origin 关系

厘清 `MagiclabRobotics/magiclab_rl_lab`（origin）提供了什么、我们自己搭建了什么、网络结构和权重分别从何而来。
Origin: 提供网络架构 + 基础训练框架 z1-custom: 全部训练策略 + 自动化工具 + 所有权重 Origin 不提供任何预训练权重 

## 1. 训练权重是否提供？

**Origin 不提供任何预训练权重。**

origin 仓库（`MagiclabRobotics/magiclab_rl_lab` 的 `feature/z1_12dof` 分支）中没有任何 `.pt` 文件。它只提供训练代码框架，需要用户自己训练生成模型。

我们仓库中 `models/p/` 下的全部 21 个模型文件均为自行训练产出：
**** **** 

| 来源 | .pt 文件数 | 存储 | 说明 |
| --- | --- | --- | --- |
| Origin | 0 | — | 只给代码，不给模型 |
| 我们 (z1-custom) | 21 | ~187 MB (LFS) | 12 个 Full Checkpoint + 9 个 JIT Policy |

## 2. rsl_rl 的内框架和 Weights

**提供框架，不提供 weights。** Origin 仓库包含完整的 rsl-rl 训练基础设施：
``````````

| 文件 | 作用 | 提供方 |
| --- | --- | --- |
| scripts/rsl_rl/train.py | 训练入口脚本 | Origin |
| scripts/rsl_rl/play.py | 基础播放脚本 | Origin |
| agents/rsl_rl_ppo_cfg.py | PPO 超参配置（含网络结构定义） | Origin |
| velocity_env_cfg.py | 环境配置（地形、奖励、观测） | Origin 基础版 → 我们大幅改造 |
| mdp/rewards.py | 奖励函数定义 | Origin 基础版 → 我们新增多项奖励 |

实际的 rsl-rl 算法库本身（`rsl_rl` Python 包）是独立安装的第三方库（我们用 3.0.1），不在 origin 仓库内。

## 3. 决策神经网络框架 — 三层 MLP（Origin 提供）

**Origin 官方定义了 Actor-Critic 网络结构，三层 MLP。**

位于 `agents/rsl_rl_ppo_cfg.py`，我们沿用至今未修改：

```
policy = RslRlPpoActorCriticCfg(
    init_noise_std=1.0,
    actor_hidden_dims=[512, 256, 128],    # Actor:  三层 MLP
    critic_hidden_dims=[512, 256, 128],    # Critic: 三层 MLP
    activation="elu",
)
```

Shared Hidden Layers INPUT obs ~48 dim joint pos/vel base vel, last act height scanner HIDDEN 1 512 ELU ELU HIDDEN 2 256 ELU ELU HIDDEN 3 128 ELU ACTOR 12 tanh → joint pos CRITIC 1 state value V(s) → PPO loss → action output PPO Algorithm: rsl-rl 3.0.1 | clip=0.2 | γ=0.99 | λ=0.95 | lr=1e-3 | entropy=0.01 | mini-batch=4 | epochs=5 

这个三层结构是 **Isaac Lab + rsl-rl** 的标准配置，由 `RslRlPpoActorCriticCfg` 类（`isaaclab_rl` 包）实现，origin 直接引用。Actor 和 Critic 共享三层隐藏层结构（512→256→128），在最后一层分叉——Actor 输出 12 维关节位置目标（tanh 激活），Critic 输出 1 维 state-value 估计。

### 3.1 白话详解：这个神经网络到底在干什么？

#### 什么是 MLP（多层感知机）？

MLP 就像一个**多级筛选器**。想象一条流水线：原材料（传感器数据）从一端进入，经过三道工序（三个隐藏层），每道工序都在对数据进行不同角度的"提炼"和"理解"，最后输出成品（关节动作指令）。

每一层里面有若干个**"神经元"**。你可以把每个神经元理解为一个"打分员"——它接收上一步传来的所有信息，给每条信息乘上一个权重（相当于"重要性打分"），全部加起来后，再通过一个**激活函数**决定自己要"输出什么信号"给下一层。
单个神经元的工作方式： 输入 x₁ x₂ x₃ … → 加权求和 Σ wᵢ·xᵢ + b → 激活函数 ELU → 输出 y 

其中 `wᵢ` 是权重（这个神经元对第 i 个输入的"重视程度"），`b` 是偏置（一个基础调整值）。这些 w 和 b 就是**"训练"要学的东西**——训练前它们是随机数，训练过程中不断调整，让输出越来越合理。

#### Z1 的三层分别干什么？

网络从"宽"到"窄"（512→256→128），这是一种经典的**信息压缩**设计。每一层都在做不同层次的特征提取：
第一层 · 512 个神经元 "广泛接收"  512 个神经元，每个都在从 48 维输入中提取一种"低级特征"。这一层很"宽"，因为原始传感器数据杂而多，需要大量神经元来并行捕捉各种基础模式： → 关节角度的相对关系、身体倾斜趋势、脚底接触状态…… 第二层 · 256 个神经元 "特征组合"  把第一层发现的低级特征组合成更高级的"模式"。神经元数量减半，因为已经滤掉噪声，开始形成有意义的组合： → "左前腿抬高 + 身体前倾" → 可能需要加速、"双脚同时触地" → 需要调整步态 第三层 · 128 个神经元 "决策压缩"  再压缩，形成高度抽象的"运动意图"表示。128 个数字浓缩了机器人的完整运动状态理解： → 准备好输出具体动作了——12 个关节各自该去什么位置 **为什么从宽到窄？** 就像写论文——先大量阅读（512），再归纳要点（256），最后凝练结论（128）。信息在传递中不断被提炼，噪声被滤掉，有用的模式被放大。这种"漏斗"结构是深度学习的经典设计。 

#### 什么是"激活函数"？

如果没有激活函数，三层网络本质上等价于一层（因为线性变换的线性变换还是线性的）。激活函数引入**非线性**，让网络能学到复杂的、非直线的映射关系。
ELU（隐藏层用） y x=0 

**特点：**正数区域直接通过（线性），负数区域平滑压缩到一个负值。 **作用：**让神经元能"关闭"不相关的信号（输出接近 0），同时保持梯度流畅，训练更稳定。 
tanh（Actor 输出层用） +1 -1 x=0 → y=0 

**特点：**把任意数字压缩到 [-1, +1] 范围内。 **作用：**关节位置目标有物理上下限，tanh 保证输出永远在合理范围内（-1 到 +1 再映射到实际关节角度）。 

#### 为什么分 Actor 和 Critic 两个分支？

这是 PPO 算法的核心设计，类比一下：
Actor（演员） "决定怎么动"  输入当前状态 → 输出 12 个关节的位置目标 就像一个运动员，根据当前身体状态决定"左膝弯曲 30°、右髋伸展 15° ……"。 **输出维度：12**（Z1 有 12 个关节，每个关节一个目标值） Critic（评论家） "评估当前状态好不好"  输入当前状态 → 输出 1 个分数（state value） 就像一个教练，看到运动员的姿势后判断"这个状态不错，打 8 分"或"要摔了，打 2 分"。 **输出维度：1**（一个标量分数，越高说明当前状态越好） 

训练时两者配合：**Actor 尝试动作 → Critic 打分 → 根据分数差距调整 Actor 的策略**。Actor 越来越会动，Critic 越来越会评估，两者共同进步。

#### 完整数据流：从传感器到关节动作
传感器数据 (~48维)  │ ├─ 关节位置 (12) ─ 每个关节当前弯了多少  │ ├─ 关节速度 (12) ─ 每个关节转多快  │ ├─ 上一步动作 (12) ─ 上次命令每个关节去哪  │ ├─ 基座线速度 (3) ─ 身体前后左右上下移动多快  │ ├─ 基座角速度 (3) ─ 身体翻滚/俯仰/偏航多快  │ ├─ 投影重力 (3) ─ 重力方向（判断倾斜）  │ └─ 高度扫描 (187) ─ 前方地面的高度图  ▼ Hidden 1 (512 neurons, ELU) ← 广泛提取低级特征  ▼ Hidden 2 (256 neurons, ELU) ← 组合成中级模式  ▼ Hidden 3 (128 neurons, ELU) ← 压缩为决策意图  ▼  ┌─────────────┴─────────────┐  ▼ ▼ Actor (tanh) Critic 12维关节目标 1维状态评分 范围 [-1,+1] 越高越好 

#### 这个网络有多大？
**** **** **** **** **** 

| 层 | 输入维度 | 输出维度 | 参数量（权重 + 偏置） | 说明 |
| --- | --- | --- | --- | --- |
| Input → Hidden 1 | 48 | 512 | 48×512 + 512 = 25,088 | 48 维传感器数据进去，512 维特征出来 |
| Hidden 1 → Hidden 2 | 512 | 256 | 512×256 + 256 = 131,328 | 压缩一半 |
| Hidden 2 → Hidden 3 | 256 | 128 | 256×128 + 128 = 32,896 | 再压缩一半 |
| Hidden 3 → Actor | 128 | 12 | 128×12 + 12 = 1,548 | 输出 12 个关节目标 |
| Hidden 3 → Critic | 128 | 1 | 128×1 + 1 = 129 | 输出 1 个状态评分 |
| 总计 | ~191,000 | 约 0.76 MB（非常轻量） |  |  |

 对比参考：GPT-2 有 1.5 亿参数，GPT-4 有上万亿参数。Z1 的网络只有 **~19 万参数**，非常小巧——因为四足 locomotion 的决策空间远比语言理解简单，不需要大模型。 这也是为什么 checkpoint 文件只有 6.8 MB（包含了 Actor、Critic、优化器状态等全部内容），JIT 导出的纯 Actor 仅 1.2 MB。 

## 4. 我们的训练 vs Origin：半官方半自建

Origin 提供了**骨架**（网络结构 + 基础训练流程），实际的**训练策略设计**和**所有自动化工具**均为自行搭建。
**** **** **** **** **** **** **** **** **** **** **** **** 

| 组成部分 | Origin 提供 | 我们自建 (z1-custom) |
| --- | --- | --- |
| 网络架构（三层 MLP 512-256-128） | 提供 | 原样沿用，未修改 |
| PPO 超参 | 提供 | 沿用基础配置，pipeline 中动态调 LR、entropy coef |
| 环境配置（地形、观测、终止条件） | 基础版 | 大幅改造：5 级地形 curriculum、新增观测项、termination 调优 |
| 奖励函数 | 基础版 | 大幅改造：新增 joint_mirror、feet_clearance、joint_deviation_legs 等 |
| 训练脚本 | train.py | 新增 train_multigpu.py（4 GPU 分布式训练） |
| Pipeline 自动化 | 不提供 | 全部自建：phase_orchestrator、embedded_monitor、config_generator、ppo_override、state_store |
| 5-Phase 训练计划 | 不提供 | 全部自建：z1_5phase_plan.yaml（P1 Bootstrap → P5 Full Terrain） |
| Sim2Sim / MuJoCo | 不提供 | 全部自建：mujoco_sim2sim.py、mujoco_manual.py |
| 视频录制 / 导出 | 基础 play.py | 新增 play_z1_video.py、export_jit.py、一键录制脚本 |
| 训练监控 / 分析 | 不提供 | 全部自建：train_monitor.py、train_analyzer.py、bestmodel_phase_sync.py |
| 部署工具 | 不提供 | 全部自建：robot_deploy.py |
| 训练权重 | 不提供 | 全部自行训练：21 个 .pt 文件，覆盖 P1–P4 |

## 总结
****``**** ******** ****``

| 网络结构从哪来？ | Origin 官方提供，三层 MLP (512→256→128)，Actor-Critic 架构，ELU 激活。定义在 rsl_rl_ppo_cfg.py。 |
| --- | --- |
| 训练权重从哪来？ | 全部自己训练。Origin 不提供任何 .pt 文件。 |
| 训练框架从哪来？ | Origin 提供基础骨架（train.py、env_cfg、rewards）。我们自建了全部自动化层（orchestrator、monitor、5-phase plan、sim2sim）。 |
| 别人 clone 后能复现吗？ | 能。Clone 父仓库 → git submodule update --init → 获得 z1-custom 分支（含所有自建工具）+ LFS 下载权重 → 即可播放/推理。不需要 origin 的原始分支。 |

Generated: 2026-05-19 | Source: `origin/feature/z1_12dof` vs `fork/z1-custom` comparison