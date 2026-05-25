# Magicbot_Z1 全仓库 Framework Map

这份文档不是 README 的复述，而是对当前 `Magicbot_Z1` 文件夹的实物梳理。重点区分源码、实验产物、录像、分析文档、远程操作脚本，以及哪些目录只是历史镜像或本地缓存。
当前仓库约 427 个文件 核心主线：IsaacLab 训练 + MuJoCo sim2sim + 本地资产整理 存在旧方案 / 新方案 / 镜像目录并存 README 仍混有旧的 5-phase 叙述  最重要的判断标准：**源码入口以 `magiclab_rl_lab/` 为主**，**本地实验资产以顶层 `models/`、`videos/`、`plots/`、`docs/` 为主**。顶层很多目录不是“可执行源码”，而是“结果组织层”。 Source Core magiclab_rl_lab 

真正的 RL 任务、训练脚本、自动化编排、sim2sim 和 deploy 逻辑都在这个子仓库里。
Asset Layer models / videos / plots 

顶层模型、录像、曲线和 PDF 报告是本地整理好的可读结果层，不是训练运行时代码本体。
Reference Stack IsaacLab + 官方 Z1 

`IsaacLab/` 提供仿真框架，`magicbot-z1_description/` 和 `magicbot-z1_sdk/` 提供官方资产和 SDK。
Ops Layer scripts / ops / docs 

训练监控、远程记录、GPU 网关、手册、追踪 HTML 都是项目的操作层。

## 1. 顶层目录总表
``````````````````````````````````````````````````````````````````````````````````````````````````````````

| 目录 / 文件 | 角色 | 现在应如何理解 | 关键内容 |
| --- | --- | --- | --- |
| magiclab_rl_lab/ | 核心源码子仓库 | 最重要。训练、录像、自动化、MuJoCo、deploy 全在这里。 | scripts/rsl_rl/、scripts/automation/、sim2sim/、deploy/、source/magiclab_rl_lab/ |
| IsaacLab/ | 仿真框架本体 | 上游 Isaac Lab 源码。项目依赖它，但业务逻辑不写在这里。 | isaaclab.bat、apps/、source/isaaclab/ |
| magicbot-z1_description/ | 官方机器人描述资产 | URDF / MJCF / meshes 来源。MuJoCo 和一些基线物理参数要以它为准。 | mjcf/MAGICBOTZ1.xml |
| magicbot-z1_sdk/ | 官方 SDK | 部署和真机控制的接口参考层。 | pybind、示例、关节结构定义 |
| models/ | 本地模型整理层 | 按方案族整理导出的 checkpoint / JIT policy，方便本地测试和录像。 | A_legged_gym/、B_custom_curriculum/、C_amp/ |
| videos/ | 本地录像资产层 | 同一策略的 IsaacLab / MuJoCo 对照、重录版本、相机试验都在这里。 | A_legged_gym/、B_custom_curriculum/、batch_best_20260523/、phase_best_rerecord* |
| plots/ | 本地训练分析层 | 按 run 生成的 4 张曲线 + PDF/MD/TEX 汇总，是 $plot-train-Z1 的主要本地产物目录。 | p1/、p2/、p3/、B_custom_curriculum/* |
| docs/ | 文档层 | 包含计划、手册、追踪、README 演示素材和旧分析报告。 | tracking/、guides/、manual_commands/、plans/ |
| scripts/ | 顶层本地工具层 | 偏 Windows 本地使用，负责取视频、画图、打标签、GUI、生成 PDF。 | record_best_videos_remote.py、plot_learning_curves.py、local_play_gui.py |
| logs/ | 本地日志镜像层 | 不是远端训练主日志，而是本地保留的行为日志、CSV、回放记录和归档。 | A_legged_gym/、B_custom_curriculum/、C_amp/ |
| configs/ | 顶层轻量配置层 | 目前主要存视频录制清单和一条 deploy 脚本，不是训练主配置库。 | video_record_targets_current.json |
| ops/ | 外围运维工具层 | 当前主要是 GPU gateway，不直接参与训练，但服务团队访问和管控。 | gpu_gateway/ |
| sim2sim/ | 顶层残留目录 | 几乎空。实际可用的 sim2sim 代码在 magiclab_rl_lab/sim2sim/。 | 当前仅见缓存残留 |
| training_plans/ | 顶层计划镜像 | 只有一个顶层 YAML。更完整、可执行的计划仍在 magiclab_rl_lab/training_plans/。 | z1_5phase_plan.yaml |
| best_models.json | 训练汇总状态 | 当前最关键的聚合指标文件，记录每个 run 的 peak/best/latest 和过拟合状态。 | 被 train_monitor.py 和 gen_report_pdf.py 消费 |

## 2. 当前最值得信任的主线

```
Magicbot_Z1 (本地整理层)
  ├─ magiclab_rl_lab/               真正源码和训练入口
  │   ├─ source/magiclab_rl_lab/    任务定义、机器人资产、MDP
  │   ├─ scripts/rsl_rl/            训练 / 播放 / 录像
  │   ├─ scripts/automation/        多阶段 orchestrator
  │   ├─ sim2sim/                   MuJoCo 验证
  │   ├─ deploy/                    真机部署
  │   └─ training_plans/            当前有效计划
  ├─ models/                        本地 checkpoint / policy 整理
  ├─ videos/                        IsaacLab / MuJoCo 录像整理
  ├─ plots/                         曲线和 PDF 报告
  ├─ docs/                          说明、追踪和历史报告
  └─ scripts/                       本地拉取/分析/GUI 工具
```

 如果你的问题是“某个功能真正在哪”，优先沿这条主线找。不要先看顶层 `sim2sim/`、不要先看旧 README 里的路径描述、也不要把本地录像目录误当成训练配置源码。 

## 3. 三条实验路线是什么
````````````````````````````

| 方案族 | 含义 | 本地目录 | 现状 |
| --- | --- | --- | --- |
| A_legged_gym | 更贴近社区 / 官方简化思路的 4-phase 风格方案 | models/A_legged_gym/、videos/A_legged_gym/、plots/p1..p3/ | 目前本地有 p1/p2/p3 三个 best model 和对应视频，P4 尚未形成有效本地产物。 |
| B_custom_curriculum | 自研 5-phase coarse/fine orchestrator 流水线 | models/B_custom_curriculum/、videos/B_custom_curriculum/、plots/B_custom_curriculum/ | 这是当前仓库里内容最完整的一条线，文档、曲线、录像和 deploy 参数都最齐。 |
| C_amp | 给未来 AMP / imitation / motion prior 预留的占位方案 | models/C_amp/、videos/C_amp/、plots/C_amp/、logs/C_amp/ | 目前更多是结构占位，还不是仓库里的主工作流。 |

## 4. `magiclab_rl_lab/` 子仓库详解
``[](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/magiclab_rl_lab/source/magiclab_rl_lab/magiclab_rl_lab/assets/robots/magiclab.py) ``[](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/magiclab_rl_lab/source/magiclab_rl_lab/magiclab_rl_lab/tasks/locomotion/robots/z1/12dof/velocity_env_cfg.py) ``````````````````````````````````````````[](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/magiclab_rl_lab/scripts/train_monitor.py) ````````````````````````

| 区域 | 代表文件 | 职责 |
| --- | --- | --- |
| source/magiclab_rl_lab/magiclab_rl_lab/assets/robots/ | magiclab.py | 定义 Z1 机器人资产、PD 增益、armature、关节名顺序，是训练和部署的物理参数核心来源之一。 |
| tasks/locomotion/robots/z1/12dof/ | velocity_env_cfg.py | 最核心的环境配置文件。场景、地形、指令范围、奖励、终止条件、事件和播放配置都从这里长出来。 |
| tasks/locomotion/mdp/ | rewards.py、observations.py、curriculums.py、commands/velocity_command.py | 把 locomotion 的 reward、观测、curriculum 和速度命令拆成可组合的 MDP 模块。 |
| tasks/locomotion/agents/ | rsl_rl_ppo_cfg.py | 定义 PPO 训练超参数，是 rsl_rl 训练入口读取的 agent config。 |
| scripts/rsl_rl/ | train.py、play.py、play_keyboard.py、play_z1_video.py、record_z1_batch.py | 训练、评估、录像的标准入口。你现在录像主线依赖的就是 play_z1_video.py。 |
| scripts/automation/ | phase_orchestrator.py、phase_manager.py、config_generator.py、training_launcher.py | 多阶段自动化训练框架。负责 phase/sub-phase 生命周期、checkpoint 继承、配置生成和失败恢复。 |
| scripts/train_monitor.py | train_monitor.py | 单 run / 多 run 的训练体检器，会生成 best_models.json 的关键指标。 |
| sim2sim/ | mujoco_manual.py、mujoco_humanoid_gym.py | MuJoCo 侧 replay / sim2sim 验证。当前很多 damping、terrain、recording 判断都在这里。 |
| deploy/ | robot_deploy.py | 真机部署层，读取 deploy 配置，把策略输送到 SDK 控制接口。 |
| training_plans/ | z1_5phase_plan.yaml、z1_4phase_plan_v2.yaml | 真正被 orchestrator 消费的 phase 计划文件。注意这里比顶层 training_plans/ 更权威。 |
| source/.../utils/ | export_deploy_cfg.py | 把训练中的关节参数导出成 deploy.yaml，是 sim2sim / deploy 对齐的重要桥梁。 |

## 5. 顶层 `scripts/` 的职责
[](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/scripts/record_best_videos_remote.py) ``[](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/scripts/plot_learning_curves.py) ``[](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/scripts/gen_report_pdf.py) ``[](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/scripts/local_play_gui.py) ````[](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/scripts/label_video.py) ````

| 文件 | 职责 | 它和子仓库的关系 |
| --- | --- | --- |
| record_best_videos_remote.py | 把 batch video manifest 和录制脚本同步到 RTX，再把视频和元数据拉回本地。 | 调用远端 magiclab_rl_lab/scripts/rsl_rl/record_z1_batch.py。 |
| plot_learning_curves.py | 本地/远端共用的 TensorBoard 曲线生成器。 | 被 $plot-train-Z1 的远端流程使用。 |
| gen_report_pdf.py | 基于 4 张 PNG 和 best_models.json 生成 PDF/TEX/MD 报告。 | 曲线分析的本地收尾器。 |
| local_play_gui.py | 本地 MuJoCo 播放 GUI，自动扫描 models/ 和 videos/ 里的 deploy 参数。 | 是实验资产层到 sim2sim 的本地交互入口。 |
| label_video.py | 给视频打参数水印、速度标签。 | 面向展示资产，不参与训练。 |
| plot_symmetry.py / plot_asymmetry.py | 偏专项分析，用于关节左右对称性诊断。 | 对应 B 路线里的 asymmetry 问题分析链。 |

## 6. 结果目录分别代表什么
``````````

| 目录 | 它装的东西 | 常见误解 |
| --- | --- | --- |
| models/ | 本地保留的 checkpoint / JIT policy，便于离线复现、录像和 sim2sim。 | 它不是远端 run 原目录，所以通常缺少完整 TensorBoard 事件和 params 快照。 |
| videos/ | 最终可展示视频、重录版本、试验相机版本、batch 抽取版本。 | 它不是唯一录像真源。很多视频只是从远端拷回来的副本。 |
| plots/ | 每个 run 的 4 图 + report PDF/TEX/MD。 | 它是分析结果，不是训练日志本身。 |
| logs/ | 本地的 CSV、测试记录、局部回放日志、历史实验归档。 | 不要把它和 RTX 服务器上的 logs/rsl_rl/... 混为一谈。 |

## 7. 文档层如何读
````````````

| 路径 | 职责 | 推荐用途 |
| --- | --- | --- |
| docs/tracking/ | 状态追踪与专项对比 | 看当前 best model、阻尼对照、terrain 加载状态、架构分歧。 |
| docs/guides/ | 操作导向文档 | 看 orchestrator、录像入口、sim2sim、policy viewer、日志架构。 |
| docs/manual_commands/ | 命令手册 | 找具体 CLI 或远端命令。 |
| docs/plans/ | 路线图和思路文档 | 理解设计意图和未来模块扩展。 |
| docs/github_readme/ | README 可视化素材 | 只适合演示，不适合判断当前真实状态。 |
| docs/training_logs/ | 历史记录与表格 | 查过去某天的训练和管线状态。 |

## 8. 配置层与“真源”关系
``````````````

| 配置项 | 真源 | 说明 |
| --- | --- | --- |
| 训练环境配置 | magiclab_rl_lab/source/.../velocity_env_cfg.py | 当前源码默认值在这里；历史录像则可能优先读 run-local params/velocity_env_cfg.py。 |
| PPO 超参数 | tasks/locomotion/agents/rsl_rl_ppo_cfg.py + orchestrator 生成的 override | 如果是多阶段流程，运行期会生成临时 PPO override。 |
| 录像批处理清单 | configs/video_record_targets_*.json | 规定录哪些 run / checkpoint 和输出文件名。 |
| Deploy / sim2sim 参数 | videos/.../params/deploy.yaml | 这里常常是最完整的“当时导出的真实部署参数快照”。 |
| 训练健康摘要 | best_models.json | 由 train_monitor.py 生成，是很多分析和判断的聚合入口。 |

## 9. 当前目录里最容易踩坑的地方

- **顶层 `sim2sim/` 不是主代码。** 真正可用的 MuJoCo 逻辑在 `magiclab_rl_lab/sim2sim/`。 
- **顶层 `training_plans/` 只有一个镜像计划。** 要看 orchestrator 真正执行的计划，优先去子仓库里的 `training_plans/`。 
- **README 和当前状态不完全一致。** 它仍偏向旧的 5-phase narrative，而本地资产已经并存 A/B/C 三条路线。 
- **`models/` 不等于原始 run 目录。** 本地整理后的模型常常缺少完整历史参数快照。 
- **`videos/` 里有很多“重录版本”。** 同一个策略可能有 oldcam / eye4m4_3 / track45 等多个机位试验版本。 

## 10. 对这个仓库最实用的心智模型

```
上游依赖层
  IsaacLab/ + 官方 Z1 描述/SDK

业务源码层
  magiclab_rl_lab/
    ├─ source/                 任务、机器人、MDP
    ├─ scripts/rsl_rl/         train / play / record
    ├─ scripts/automation/     orchestrator
    ├─ sim2sim/                MuJoCo 验证
    └─ deploy/                 真机部署

本地资产整理层
  models/ videos/ plots/ logs/

分析与运维层
  docs/ scripts/ ops/ best_models.json
```

 如果你后续让我继续梳理某个局部，我建议按这个顺序切：**先找业务源码层，再找本地资产层，再看文档层是否有历史说明**。这样最不容易被重复目录误导。