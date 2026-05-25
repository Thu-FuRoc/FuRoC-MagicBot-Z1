# MagicBot Z1 Framework

> Consolidated project architecture for Z1 locomotion, source layout, automation pipeline, and local/remote artifact organization. 

---

## 1. Project Scope

This repo stack covers four linked areas:

- Isaac Lab locomotion training on RTX. 
- Z1 task and robot configuration inside `magiclab_rl_lab`. 
- Automation for multi-phase training and post-phase processing. 
- Local Windows-side organization of videos, docs, and models. 

---

## 2. High-Level Layout

```
magiclab_rl_lab/
├── source/magiclab_rl_lab/magiclab_rl_lab/
│   ├── assets/robots/
│   ├── tasks/locomotion/
│   └── utils/
├── scripts/
│   ├── rsl_rl/
│   └── automation/
├── sim2sim/
├── deploy/
├── training_plans/
└── logs/

```

### Remote RTX role

- Holds the runnable codebase. 
- Produces checkpoints, exported policies, phase configs, and remote video bundles. 
- Runs IsaacLab, MuJoCo recording, orchestrator, and Slurm jobs. 

### Local Windows role

- Holds mirrors, docs, labeled videos, and manually curated artifacts. 
- Receives fetched videos and organizes `models/`, `videos/`, and `docs/`. 

---

## 3. Core Source Areas

### `assets/robots/`

- Robot articulation configuration. 
- Main file: `magiclab.py`
- Defines initial pose, actuator gains, armature, and SDK joint order. 

### `tasks/locomotion/`

- Gym task registration. 
- Environment configuration. 
- MDP components such as rewards, observations, curriculums, and commands. 

### `scripts/rsl_rl/`

- Training and evaluation entrypoints. 
- Includes training, play, and video recording scripts. 

### `sim2sim/`

- MuJoCo-side validation and deployment playback. 

### `training_plans/`

- Multi-phase YAML plans for orchestrated runs. 

---

## 4. Z1 Locomotion Runtime Flow

```
velocity_env_cfg.py
  -> build scene / commands / rewards / observations
  -> register Magiclab-Z1-12dof-Velocity
  -> train.py or train_multigpu.py
  -> logs/rsl_rl/.../<run_dir>/model_*.pt
  -> export_jit.py -> exported/policy.pt
  -> play / sim2sim / video recording

```

### Main runtime files
``````````````

| Area | Main file |
| --- | --- |
| Robot config | assets/robots/magiclab.py |
| Environment | tasks/locomotion/robots/z1/12dof/velocity_env_cfg.py |
| PPO config | tasks/locomotion/agents/rsl_rl_ppo_cfg.py |
| Training | scripts/rsl_rl/train.py |
| Multi-GPU | scripts/rsl_rl/train_multigpu.py |
| Video play | scripts/rsl_rl/play_z1_video.py |
| Sim2sim | sim2sim/mujoco_manual.py |

---

## 5. Automation Architecture

### Main modules
``````````````

| Module | Responsibility |
| --- | --- |
| phase_orchestrator.py | Main event loop and phase transitions |
| phase_manager.py | Parse YAML and merge defaults/phase/sub-phase config |
| config_generator.py | Generate per-phase env overrides |
| ppo_override.py | Generate PPO override config |
| training_launcher.py | Launch train or torchrun |
| embedded_monitor.py | Poll TensorBoard and checkpoints |
| state_store.py | Persist orchestrator state |

### Generated runtime artifacts
``````````

| Artifact | Path |
| --- | --- |
| State file | orchestrator_state.json |
| Temp env cfg | tmp/phase_configs/<sub_phase>/velocity_env_cfg.py |
| Temp PPO cfg | tmp/phase_configs/<sub_phase>/ppo_override_cfg.py |
| Run logs | logs/train_<sub_phase>.log |
| Checkpoints | logs/rsl_rl/.../<run_dir>/model_*.pt |

### Phase lifecycle

```
pending
  -> generate env cfg and PPO cfg
  -> resolve starting checkpoint
  -> launch training
  -> monitor metrics and process liveness
  -> choose best checkpoint
  -> optional rollback / retry
  -> export policy and produce videos
  -> advance to next sub-phase

```

---

## 6. Local Artifact Organization

### Models

```
Magicbot_Z1/models/p/<phase>/

```

### Videos

```
Magicbot_Z1/videos/p/<fetch_timestamp>/<phase>/

```

### Tracking docs

```
Magicbot_Z1/docs/tracking/

```

### Notes

- Remote `tmp/phase_configs` is runtime-generated and reproducible. 
- Local fetched videos are labeled after download. 
- Raw local videos should be removed after successful labeled output. 

---

## 7. Recommended Reading

- RTX-side operations: [`RTX_Server_Guide.md`](/D:/Desktop_Files/GPU-Train/RTX6000/docs/RTX_Server_Guide.md) 
- `/gpu-train` commands: [`GPU_Train_Command_Reference.md`](/D:/Desktop_Files/GPU-Train/RTX6000/docs/GPU_Train_Command_Reference.md) 
- Z1 orchestrator usage: [`Z1_Orchestrator_Guide.md`](/D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/docs/guides/Z1_Orchestrator_Guide.md) 
- Z1 sim pipeline: [`gpu_train_sim_pipeline_light.html`](/D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/docs/guides/gpu_train_sim_pipeline_light.html) 
Generated from FRAMEWORK.md