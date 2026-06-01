# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RL locomotion training pipeline for MagicBot Z1 12DOF bipedal robot. Three parallel training strategies sharing a unified orchestrator + RTX server infrastructure:

| Strategy | Directory Prefix | Status |
|----------|-----------------|--------|
| A. Legged Gym | `A_legged_gym` | Done (p1–p3) |
| B. Custom Curriculum | `B_custom_curriculum` | In progress (p3_coarse done, p3_fine training) |
| C. AMP | `C_amp` | Planned |

## Common Commands

### Training (on RTX server via SSH)

Training runs on `phh@192.168.120.155` (VPN: iNode, conda env: `isaaclab`).

```bash
# Orchestrated pipeline via SLURM
sbatch scripts/z1_orchestrator.slurm          # B_custom (5-phase)
sbatch scripts/z1_orchestrator_legged_gym.slurm  # A_legged_gym (4-phase)

# Direct orchestrator (no SLURM)
python scripts/automation/phase_orchestrator.py \
    --plan config/pipeline/z1_custom_5phase_plan.yaml \
    --num-gpus 4 --poll-interval 120
```

### Video Recording (`--sim`)

The current recording script is `D:\Desktop_Files\GPU-Train\RTX6000\rtx_record_video.py` (one level above repo root).

```bash
python rtx_record_video.py --phase p3_coarse --yes
```

Output lands in `videos/{group}/{phase}/{YYYYMMDD_HHMM_modelXXXX}/` containing:
- `{phase}_{model}_isaaclab.mp4` (labeled video)
- `parameters/record_meta.json` + `sweep.json`
- `config_snapshot/deploy.yaml` + `velocity_env_cfg.py`

### Local Playback

```bash
python scripts/local_play_gui.py   # or: start_local_play_gui.bat
```

Tkinter GUI auto-discovers presets from `models/{A_legged_gym,B_custom_curriculum}/`. Controls: arrows=move, q/e=lateral, space=stop, esc=quit. JIT export runs automatically for unconverted checkpoints.

### Analysis

```bash
python scripts/analyze_sim_log.py <csv_path>    # MuJoCo CSV analysis
python scripts/plot_learning_curves.py --log_root <path> --output_dir <path>
python scripts/label_video.py <video> --run <phase> --model <model_stem>
```

## Architecture

### Orchestrator (plan-driven, strategy-agnostic)

`magiclab_rl_lab/scripts/automation/phase_orchestrator.py`

Two-level loop: **Phases** → **Sub-phases** (coarse/fine). For each sub-phase:
1. `config_generator.py` — three-layer merge: `defaults` → `phase` → `sub_phase` YAML
2. Swap env config at `source/magiclab_rl_lab/.../velocity_env_cfg.py`
3. Launch `torchrun` distributed PPO
4. Monitor for overfitting (5 signals: reward decline, policy collapse, action explosion, entropy collapse, value divergence)
5. Auto-rollback: LR×0.5 if reward drops < 95% of starting reward
6. Post-phase: JIT export → MuJoCo video → Isaac video → label videos → plots

State persisted in `orchestrator_state.json`. Can resume with `--resume`.

**Key:** The orchestrator is strategy-agnostic. The `--plan` YAML file selects which strategy to run. Plans live in `config/pipeline/`.

### Config Generation

`magiclab_rl_lab/scripts/automation/config_generator.py`

YAML plans have three layers:
```yaml
defaults:              # Shared across all phases
  training:
    num_envs_per_gpu: 1024
phases:
  p1:
    training:
      max_iterations: 3000
    sub_phases:
      coarse: {}       # Inherits p1 + defaults
      fine:
        training:
          max_iterations: 2000
```

PPO overrides use `--agent_cfg` with a temp file (never modifies the base agent config).

### Tracking System

`docs/tracking/bestmodel_phase.json` — main pipeline state (all strategies)
`docs/tracking/bestmodel_custom.json` — B_custom entries only
`docs/tracking/bestmodel_legged.json` — A_legged_gym entries only

Key field: `best_checkpoint_path` (NOT `best_model_path`). Status values: `PLANNED`, `RUNNING`, `COMPLETE`, `STOPPED`, `ARCHIVED`.

### Local Play GUI Preset Bindings

`scripts/local_play_gui.py` lines 65–78: `PRESET_RUNTIME_BINDINGS` maps preset names to `{phase, terrain, flat}` for auto-filling GUI fields. Two groups:
- `p1_coarse`/`p1_fine`/`p2_coarse`/`p2_fine`/`p3_coarse`/`p3_fine` → B_custom
- `p1`/`p2`/`p3`/`p4` → A_legged_gym

### Video Config

`config/video/video_record_targets_current.json` — B_custom recording targets
`config/video/video_record_targets_a_legged_gym.json` — A_legged_gym targets

Both are manifest-driven. `record_best_videos_remote.py` was the old batch recorder (deleted). Current recorder is `rtx_record_video.py`.

## Directory Conventions

```
models/{strategy}/{phase}/              # Checkpoints + JIT policies
  {phase}_model_{iter}.pt               # Raw checkpoint
  {phase}_policy.pt                     # JIT-exported policy

videos/{strategy}/{phase}/              # Demo videos
  {YYYYMMDD_HHMM_modelXXXX}/            # Date-time dirs per recording
    parameters/record_meta.json
    config_snapshot/deploy.yaml

plots/{strategy}/{phase}/               # Training analysis plots

docs/tracking/                          # bestmodel_*.json tracking files
docs/training_logs/                     # Training logs (Chinese, note the 's')
docs/github_readme/                     # README assets for GitHub
```

Strategies: `A_legged_gym`, `B_custom_curriculum`, `C_amp`

## Key Environment Config

Active env config: `source/magiclab_rl_lab/magiclab_rl_lab/tasks/locomotion/robots/z1/12dof/velocity_env_cfg.py`

The orchestrator swaps this file before each training run. Never edit it directly — it's generated.

## Submodules

| Submodule | Remote | Branch |
|-----------|--------|--------|
| `magiclab_rl_lab` | `phanghonghao/magiclab_rl_lab` | `z1-custom` |
| `magicbot-z1_description` | `phanghonghao/magicbot-z1_description` | `master` |
| `magicbot-z1_sdk` | `MagiclabRobotics/magicbot-z1_sdk` | `main` |

## RTX Server Paths

| Item | Path |
|------|------|
| Project root | `~/magiclab_rl_lab` |
| Training logs | `~/magiclab_rl_lab/logs/rsl_rl/magiclab_z1_12dof_velocity/` |
| Orchestrator state | `~/magiclab_rl_lab/orchestrator_state.json` |
| Play script | `~/magiclab_rl_lab/scripts/rsl_rl/play_z1_video.py` |
| SLURM logs | `~/magiclab_rl_lab/logs/slurm/` |

## Conventions

- Training logs in Chinese
- Bug fixes record root cause + fix, concisely
- User prefers full copy-paste-ready SSH commands over automated execution
- Attribute name: `best_checkpoint_path` (NOT `best_model_path`)
