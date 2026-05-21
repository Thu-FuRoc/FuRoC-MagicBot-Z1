# 录制视频

> 推荐方式：直接使用 `D:/Desktop_Files/GPU-Train/RTX6000/rtx_record_video.sh`。
> 当前一键流程会在 RTX 远端录制 Isaac Lab + MuJoCo，然后自动 `scp` 回本地、自动打标签、并删除本地 raw 视频。
>
> MuJoCo 可以在训练时录制（2 min），Isaac Sim 必须在训练停止时录制（15-20 min）。

## Headless 渲染机器人不可见问题（已修复）

### 现象

Isaac Lab headless 模式录制视频时，机器人身体不可见。日志中出现：

```
[Warning] [omni.hydra.scene_delegate.plugin] Calling getBypassRenderSkelMeshProcessing
for prim /World/envs/env_0/Robot/pelvis/visuals/proto_mesh_id5 that has not been populated
```

### 根因

URDF converter 的 `ImportConfig` 没有 `set_make_instanceable()` 方法（MJCF converter 有）。
URDF importer 硬编码地将所有 visual link 的 `visuals` Xform prim 标记为 `instanceable = True`。
Headless 渲染管线（Hydra scene delegate）无法正确填充这些 prototype mesh 的几何数据，
导致机器人 mesh 不被渲染。

### 修复方式

在 `play_z1_video.py` 中 monkey-patch `UrdfConverter.__init__`，在 USD 文件写入磁盘后、
spawner 加载到 stage 之前，遍历并清除所有 `instanceable` 属性：

```python
import isaaclab.sim.converters.urdf_converter as _uc
_orig_uc_init = _uc.UrdfConverter.__init__
def _patched_uc_init(self, cfg):
    _orig_uc_init(self, cfg)
    try:
        from pxr import Usd as _Usd
        usd_path = str(self.usd_path)
        if os.path.exists(usd_path):
            stage = _Usd.Stage.Open(usd_path)
            count = 0
            for prim in stage.Traverse():
                if prim.IsInstanceable():
                    prim.SetInstanceable(False)
                    count += 1
            if count > 0:
                stage.GetRootLayer().Save()
                print(f"[INFO] USD post-process: cleared instanceable on {count} prims")
    except Exception as e:
        print(f"[WARN] USD post-process failed: {e}")
_uc.UrdfConverter.__init__ = _patched_uc_init
```

同时需要：
- `env_cfg.scene.robot.spawn.force_usd_conversion = True`（强制重新转换 USD）
- `env_cfg.sim.use_fabric = False`（禁用 Fabric，否则 headless 模式报 PhysX Fabric 接口错误）
- 清除 USD 缓存 `rm -rf /tmp/IsaacLab/usd_*`

### 已内置的位置

此修复已内置在以下文件中，无需手动操作：
- `scripts/play_z1_video.py`（本地版本）
- `magiclab_rl_lab/scripts/rsl_rl/play_z1_video.py`（远程部署版本，`rtx_record_video.sh` 使用）

### 验证

日志中应出现 `[INFO] USD post-process: cleared instanceable on 23 prims`，
且不再出现 `getBypassRenderSkelMeshProcessing for prim /World/envs/env_0/Robot/` 相关警告。
视频 MP4 中可见机器人身体。

---

## 前提：导出 JIT Policy

```bash
CHECKPOINT="logs/rsl_rl/magiclab_z1_12dof_velocity/<RUN_DIR>/model_<N>.pt"

python -u scripts/export_jit.py --checkpoint ${CHECKPOINT}
# 输出: <RUN_DIR>/exported/policy.pt
```

## 一键方式（推荐）

```bash
bash D:/Desktop_Files/GPU-Train/RTX6000/rtx_record_video.sh <RUN_DIR> <CHECKPOINT> [VIDEO_LENGTH] [VEL_X] [DURATION] [GPU_ID]
```

默认值：
- `VIDEO_LENGTH=1000`
- `VEL_X=0.3`
- `DURATION=20`
- `GPU_ID=auto`（自动选满足 `--idle` 规则的空闲卡）

示例（录制 p2 的 model_7900）：
```bash
bash D:/Desktop_Files/GPU-Train/RTX6000/rtx_record_video.sh \
    2026-05-21_08-15-14_p2 model_7900 1000 0.3 20
```

一键流程步骤：
1. 自动选择空闲 GPU
2. 确认 JIT export 存在（不存在则自动导出）
3. 远程录制 Isaac Lab 视频（~15-20 min，需空闲 GPU 的 cuda:0）
4. 等待 Kit 进程清理（避免 KVDB 锁冲突）
5. 远程录制 MuJoCo 视频（~2 min）
6. `scp` 下载视频 + params 到本地 `videos/p/<phase>/<timestamp>/`
7. 自动打标签、删除 raw 副本

## MuJoCo 录制（旧手动方式，仅保留参考）

```bash
POLICY="logs/rsl_rl/magiclab_z1_12dof_velocity/<RUN_DIR>/exported/policy.pt"
SAVE_NAME="p3b_coarse_model10500"

python -u sim2sim/mujoco_manual.py \
    --mjcf ~/magicbot-z1_description/mjcf/MAGICBOTZ1.xml \
    --policy ${POLICY} \
    --record /tmp/${SAVE_NAME}_mujoco.mp4 \
    --num_steps 1000 \
    --vel_x 0.3
```

下载到本地（旧手动方式）：

```bash
# 在本地 Windows 执行
scp phh@192.168.120.155:/tmp/p3b_coarse_model10500_mujoco.mp4 "D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/videos/p/p3b_coarse/"
```

## Isaac Sim 录制（旧手动方式，必须停止训练）

```bash
CHECKPOINT="logs/rsl_rl/magiclab_z1_12dof_velocity/<RUN_DIR>/model_<N>.pt"

python -u scripts/rsl_rl/play_z1_video.py \
    --checkpoint ${CHECKPOINT} \
    --video \
    --video_length 1000 \
    --headless \
    --num_envs 1 \
    --disable_fabric \
    --device cuda:<IDLE_GPU>
```

> 注意：`--disable_fabric` 是 headless 渲染必需的参数（禁用 PhysX Fabric 接口）。
> `--video` 会自动启用 camera 和 USD instanceable 修复。

视频输出：`<RUN_DIR>/videos/play/rl-video-step-0.mp4`

下载到本地（旧手动方式）：

```bash
scp phh@192.168.120.155:~/magiclab_rl_lab/logs/rsl_rl/magiclab_z1_12dof_velocity/<RUN_DIR>/videos/play/rl-video-step-0.mp4 \
    "D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/videos/p/p3b_coarse/p3b_coarse_isaaclab.mp4"
```

## 下载训练参数（旧手动方式）

```bash
# 本地 Windows 执行
scp -r phh@192.168.120.155:~/magiclab_rl_lab/logs/rsl_rl/magiclab_z1_12dof_velocity/<RUN_DIR>/params/ \
    "D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/videos/p/p3b_coarse/params/"
```

## 加标签（旧手动方式，本地执行）

```bash
LABEL_SCRIPT="D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/scripts/label_video.py"
VIDEO="D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/videos/p/p3b_coarse/p3b_coarse_mujoco.mp4"

python "$LABEL_SCRIPT" "$VIDEO" \
    --model model_10500 \
    --run p3b_coarse \
    --reward 28.53 \
    --terrain intermediate \
    --iteration 10500 \
    --action-mean 0.65

# 覆盖原文件
mv "${VIDEO%.mp4}_labeled.mp4" "$VIDEO"
```
