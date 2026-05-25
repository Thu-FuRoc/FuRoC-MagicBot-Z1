Version Compare 

# `play_z1_video.py` 三版本对照

 比较对象是远端 RTX 实际录制脚本的三个阶段：最旧可用版 `6ffbe57`、中间版 `72f4107`、当前版（含 `e09dfba` 及本地诊断增强）。 重点看相机、录制逻辑、warmup、JIT 支持，以及 URDF→USD headless 修复。 

## 总览
````````````````````````````

| 维度 | 6ffbe57 | 72f4107 | 当前版 |
| --- | --- | --- | --- |
| 输入模式 | 只支持 --checkpoint | --checkpoint + --policy | --checkpoint + --policy |
| CamTrack | 无 | 有，支持 --no_camera_track | 有，支持 --no_camera_track |
| 静态视角 | 无专门逻辑 | 有，固定 45 度俯视角 | 有，固定 45 度俯视角 |
| Warmup | 无 | 有，20 steps | 有，20 steps |
| RecordVideo fps | 未显式设置 | 显式 fps=50 | 显式 fps=50 |
| 速度日志 | 无 | 有 sweep.json | 有 sweep.json |
| URDF→USD 修复 | 无 | 无 | 有，清 instanceable |
| 强制 USD 重转 | 无 | 无 | 有，清缓存 + force_usd_conversion |
| Fabric 处理 | 无 | 无脚本内处理 | 脚本内 use_fabric = False |
| 诊断增强 | 无 | 无 | 有，可见性诊断与强制可见 |

**结论先行** 如果你说“最开始、最旧的那个才是可以用的”，最有可能指向的是 `6ffbe57` 的录制风格。 它最简单，没有 CamTrack、没有 warmup、没有后续修复，行为也最接近“早期原味”。但它同时也是最脆弱的一版。 

## 推荐判断

### 6ffbe57
最旧 最接近早期风格 

- 没有相机跟拍逻辑。 
- 没有 warmup，容易出现黑帧或首段不稳定。 
- 没有 headless 可见性修复。 
- 如果早期成功录制就是靠它，那画面风格最可能和你记忆一致。 

### 72f4107
旧但更完整 行为已变化 

- 引入了 CamTrack / 静态视角切换。 
- 引入 warmup 和 `fps=50`。 
- 增加 JIT 模式和速度日志。 
- 最像“旧版本里还能正常工程化”的版本。 

### 当前版
最稳 风格最偏离早期 

- 在 72f4107 基础上加了 URDF→USD 修复。 
- 还加了 debug marker 控制、强制可见、诊断输出。 
- 更适合排查 headless 不可见，但不一定最像你以前的成片。 

## 代码层异同点
````````````

| 点位 | 6ffbe57 | 72f4107 | 当前版 |
| --- | --- | --- | --- |
| 参数面 | 只有基础录制参数 | 新增 --policy、--no_camera_track、--camera_distance、--camera_height | 再新增 --show_command_marker |
| 环境入口 | 固定 OnPolicyRunner | 支持 OnPolicyRunner / JIT 双分支 | 保持双分支 |
| 相机逻辑 | 没有显式相机控制 | 有跟拍和静态视角逻辑 | 保持 72f4107 的相机逻辑 |
| 首帧稳定 | 直接包 RecordVideo | 先 warmup 再录 | 先 warmup 再录 |
| headless 机器人可见 | 无特殊处理 | 无特殊处理 | 清缓存、重转 USD、清 instanceable、强制可见 |
| 日志/可观测性 | 最少 | 中等 | 最多 |

## 最关键的分歧

### 你现在不满意的“两版”为什么都不像以前

- 这两版都基于“当前脚本”，不是历史旧脚本本体。 
- 只是相机参数不同：一版 CamTrack，一版静态视角。 
- 它们都已经带了后来的 warmup / fps / USD 修复 / 诊断增强。 

### 如果目标是“回到最早能用的感觉”

- 应优先测试 `6ffbe57`，因为它才是真正最旧的录制脚本内容。 
- `72f4107` 更适合作为“旧版但仍比较完整”的中间参考。 
- 当前版更像排障脚本，不像最初成片脚本。 

## 下一步建议

 最快的验证方式不是继续调当前参数，而是直接拿 GitHub 历史版本脚本本体做 A/B 测试。 

- 先备份远端当前 `play_z1_video.py`。 
- 切到 `6ffbe57` 版本，录一条 `p1_coarse@2900`。 
- 再切到 `72f4107`，录同一条。 
- 和当前版对照，三选一。