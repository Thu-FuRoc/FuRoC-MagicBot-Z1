# FuRoC-MagicBot-Z1

RL locomotion training pipeline for **MagicBot Z1 12DOF bipedal robot**, built on Isaac Lab + rsl_rl.

## Pipeline Overview

> **5-phase curriculum learning** with terrain progression: Flat → Gentle → Intermediate → Rough → Full. Each phase resumes from the best checkpoint of the previous phase. 

## Demo

### P1–P2 Pipeline Demo

> P1 Coarse → P1 Fine → P2 Coarse → P2 Fine. Left column: Isaac Lab simulation. Right column: MuJoCo sim2sim validation. 

### P3 Gentle Terrain Walking

> **Left**: P3 Fine policy in Isaac Lab (gentle terrain). **Right**: Sim2sim transfer to MuJoCo — robot walks on flat ground in a different simulator. 

### P3b Intermediate Terrain

> P3b Fine policy deployed to MuJoCo. Trained on mixed terrain (flat + grid + stairs + boxes), successfully transfers to flat-ground sim2sim. 

## Results

### Curriculum Reward Trends

> Reward curves across sub-phases. P1 (flat terrain, bootstrap → standing), P2 (flat, velocity tracking). Each phase resumes from the best checkpoint of the previous phase. 

### P2 Fine Reward Decomposition

> **Left**: P2 Fine total reward trend. **Right**: Individual reward component decomposition — velocity tracking, orientation, base height, foot contact, action rate penalty, and torque penalty. 

### P3 Fine Results

> **Left**: P3 Fine total reward trend (gentle terrain). **Right**: Reward decomposition showing terrain adaptation components. 

### P3b Fine Results

> **Left**: P3b Fine total reward trend (intermediate terrain). **Right**: Reward decomposition with stairs/boxes adaptation. 

### Left-Right Joint Asymmetry

> Time-series of left (blue) vs right (red) joint angles. **Top row (P2 Fine, flat terrain)**: joints are roughly symmetric (offset < 0.03 rad). **Bottom row (P3 Coarse, gentle terrain)**: significant offset appears — hip pitch (−0.37 rad), hip yaw (−0.52 rad), knee pitch (+0.39 rad). 

> Quantitative comparison of left-right asymmetry across phases. P3 Coarse shows 10–20x larger mean offset than P2 Fine. **Root cause**: The reward function only penalizes each joint's deviation from its default position (`joint_deviation_l1`), but never enforces left-right correspondence. On flat terrain (P2) the optimal gait happens to be symmetric, but random terrain (P3) exposes this gap — PPO freely converges to an asymmetric local optimum where left and right legs use fundamentally different joint angles, yet still scores high reward. **Fix**: Add a symmetry reward term `|qpos_left - qpos_right|` or enable Isaac Lab's built-in `RslRlSymmetryCfg(use_mirror_loss=True)`. Can resume from current P3b Fine checkpoint without retraining from scratch. 

### Sim2Sim Gap: P3 Fine on Flat MuJoCo

> **P3 Fine policy (gentle terrain training) deployed to MuJoCo** — the robot repeatedly falls. Policies trained on rough terrain initially struggle on flat ground in a different simulator due to sim2sim physics gap. This motivated the P3b phase to bridge the gap. 

## Pre-trained Models
````````````````

| Phase | Policy | Path | Description |
| --- | --- | --- | --- |
| P1 Coarse | Standing | models/p/p1_coarse/p1_coarse_policy.pt | Bootstraps standing from random init |
| P1 Fine | Standing | models/p/p1_fine/p1_fine_policy.pt | Fine-tuned stable standing on flat terrain |
| P2 Coarse | Locomotion | models/p/p2_coarse/p2_coarse_policy.pt | Initial velocity tracking on flat terrain |
| P2 Fine | Locomotion | models/p/p2_fine/p2_fine_policy.pt | Fine-tuned velocity tracking with gait shaping |
| P3 Coarse | Terrain Walk | models/p/p3_coarse/p3_coarse_policy.pt | Gentle terrain walking (70% flat + 30% grid) |
| P3 Fine | Terrain Walk | models/p/p3_fine/p3_fine_policy.pt | Fine-tuned gentle terrain walking |
| P3b Coarse | Terrain Mix | models/p/p3b_coarse/p3b_coarse_policy.pt | Intermediate terrain (50% flat + 30% grid + 10% stairs + 10% boxes) |
| P3b Fine | Terrain Mix | models/p/p3b_fine/p3b_fine_policy.pt | Fine-tuned intermediate terrain walking |

## 5-Phase Automated Pipeline

Fully automated training pipeline with overfitting detection, auto-rollback, and phase advancement.

| Phase | Terrain | Key Goal | Sub-phases | Status |
| --- | --- | --- | --- | --- |
| P1 | Flat | Bootstrap standing | coarse → fine | Done ✅ |
| P2 | Flat | Velocity tracking | coarse → fine | Done ✅ |
| P3 | 70% flat + 30% gentle grid | Light terrain walking | coarse → fine | Done ✅ |
| P3b | 50% flat + 30% grid + 10% stairs + 10% boxes | Intermediate terrain | coarse → fine | Done ✅ |
| P4 | Flat + grid + stairs + gap + boxes | Rough terrain | coarse → fine | In progress 🔄 |
| P5 | Full terrain + rails | Complex + high speed | coarse → fine | Planned ⏳ |

Each sub-phase: config generation → distributed PPO training → overfitting detection → video recording → advance. Orchestrator auto-detects 5 failure signals (reward decline, policy collapse, action explosion, entropy collapse, value divergence) and rolls back if needed.

## Directory Structure

```
Magicbot_Z1/
├── magiclab_rl_lab/          # RL framework (fork, z1-custom branch)
├── magicbot-z1_description/  # URDF/Mesh (official)
├── magicbot-z1_sdk/          # Robot SDK (official)
├── configs/                  # Custom env configs & scripts
├── docs/
│   └── github_readme/        # Demo GIFs, plots & SVG for README
├── models/
│   └── p/                    # Pipeline policy checkpoints (Git LFS)
│       ├── p1_coarse/  p1_fine/
│       ├── p2_coarse/  p2_fine/
│       ├── p3_coarse/  p3_fine/
│       ├── p3b_coarse/ p3b_fine/
├── videos/                   # Training demo videos (Git LFS)
├── IsaacLab/                 # Isaac Lab framework (.gitignored)
└── README.md

```

## Submodules
``[](https://github.com/phanghonghao/magiclab_rl_lab) ````[](https://github.com/MagiclabRobotics/magicbot-z1_description) ``[](https://github.com/MagiclabRobotics/magicbot-z1_sdk) 

| Submodule | Source | Branch |
| --- | --- | --- |
| magiclab_rl_lab | phanghonghao/magiclab_rl_lab (fork) | z1-custom |
| magicbot-z1_description | MagiclabRobotics/magicbot-z1_description | main |
| magicbot-z1_sdk | MagiclabRobotics/magicbot-z1_sdk | main |

## Quick Start

### 1. Clone with submodules

```
git clone --recurse-submodules https://github.com/phanghonghao/FuRoC-MagicBot-Z1.git
cd FuRoC-MagicBot-Z1

```

### 2. Install Isaac Lab

```
# Isaac Lab must be installed separately (excluded from repo)
# See: https://isaac-sim.github.io/IsaacLab/
# Symlink into Magicbot_Z1/IsaacLab/

```

### 3. Train

```
cd magiclab_rl_lab
bash train_bash.sh

```

### 4. Evaluate / Record Video

```
# Play trained policy
python scripts/rsl_rl/play_z1_video.py --task=<version>

# Sim2sim (MuJoCo)
python sim2sim/mujoco_deploy.py --ckpt=<path_to_model>

# Deploy to robot
python deploy/robot_deploy.py

```

## Documentation

- [Training Plan](docs/Z1_Locomotion_Training_Plan.md) 
- [Training Analysis](docs/Z1_Training_Analysis.md) 
- [TODO & Naming Convention](docs/TODO.md) 
- [Framework Guide](docs/FRAMEWORK.md) 

## Hardware

- **GPU**: 4 × RTX 6000D (85 GB VRAM each) 
- **Training**: `torchrun` distributed PPO, 16,384 parallel envs (4,096/GPU) 
- **Throughput**: ~330K steps/s (4 GPUs) 
- **Framework**: Isaac Lab + rsl_rl 
Generated from README.md