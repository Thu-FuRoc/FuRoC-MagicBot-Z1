# FuRoC-MagicBot-Z1

RL locomotion training pipeline for **MagicBot Z1 12DOF bipedal robot**, built on Isaac Lab + rsl_rl.

Three parallel training tracks:

| Track | Method | Status |
| --- | --- | --- |
| **A. Legged Gym** | Baseline PPO on flat/rough terrain | Done |
| **B. Custom Curriculum** | 5-phase curriculum (Flat → Gentle → Stairs) | P3 in progress |
| **C. AMP** | Adversarial Motion Priors | Planned (separate branch) |

---

## A. Legged Gym (Baseline)

Standard PPO training using legged_gym default configs. No curriculum, no terrain progression.

![Legged Gym P1-P3 Demo](docs/github_readme/A_legged_gym/legged_gym_p1_p2_p3.gif)

| Phase | Terrain | Best Reward | Status |
| --- | --- | --- | --- |
| P1 | Flat | 7.23 | Done ✅ |
| P2 | Flat | 28.09 (overfitting) | Done ✅ |
| P3 | Rough terrain | 32.52 (overfitting) | Done ✅ |

Pre-trained policies: `models/A_legged_gym/p{1,2,3}/`

---

## B. Custom Curriculum (Main)

5-phase automated curriculum pipeline. Each phase resumes from the best checkpoint of the previous phase.

![Pipeline Flow](docs/github_readme/B_custom_curriculum/pipeline_flow.svg)

### Pipeline Overview

| Phase | Terrain | Key Goal | Sub-phases | Status |
| --- | --- | --- | --- | --- |
| P1 | Flat | Bootstrap standing | coarse → fine | Done ✅ |
| P2 | Flat | Velocity tracking | coarse → fine | Done ✅ |
| P3 | Gentle terrain (flat + random grid) | Terrain walking | coarse → fine | Coarse done ✅ · Fine in progress 🔄 |
| P4 | Stairs (flat + stairs + random grid) | Stair climbing | coarse → fine | Pending |

### Demo

**P1–P2 Pipeline Demo** — P1 Coarse → P1 Fine → P2 Coarse → P2 Fine. Left: Isaac Lab simulation. Right: MuJoCo sim2sim validation.

![P1-P2 Pipeline Demo](docs/github_readme/B_custom_curriculum/pipeline_p1p2_demo.gif)

### Pre-trained Models

| Phase | Policy | Path | Best Reward | Description |
| --- | --- | --- | --- | --- |
| P1 Coarse | Standing | `models/B_custom_curriculum/p1_coarse/p1_coarse_policy.pt` | 15.61 | Bootstraps standing from random init |
| P1 Fine | Standing | `models/B_custom_curriculum/p1_fine/p1_fine_policy.pt` | 5.54 | Fine-tuned stable standing on flat terrain |
| P2 Coarse | Locomotion | `models/B_custom_curriculum/p2_coarse/p2_coarse_policy.pt` | 33.11 | Initial velocity tracking on flat terrain |
| P2 Fine | Locomotion | `models/B_custom_curriculum/p2_fine/p2_fine_policy.pt` | 38.21 | Fine-tuned velocity tracking with gait shaping |
| P3 Coarse | Terrain Walk | — | 51.70 | Gentle terrain (90% flat + 10% grid) · JIT pending |
| P3 Fine | Terrain Walk | — | *Training* | Fine-tuned gentle terrain (85% flat + 15% grid) · In progress |
| P4 Coarse | Stair Climb | — | *Pending* | Stair terrain intro (60% flat + 40% stairs) |
| P4 Fine | Stair Climb | — | *Pending* | Stair mastery (40% flat + 50% stairs + 10% grid) |

### Reward Trends

| P1 Coarse | P1 Fine |
| --- | --- |
| ![P1 Coarse](docs/github_readme/B_custom_curriculum/reward_trend_p1_coarse.png) | ![P1 Fine](docs/github_readme/B_custom_curriculum/reward_trend_p1_fine.png) |

| P2 Coarse | P2 Fine |
| --- | --- |
| ![P2 Coarse](docs/github_readme/B_custom_curriculum/reward_trend_p2_coarse.png) | ![P2 Fine](docs/github_readme/B_custom_curriculum/reward_trend_p2_fine.png) |

| P3 Coarse | P3 Fine |
| --- | --- |
| ![P3 Coarse](docs/github_readme/B_custom_curriculum/reward_trend_p3_coarse.png) | *Training in progress...* |

| P4 Coarse | P4 Fine |
| --- | --- |
| *Pending* | *Pending* |

### Automated Pipeline

Each sub-phase: config generation → distributed PPO training → overfitting detection → video recording → advance. Orchestrator auto-detects 5 failure signals (reward decline, policy collapse, action explosion, entropy collapse, value divergence) and rolls back if needed.

---

## C. AMP (Adversarial Motion Priors)

> AMP training is being developed on a separate branch and will be merged when ready. This section will be updated with demos, results, and pre-trained models after merge.

---

## Directory Structure

```
Magicbot_Z1/
├── magiclab_rl_lab/          # RL framework (fork, z1-custom branch)
├── magicbot-z1_description/  # URDF/Mesh (official)
├── magicbot-z1_sdk/          # Robot SDK (official)
├── config/                   # Pipeline configs
├── docs/
│   └── github_readme/        # README assets
│       ├── A_legged_gym/     # Track A demos
│       ├── B_custom_curriculum/  # Track B demos, plots & pipeline SVG
│       └── C_amp/            # Track C (placeholder)
├── models/
│   ├── A_legged_gym/         # Legged Gym policies
│   └── B_custom_curriculum/  # Curriculum pipeline policies
├── videos/                   # Training demo videos (Git LFS)
├── IsaacLab/                 # Isaac Lab framework (.gitignored)
└── README.md
```

## Submodules

| Submodule | Source | Branch |
| --- | --- | --- |
| magiclab_rl_lab | [phanghonghao/magiclab_rl_lab](https://github.com/phanghonghao/magiclab_rl_lab) | z1-custom |
| magicbot-z1_description | [MagiclabRobotics/magicbot-z1_description](https://github.com/MagiclabRobotics/magicbot-z1_description) | main |
| magicbot-z1_sdk | [MagiclabRobotics/magicbot-z1_sdk](https://github.com/MagiclabRobotics/magicbot-z1_sdk) | main |

## Quick Start

### 1. Clone with submodules

```bash
git clone --recurse-submodules https://github.com/phanghonghao/FuRoC-MagicBot-Z1.git
cd FuRoC-MagicBot-Z1
```

### 2. Install Isaac Lab

```bash
# Isaac Lab must be installed separately (excluded from repo)
# See: https://isaac-sim.github.io/IsaacLab/
# Symlink into Magicbot_Z1/IsaacLab/
```

### 3. Train

```bash
cd magiclab_rl_lab
bash train_bash.sh
```

### 4. Evaluate / Record Video

```bash
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
- **Training**: `torchrun` distributed PPO, 4096 parallel envs (1024/GPU)
- **Framework**: Isaac Lab + rsl_rl
