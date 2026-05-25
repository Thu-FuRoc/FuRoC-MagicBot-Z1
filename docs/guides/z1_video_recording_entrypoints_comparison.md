# Z1 Video Recording Entrypoints Comparison

## Current Recording Version Used In This Round

The version just used in the latest successful rerecord is:

- Primary playback script: [play_z1_video.py](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/magiclab_rl_lab/scripts/rsl_rl/play_z1_video.py:1)
- Batch remote/local orchestration entry: [record_best_videos_remote.py](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/scripts/record_best_videos_remote.py:1)
- Remote batch worker: [record_z1_batch.py](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/magiclab_rl_lab/scripts/rsl_rl/record_z1_batch.py:1)

Remarks:

- This is the current validated static-camera rerecord pipeline.
- Camera mode:
  - `--no_camera_track`
  - `eye=(4,-4,3)`
  - `target=(0,0,0)`
- Playback framework:
  - IsaacLab script layer
  - Isaac Sim 4.5.0.0 runtime / renderer underneath
- Environment config behavior:
  - prefer historical run-local `params/velocity_env_cfg.py`
  - fall back to current source config only if the historical file is missing

## Conceptual Distinction

For current Z1 recording, "IsaacLab" and "Isaac Sim" are not two separate competing recording modes here:

- IsaacLab provides the task/env/script layer
- Isaac Sim provides the actual simulator and renderer

So the current recording can be described as:

- "IsaacLab recording"
- or "Isaac Sim rendered recording launched by IsaacLab"

Both are accurate.

## Entrypoint Comparison

| Entrypoint | Type | Main Purpose | Records What | Batch | Auto SCP Back | Current Recommended | Notes |
|---|---|---|---|---|---|---|---|
| [play_z1_video.py](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/magiclab_rl_lab/scripts/rsl_rl/play_z1_video.py:1) | Python | Main current Z1 playback/recording script | IsaacLab / Isaac Sim MP4 | No | No | Yes | Current primary script. Supports static camera, camera tracking toggle, warmup, run-local env config loading, headless visibility fixes. |
| [play_z1_video_legacy_6ffbe57.py](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/magiclab_rl_lab/scripts/rsl_rl/play_z1_video_legacy_6ffbe57.py:1) | Python | Legacy playback script | IsaacLab / Isaac Sim MP4 | No | No | No | Older fallback for historical comparison. Lacks current fixes. |
| [record_z1_batch.py](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/magiclab_rl_lab/scripts/rsl_rl/record_z1_batch.py:1) | Python | Remote batch recording from manifest | IsaacLab / Isaac Sim MP4 | Yes | No | Yes | New batch worker. Runs on RTX and copies outputs into a remote target folder. |
| [record_best_videos_remote.py](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/scripts/record_best_videos_remote.py:1) | Python | Local sync + remote run + SCP back | IsaacLab / Isaac Sim MP4 | Yes | Yes | Yes | New top-level convenience entrypoint. This is the one used in the latest batch rerecords. |
| [mujoco_manual.py](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/sim2sim/mujoco_manual.py:1) | Python | MuJoCo local/remote sim2sim playback and recording | MuJoCo MP4 | No | No | Depends | Separate path from IsaacLab/Isaac Sim. Useful for sim2sim playback. |
| [mujoco_record_fixed.py](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/sim2sim/mujoco_record_fixed.py:1) | Python | Fixed-velocity MuJoCo recording wrapper | MuJoCo MP4 | No | No | Depends | Convenience wrapper over `mujoco_manual.py`. |
| [rtx_record_video.sh](D:/Desktop_Files/GPU-Train/RTX6000/rtx_record_video.sh:1) | Shell | One-shot remote recording pipeline | IsaacLab MP4 + MuJoCo MP4 | No | Yes | Legacy-useful | Older all-in-one shell flow. Includes download and labeling. |
| [rtx_submit_batch_record.sh](D:/Desktop_Files/GPU-Train/RTX6000/rtx_submit_batch_record.sh:1) | Shell | Submit remote batch recording job | IsaacLab MP4 + MuJoCo MP4 | Yes | Indirect | Legacy-useful | Batch submission wrapper around remote worker scripts. |
| [rtx_fetch_batch_recordings.sh](D:/Desktop_Files/GPU-Train/RTX6000/rtx_fetch_batch_recordings.sh:1) | Shell | Pull remote batch recordings back | Download / label only | Yes | Yes | Legacy-useful | Fetch-only stage for the older batch shell workflow. |
| [rtx_batch_record_worker_remote.sh](D:/Desktop_Files/GPU-Train/RTX6000/rtx_batch_record_worker_remote.sh:1) | Shell | Remote batch worker | IsaacLab MP4 + MuJoCo MP4 | Yes | No | Legacy-useful | Older remote worker used by the shell batch pipeline. |

## Practical Grouping

### 1. Current main IsaacLab / Isaac Sim route

- [play_z1_video.py](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/magiclab_rl_lab/scripts/rsl_rl/play_z1_video.py:1)
- [record_z1_batch.py](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/magiclab_rl_lab/scripts/rsl_rl/record_z1_batch.py:1)
- [record_best_videos_remote.py](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/scripts/record_best_videos_remote.py:1)

Use this route when:

- you want the current validated static-camera setup
- you want historical run-local env config loading
- you want the headless visibility fixes
- you want simple batch rerecord + SCP back

### 2. Older shell pipeline

- [rtx_record_video.sh](D:/Desktop_Files/GPU-Train/RTX6000/rtx_record_video.sh:1)
- [rtx_submit_batch_record.sh](D:/Desktop_Files/GPU-Train/RTX6000/rtx_submit_batch_record.sh:1)
- [rtx_fetch_batch_recordings.sh](D:/Desktop_Files/GPU-Train/RTX6000/rtx_fetch_batch_recordings.sh:1)
- [rtx_batch_record_worker_remote.sh](D:/Desktop_Files/GPU-Train/RTX6000/rtx_batch_record_worker_remote.sh:1)

Use this route when:

- you need the older combined IsaacLab + MuJoCo shell workflow
- you want compatibility with prior archived batch scripts

### 3. MuJoCo-only route

- [mujoco_manual.py](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/sim2sim/mujoco_manual.py:1)
- [mujoco_record_fixed.py](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/sim2sim/mujoco_record_fixed.py:1)

Use this route when:

- you specifically want MuJoCo playback/recording
- you are not trying to reproduce the IsaacLab/Isaac Sim rendered videos

## File Count Summary

Directly relevant recording entrypoints currently tracked in this document:

- Python files: 6
- Shell files: 4

## Latest Batch Rerecords That Used The Current Version

### B custom curriculum batch

- [videos/batch_best_20260523](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/videos/batch_best_20260523)

### A legged gym batch

- [videos/A_legged_gym/20260523_rerecord](D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/videos/A_legged_gym/20260523_rerecord)

