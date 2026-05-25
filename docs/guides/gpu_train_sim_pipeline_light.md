GPU Train · Light HTML 

# `/gpu-train --sim` 当前工作 Pipeline

 这张图现在对应已经修正后的实际 `--sim` pipeline。 结构仍然保持“远端录制 → scp 回本地 → 本地立刻打标”， 只是把默认参数、idle GPU 选择、自动下载和自动清理 raw 全部补齐了。 
输入模式 `--best <VERSION>` 或 `--checkpoint <PATH>`远端平台 RTX 6000D · `phh@192.168.120.155` · env=`isaaclab`核心输出 Isaac Lab MP4 + MuJoCo MP4 + 可选本地标签与图表 当前差异 默认值与下载/打标链路已按当前要求修正 

## 实际执行流

 下面这一列对应当前仓库里已经修正过的实际落地实现： `rtx_record_video.sh`。 
1 

### 解析输入

先确定远端 run 和 checkpoint。当前一键脚本仍以 `<RUN_DIR> + <CHECKPOINT>` 为入口，保持原来的远端录制结构。
文档支持 脚本本体吃 RUN_DIR + CHECKPOINT 2 

### 远端 GPU 健康检查

先通过 SSH 执行 `nvidia-smi`，确认 RTX 侧 GPU 可用。失败时整条录制流程直接中止。
ssh phh@192.168.120.155 "nvidia-smi --query-gpu=name,memory.free --format=csv,noheader" 脚本自动 3 

### 补齐或复用 JIT policy

脚本会检查 `<run_dir>/exported/policy.pt` 是否已存在。没有就调用 `scripts/export_jit.py` 导出；有就直接复用。
python -u scripts/export_jit.py --checkpoint logs/rsl_rl/<RUN_DIR>/<CHECKPOINT>.pt --output logs/rsl_rl/<RUN_DIR>/exported/policy.pt 脚本自动 4 

### 录制 Isaac Lab 视频

通过 `play_z1_video.py` 在 RTX 侧 headless 录制 Isaac Lab 视频。默认改为 `video_length=1000`，显卡不再写死 `cuda:0`，而是自动选一张符合 `--idle` 规则的空闲卡；同时增加 `timeout 600s`，避免异常 run 一直挂住。必须加 `--disable_fabric`，否则 PhysX Fabric 插件会因版本不兼容导致启动失败。
timeout 600s python -u scripts/rsl_rl/play_z1_video.py --checkpoint <CKPT_PATH> --headless --video --video_length 1000 --num_envs 1 --disable_fabric --device cuda:<IDLE_GPU> 脚本自动 GPU 自动按 idle 规则选择 Isaac timeout 600s 5 

### 等待 Kit 清理后再录 MuJoCo

Isaac 录制结束后，脚本会先等待 Kit 相关进程退出，避免 KVDB lock 一类冲突；等待上限是 `60s`，超时后会强制清理残留 Kit。之后再调用 `sim2sim/mujoco_manual.py` 远端录制 MuJoCo，默认参数是 `duration=20`、`vel_x` 取 env 配置的速度范围中值（`lin_vel_x=[0.0, 1.0]` → `0.5`），按 50Hz 折算为 `num_steps=1000`，并增加 `timeout 300s`。
wait_for_kit_cleanup() # up to 60s, force-kill stale Kit if neededtimeout 300s python -u sim2sim/mujoco_manual.py --mjcf ~/magicbot-z1_description/mjcf/MAGICBOTZ1.xml --policy <POLICY_PATH> --deploy_cfg <DEPLOY_CFG_PATH> --record /tmp/<RUN>_<CKPT>_mujoco.mp4 --num_steps 1000 --vel_x 0.5 脚本自动 Kit cleanup 60s MuJoCo timeout 300s 远端 RTX 录制 6 

### 自动 scp 回本地

录制完成后，脚本会自动把 Isaac Lab 视频、MuJoCo 视频，以及对应的 `params/` 目录一起拉回本地，不再停在“打印 scp 命令”这一步。
scp remote:Isaac.mp4 -> local rawscp remote:MuJoCo.mp4 -> local rawscp -r remote:params/ -> local params/ 脚本自动 7 

### 下载后立刻打标签并删除 raw

`label_video.py` 现在属于 `--sim` 的实际 pipeline，不再被描述成独立后处理。视频下载完成后会立刻按本次录制参数打标，成功后删除本地 raw 文件。
python Magicbot_Z1/scripts/label_video.py raw.mp4 -o final.mp4 --run <PHASE> --model <CKPT> --vel 0.3 m/s --extra "sim: IsaacLab/MuJoCo" ...rm raw.mp4 脚本自动 raw 自动清理 

## 文档定义 vs 现在现状

### 文档里的目标定义

较早的说明里把 `--sim` 写成 5 步：JIT 导出 → Isaac 录制 → MuJoCo 录制 → 下载视频 → 本地打标签。现在这张图只保留当前有效流程，不再单独指向旧说明文件。

### 现在真正可跑的一键路径

`rtx_record_video.sh` 现在是 GPU 检查/选卡 → JIT 检查/导出 → Isaac 录制 → Kit 清理等待 → MuJoCo 录制 → 自动 scp 下载 → 自动打标签并删除 raw。

### 最关键的现实差异

现在脚本和文档定义已经基本对齐，但仍然保持原始原则：录制始终发生在远端 RTX，回传和打标发生在本地。学习曲线绘图仍然是另一路，不属于这条视频 pipeline。

### 这次异常长的主要原因与修正

现象上主要是两件事叠加：批量中断后远端残留 Isaac 录制还在跑；旧脚本没有 `timeout` 和 Kit 清理等待，异常 run 会把后面的 phase 一起拖长。现在脚本已经补上 `ISAAC_TIMEOUT_SEC=600`、`MUJOCO_TIMEOUT_SEC=300`、`KIT_CLEANUP_TIMEOUT_SEC=60`，并在超时后强制回收 stale Kit 进程。

### 单 phase 耗时预期

正常情况下，单个 phase 应该是“Isaac 录制几分钟内完成 + 最多 60 秒 Kit 清理 + MuJoCo 约 20 秒实录与编码 + scp 回传 + 本地打标”。如果明显长于这个量级，优先怀疑远端残留 Isaac/Kit 进程没有退出。
 已在脚本里自动执行  需要后续接力  文档与实现存在缺口  参数解析与入口层 

## 当前入口参数

### 常用参数

- `--best <VERSION>`：从 `best_models.json` 自动解析 checkpoint。 
- `--checkpoint <PATH>`：手动指定模型。 
- `--video_length`：Isaac Lab 默认 1000；MuJoCo 以 20s@50Hz 对应到同量级 1000 steps。 
- `--vel_x`：MuJoCo 默认前进速度改为 0.3m/s。 
- `--duration`：MuJoCo 默认时长改为 20 秒。 
- `GPU_ID`：默认 `auto`，优先挑一张满足 `--idle` 规则的空闲卡。 
- `ISAAC_TIMEOUT_SEC` / `MUJOCO_TIMEOUT_SEC`：默认分别为 600 秒和 300 秒。 
- `KIT_CLEANUP_TIMEOUT_SEC`：默认 60 秒，超时后强制清理残留 Kit。 
- `--mujoco_only` / `--isaac_only`：只录单一路径。 
- `--skip_export`：跳过 JIT 导出检查。 

## 你现在最该关心的点

### 工作结论

- 现在跑 `--sim`，实际含义就是：远端录制两段视频，再自动 scp 回本地并立刻打标。 
- Isaac Lab 不再强制绑死 `cuda:0`，会优先使用满足 `--idle` 规则的空闲卡。 
- 为避免异常长，脚本会给 Isaac/MuJoCo 加 timeout，并在 Isaac 后等待 Kit 清理，不再直接硬切到下一段录制。 
- 绘图仍然走 `/plot-train-Z1`，不混进这条视频链路。 
 Source map: `docs/GPU_Train_Command_Reference.md`, `rtx_record_video.sh`, `Magicbot_Z1/scripts/label_video.py`, `Magicbot_Z1/scripts/plot_learning_curves.py`.