# Z1 Video Recording Current Baseline

## Purpose

This document records the currently validated IsaacLab video-recording setup for Z1 so future recordings can reproduce the same result without re-guessing camera or terrain behavior.

Confirmed on 2026-05-23.

## Current Correct Recording Scheme

- Framework: IsaacLab / Isaac Sim headless offscreen recording
- Script: [play_z1_video.py](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/magiclab_rl_lab/scripts/rsl_rl/play_z1_video.py:1)
- Remote host: `phh@192.168.120.155`
- Conda env: `isaaclab`
- Isaac Sim: `4.5.0.0`
- IsaacLab package: `0.47.2`

## Camera

Use a static camera, not camera tracking.

- Flag: `--no_camera_track`
- Static camera pose:
  - `eye=(4, -4, 3)`
  - `target=(0, 0, 0)`

Reference:
- [play_z1_video.py](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/magiclab_rl_lab/scripts/rsl_rl/play_z1_video.py:361)

## Terrain Loading Rule

The recording script now prefers the historical env config saved next to the checkpoint:

- `<run_dir>/params/velocity_env_cfg.py`

Only if that file is missing does it fall back to the current source env config.

Reference:
- [play_z1_video.py](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/magiclab_rl_lab/scripts/rsl_rl/play_z1_video.py:96)

This matters because:

- Historical `p2_fine` uses plane terrain:
  - [p2_fine params velocity_env_cfg.py](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/videos/B_custom_curriculum/p2_fine/params/velocity_env_cfg.py:50)
  - `terrain_type="plane"`
  - `terrain_generator=None`
- Current source config uses generator terrain with materialized tiles:
  - [current source velocity_env_cfg.py](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/magiclab_rl_lab/source/magiclab_rl_lab/magiclab_rl_lab/tasks/locomotion/robots/z1/12dof/velocity_env_cfg.py:47)

## Visual Ground Note

Plane terrain and visual material are different things.

- `terrain_type="plane"` means the physical ground is flat.
- The visible floor pattern depends on whether a `visual_material` is bound.

In the validated `p2_fine` historical config:

- The ground is physically flat.
- No custom `visual_material` is specified in the saved params file.
- So IsaacLab/Isaac Sim uses its default plane appearance, which can look like a gray grid.

This is different from the older gray noisy look:

- Same possible flat physics
- Different visible surface material / texture impression

So if the floor looks like square tiles, that does not by itself mean terrain loading is wrong.

## Headless Visibility Fixes Kept In Script

The current recording script keeps the rendering fixes that were needed for headless visibility:

- monkey-patch `UrdfConverter`
- clear USD `instanceable`
- clear `/tmp/IsaacLab/usd_*`
- force USD reconversion:
  - `env_cfg.scene.robot.spawn.force_usd_conversion = True`

Reference:
- [play_z1_video.py](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/magiclab_rl_lab/scripts/rsl_rl/play_z1_video.py:309)

## Validated Recording Command

Example for `p2_fine` at `model_3600.pt`:

```bash
ssh phh@192.168.120.155 "source ~/miniconda3/etc/profile.d/conda.sh && conda activate isaaclab && cd ~/magiclab_rl_lab && python -u scripts/rsl_rl/play_z1_video.py --checkpoint ~/magiclab_rl_lab/logs/rsl_rl/magiclab_z1_12dof_velocity/2026-05-18_19-35-30_p2_fine/model_3600.pt --video --video_length 200 --headless --num_envs 1 --device cuda:0 --no_camera_track"
```

## Local Output Paths

Validated kept videos:

- [p1_coarse_model_2900_isaaclab_eye4m4_3.mp4](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/videos/phase_best_rerecord_eye4m4_3/p1_coarse_model_2900_isaaclab_eye4m4_3.mp4)
- [p2_fine_model_3600_isaaclab_eye4m4_3.mp4](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/videos/phase_best_rerecord_eye4m4_3/p2_fine_model_3600_isaaclab_eye4m4_3.mp4)

## SCP Back To Local

Example:

```bash
scp phh@192.168.120.155:~/magiclab_rl_lab/logs/rsl_rl/magiclab_z1_12dof_velocity/2026-05-18_19-35-30_p2_fine/videos/play/rl-video-step-0.mp4 D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/videos/phase_best_rerecord_eye4m4_3/p2_fine_model_3600_isaaclab_eye4m4_3.mp4
```

## Practical Conclusion

If the goal is to reproduce the currently accepted result, keep all of the following fixed:

- use `play_z1_video.py`
- use `--no_camera_track`
- keep static view `eye=(4,-4,3), target=(0,0,0)`
- prefer historical run-local `params/velocity_env_cfg.py`
- keep headless visibility fixes and forced USD reconversion

