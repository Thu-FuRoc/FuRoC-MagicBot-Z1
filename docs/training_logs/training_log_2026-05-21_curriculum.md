# Training Log: Z1 12DOF Curriculum Training

**Date**: 2026-05-21
**Config**: v8_curriculum (single-pass terrain curriculum)
**Status**: Running

---

## 基本信息

| 项目 | 值 |
|------|------|
| 环境 | `Magiclab-Z1-12dof-Velocity-Curriculum` |
| 算法 | PPO (RSL-RL) |
| 起点权重 | 随机初始化（不加载 checkpoint） |
| GPUs | 4x RTX PRO 6000 (共享，与 p3_coarse 并行) |
| Envs | 4096 |
| Max Iterations | 30000 |
| Save Interval | 500 |
| Episode Length | 20s |
| dt / decimation | 0.002 / 10 |
| Fabric | **禁用** (`--disable_fabric`，避免与 p3_coarse 冲突) |

---

## 配置要点

### Terrain (5 类混合, curriculum=True)
| 类型 | 比例 | 参数 |
|------|------|------|
| flat | 0.3 | 默认平面 |
| random_grid | 0.2 | grid_width=0.6, height=0~0.4 |
| pyramid_stairs | 0.2 | step_height=0.05~0.2, step_width=0.3, platform_width=1.5 |
| boxes | 0.15 | box_height=0.05~0.2, platform_width=1.0 |
| gap | 0.15 | gap_width=0.1~0.3, platform_width=1.5 |

- `num_rows=10`, `max_init_terrain_level=0` (所有 env 从最简地形开始)
- `terrain_levels_vel` 自动按行走距离升降

### Commands (自动课程)
- 初始范围: `lin_vel_x=[-0.1, 0.1]`, `lin_vel_y=[-0.1, 0.1]`, `ang_vel_z=[-0.1, 0.1]`
- 极限范围: `lin_vel_x=[-0.5, 1.0]`, `lin_vel_y=[-0.5, 0.5]`, `ang_vel_z=[-1.0, 1.0]`
- `rel_standing_envs=0.3` (30% env 零速命令)
- `lin_vel_cmd_levels` + `ang_vel_cmd_levels` 自动扩展

### Rewards (统一权重)
- `track_lin_vel_xy=1.9`, `track_ang_vel_z=0.9`
- `alive=0.3` (双足冷启动需较高存活奖励)
- `base_height=-8.0`, `flat_orientation=-5.5`
- `action_rate_l1=-0.04`, `feet_clearance=1.0`
- 共 18 项 reward

### PPO 覆盖项
| 参数 | 值 |
|------|------|
| learning_rate | 1e-3 |
| entropy_coef | 0.01 |
| init_noise_std | 1.0 |
| num_steps_per_env | 24 |
| num_mini_batches | 8 |
| desired_kl | 0.016 |
| max_grad_norm | 0.5 |

---

## 跑通过程 (Troubleshooting)

### 问题 1: Terrain 参数错误
**错误**: `MeshPyramidStairsTerrainCfg.__init__() got an unexpected keyword argument 'platform_length'`

**原因**: IsaacLab 地形配置的参数名与直觉不同：
- `MeshPyramidStairsTerrainCfg`: 用 `platform_width`，不是 `platform_length`
- `MeshBoxTerrainCfg`: 只有 `box_height_range` 和 `platform_width`，没有 `box_size_range`
- `MeshGapTerrainCfg`: 用 `platform_width`，不是 `platform_length`

**修复**: 查阅源码 `~/IsaacLab/source/isaaclab/isaaclab/terrains/trimesh/mesh_terrains_cfg.py`，使用正确参数名。

### 问题 2: PhysX Fabric 接口冲突
**错误**: `RuntimeError: Failed to acquire interface: omni::physx::IPhysxFabric (pluginName: nullptr)`

**原因**: p3_coarse 训练（4 GPU, 使用 Fabric）已在运行，PhysX Fabric 接口被锁定，新进程无法获取。

**修复**:
1. 给 `train.py` 添加 `--disable_fabric` 参数支持
2. 修改 `scripts/rsl_rl/train.py`:
   - 添加 argparse: `--disable_fabric` flag
   - 在 env 创建前添加: `if args_cli.disable_fabric: env_cfg.sim.use_fabric = False`
3. 训练命令加上 `--disable_fabric`

### 问题 3: `--disable_fabric` 不存在于 train.py
**原因**: `play.py` 有此参数但 `train.py` 没有。

**修复** (sed 破坏语法后改用 Python 脚本):
```python
# 1. 添加参数 (在 --distributed 之后)
parser.add_argument(
    "--disable_fabric", action="store_true", default=False,
    help="Disable fabric and use USD I/O operations."
)

# 2. 在 env_cfg.sim.device 设置后添加
if args_cli.disable_fabric:
    env_cfg.sim.use_fabric = False
```

---

## 训练命令

### 验证测试 (64 envs, 100 iters) — 已通过
```bash
cd ~/magiclab_rl_lab && source ~/miniconda3/etc/profile.d/conda.sh && conda activate isaaclab && \
python scripts/rsl_rl/train.py \
    --task Magiclab-Z1-12dof-Velocity-Curriculum \
    --num_envs 64 --headless --max_iterations 100 \
    --agent_cfg scripts/cfgs/ppo_curriculum_30k.py \
    --disable_fabric
```

验证结果:
- 100 iters 无报错
- Mean reward: -1.84 (冷启动正常)
- bad_orientation 终止: 100% (预期内)
- terrain_levels: 0.0 (所有 env 仍在最简地形)
- lin_vel_cmd_levels: 0.1 (命令范围在初始值)

### 正式训练 (4096 envs, 30000 iters, 4 GPUs) — 运行中
```bash
cd ~/magiclab_rl_lab && source ~/miniconda3/etc/profile.d/conda.sh && conda activate isaaclab && \
nohup torchrun --nproc_per_node=4 --master_port=29503 \
    scripts/rsl_rl/train.py \
    --task Magiclab-Z1-12dof-Velocity-Curriculum \
    --num_envs 4096 --headless --distributed \
    --max_iterations 30000 \
    --agent_cfg scripts/cfgs/ppo_curriculum_30k.py \
    --disable_fabric \
    > /tmp/z1_curriculum_train.log 2>&1 &
echo "PID=$!"
```

> Note: `master_port=29503` 避免与 p3_coarse (29502) 冲突

---

## 当前并行训练状态

| 任务 | PID | 端口 | GPUs | Fabric | 脚本 |
|------|-----|------|------|--------|------|
| Z1 p3_coarse (5-phase) | 2952470 | 29502 | 4 | Yes | train_multigpu.py |
| Z1 Curriculum (新) | 3090451 | 29503 | 4 | **No** | train.py |
| BoosterK1 play (video) | 2958881 | - | 1 | - | play_k1_video_safe.py |

两个 Z1 训练共享 4 张 RTX 6000D (每张 85GB)，内存充裕。

---

## 监控命令

```bash
# 查看训练日志
tail -40 /tmp/z1_curriculum_train.log

# 查看 TensorBoard
tensorboard --logdir ~/magiclab_rl_lab/logs/rsl_rl/magiclab_z1_12dof_velocity_curriculum

# 检查进程是否还在
ps aux | grep 29503 | grep -v grep
```

---

## 监控指标

| 指标 | 期望趋势 | 说明 |
|------|----------|------|
| episode_reward | 上升 | 总 reward |
| episode_length | 趋近 1000 | 20s / (0.002*10) = 1000 steps |
| alive_rate | >80% | 前 1000 iter 应逐步上升 |
| terrain_levels | 逐步上升 | curriculum 自动提难度 |
| lin_vel_cmd | 逐步扩展 | 从 [-0.1, 0.1] 到 [-0.5, 1.0] |
| Value_loss | 下降 | critic 预测更准 |
| bad_orientation | 下降 | 从 100% 逐步降低 |

### 关键检查点
- **iter 500**: reward 应 > 0, alive_rate > 50%
- **iter 2000**: reward 稳步上升, terrain_level 开始增长
- **iter 5000**: reward 接近前 pipeline 同期水平
- **iter 10000**: 地形课程效果明显, 部分 env 进入高难度地形

---

## 设计要点

- **alive=0.3**: 双足从零冷启动需要较高存活奖励。如果前 1000 iter 存活率太低可提到 0.5
- **max_init_terrain_level=0**: 所有 env 从最简地形开始
- **rel_standing_envs=0.3**: 30% env 收到零速度命令，帮助先学站立
- **不需要 orchestrator，不需要 rollback，不需要手动阶段切换**
- **--disable_fabric**: 与 p3_coarse 并行时必须加此参数

---

## 文件清单

| 文件 | 路径 |
|------|------|
| Env Config | `source/.../z1/12dof/velocity_env_cfg_v8_curriculum.py` |
| Task Registration | `source/.../z1/12dof/__init__.py` |
| PPO Override | `scripts/cfgs/ppo_curriculum_30k.py` |
| train.py (已修改) | `scripts/rsl_rl/train.py` (+`--disable_fabric`) |
| Training Log | 本文件 |
| 日志 (服务器) | `/tmp/z1_curriculum_train.log` |
