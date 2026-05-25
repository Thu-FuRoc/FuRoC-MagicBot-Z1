# Z1 阻尼方案对照

目标是决定在推进到 Phase 4 之前，MuJoCo 应该继续使用当前的 sim2sim 特化策略，还是切回 Magiclab Z1 原生仓库更接近“描述文件默认值”的方案。
结论：先按原生推荐做对照验证 当前 MuJoCo 被动阻尼被代码清零 P3 当前 run 已过拟合，不应直接硬推到 P4  这里把“原生推荐”定义为：遵循 MagiclabRobotics 的 Z1 描述文件默认设置，不主动把 MuJoCo 的被动关节阻尼清零；同时保留 Z1 训练侧使用的 PD 增益，做一版干净对照。 Current MuJoCo Passive Damping = 0 

当前 sim2sim 在运行时覆盖 MuJoCo model，把 12 个腿部关节的 `dof_damping` 全部设为 `0.0`。
Native Z1 MJCF Passive Damping = 10 

原生 Z1 描述文件在 MJCF `<default>` 下声明了 `<joint damping="10"/>`。
P4 Gate 先验证再推进 

建议先录像对照 Isaac Lab / MuJoCo，并用原生阻尼方案复查一次，再决定是否从 `p3_model_7900.pt` 开新 P4 run。

## 方案总表
**** ````[](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/magiclab_rl_lab/sim2sim/mujoco_manual.py)[](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/magiclab_rl_lab/sim2sim/mujoco_humanoid_gym.py)[](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/magicbot-z1_description/mjcf/MAGICBOTZ1.xml)[](https://github.com/MagiclabRobotics/magicbot-z1_description/blob/master/mjcf/MAGICBOTZ1.xml) **** ``[](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/magiclab_rl_lab/source/magiclab_rl_lab/magiclab_rl_lab/assets/robots/magiclab.py)[](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/videos/p/p3/20260522_174009/params/deploy.yaml)[](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/magiclab_rl_lab/sim2sim/mujoco_manual.py) **** ````[](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/magiclab_rl_lab/sim2sim/mujoco_manual.py)[](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/magiclab_rl_lab/source/magiclab_rl_lab/magiclab_rl_lab/assets/robots/magiclab.py) **** ``[](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/magiclab_rl_lab/scripts/rsl_rl/play_z1_video.py)[](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/magiclab_rl_lab/sim2sim/mujoco_manual.py) **** ``````

| 项 | 当前实现 | 原生推荐 | 来源 / 证据 |
| --- | --- | --- | --- |
| MuJoCo 被动关节阻尼 | 清零model.dof_damping[jid] = 0.0 | 保留 MJCF 默认值不主动覆盖，沿用 damping="10" | 当前代码：mujoco_manual.py 第 671-672 行，
              mujoco_humanoid_gym.py 第 347-350 行。
              原生描述：MAGICBOTZ1.xml 第 44 行。
              GitHub：MagiclabRobotics/magicbot-z1_description |
| PD damping / kd | 启用[4,4,4,5,3,3] x 2 | 同样保留继续使用这组 Z1 训练/部署导出的腿部 PD damping | 资产配置：magiclab.py 第 121-138 行。
              部署导出：deploy.yaml 第 3-5 行。
              MuJoCo 读取：mujoco_manual.py 第 635-643 行。 |
| Armature | 运行时覆盖0.02863 hip/knee，0.01503 ankle | 保持一致这部分与训练资产一致，不是主要矛盾 | 当前 MuJoCo：mujoco_manual.py 第 674-677 行。
              训练资产：magiclab.py 第 127-138 行。 |
| 地形加载逻辑 | Isaac / MuJoCo 分开核对Isaac 录像取 run 内快照，MuJoCo 由 load_model_with_terrain() 注入 | 先做一一对照推进 P4 前先确认 P3 gentle terrain 在两侧都一致 | Isaac 录像：play_z1_video.py 第 103-128 行。
              MuJoCo 地形：mujoco_manual.py 第 191 行与第 648-651 行。 |
| P3 -> P4 推进方式 | 不要继续硬训同一个 P3 run当前 P3 已明显过拟合 | 新开 P4 run从 p3_model_7900.pt 初始化，但先完成视频与阻尼对照 | [bestmodel_legged.json](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/docs/tracking/bestmodel_legged.json)
              P3 best: 32.52 @ model_7900.pt
              P3 latest: -8.89 @ iter 10479 |

## 关键参数矩阵
````````````````````

| 关节组 | Stiffness | PD Damping / kd | Armature | 备注 |
| --- | --- | --- | --- | --- |
| Hip pitch / roll / yaw | 100 | 4 | 0.02863 | 当前部署与训练资产一致，问题不在这组数字本身。 |
| Knee | 150 | 5 | 0.02863 | 当前部署与训练资产一致。 |
| Ankle pitch / roll | 60 | 3 | 0.01503 | 当前部署与训练资产一致。 |
| MJCF passive damping | 不适用 | 10（MJCF 默认） | MJCF 自身定义 | 这是你现在与“原生推荐”最核心的差异项。 |

## 建议动作
 建议先采用原生推荐方案做对照，也就是在 MuJoCo 里保留 Z1 MJCF 默认被动阻尼，不再把 `dof_damping` 清零，然后与当前方案各录一版 P3 视频。 

- 对照 A：当前方案。MuJoCo 被动阻尼清零，PD `kd=[4,4,4,5,3,3,...]`。 
- 对照 B：原生推荐。保留 MJCF `damping="10"`，同时仍保留同一套 PD `kd`。 
- 两版都用同一个 `p3_model_7900.pt`、同一个 gentle terrain、同一组速度命令和相机位姿。 
- 如果 B 比 A 更稳，P4 就从 B 方案继续；如果 B 明显过阻尼，再保留 A，但要把这个偏差写入 sim2sim 基线说明。 

## 来源

- 本地 MJCF：[MAGICBOTZ1.xml](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/magicbot-z1_description/mjcf/MAGICBOTZ1.xml) 
- 本地 MuJoCo sim2sim：[mujoco_manual.py](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/magiclab_rl_lab/sim2sim/mujoco_manual.py)、[mujoco_humanoid_gym.py](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/magiclab_rl_lab/sim2sim/mujoco_humanoid_gym.py) 
- 本地训练资产：[magiclab.py](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/magiclab_rl_lab/source/magiclab_rl_lab/magiclab_rl_lab/assets/robots/magiclab.py) 
- 本地部署参数样例：[deploy.yaml](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/videos/p/p3/20260522_174009/params/deploy.yaml) 
- GitHub 仓库：[https://github.com/MagiclabRobotics](https://github.com/MagiclabRobotics) 
- GitHub Z1 描述文件：[magicbot-z1_description / MAGICBOTZ1.xml](https://github.com/MagiclabRobotics/magicbot-z1_description/blob/master/mjcf/MAGICBOTZ1.xml)