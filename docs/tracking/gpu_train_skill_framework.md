# `$gpu-train` Skill Framework

这个 skill 不是训练器本身，而是“远程 RTX 训练管理的操作抽象层”。它把 SSH、VPN、Slurm、GPU 查询、日志 tail、orchestrator resume、远程录视频等动作统一成一组稳定意图。
核心定位：远程训练运维代理 主目标：看状态、读日志、管 orchestrator、拉视频 强依赖 VPN / SSH / 远端 IsaacLab 环境 

## 1. Skill 的输入和真源
``````````

| 层 | 文件 | 作用 |
| --- | --- | --- |
| Skill 规范 | C:\Users\20174\.codex\skills\gpu-train\SKILL.md | 定义该 skill 该做什么、什么时候做、默认操作规则是什么。 |
| 平台真源 | references/platforms.md | 定义 SSH host、conda env、项目根目录、日志路径、录像命令。 |
| 补充文档 | RTX_Server_Guide.html、GPU_Train_Command_Reference.html、Z1_Orchestrator_Guide.html | 把路径和命令解释成操作手册。 |

## 2. Skill 实际管理的对象
````````````

| 对象 | 典型问题 | 它会调用什么 |
| --- | --- | --- |
| RTX 远端进程 | 训练还活着吗？PID 是什么？ | ssh ... ps aux |
| 远端日志 | 当前 reward、速度、ETA、loss 怎么样？ | tail -30、扫描 train_*.log |
| GPU | 哪张卡空闲？谁在占？是不是 Slurm 绕过？ | nvidia-smi、Slurm 队列、process owner 过滤 |
| orchestrator | 当前 phase 到哪了？能不能 resume？ | 检查 orchestrator_state.json、调用 Slurm wrapper |
| 录像产物 | 某个 checkpoint 的 IsaacLab / MuJoCo 视频如何批量录制并取回？ | 调用远端录制命令，再 scp 回本地 |

## 3. Skill 的标准工作流

```
用户意图
  -> 识别是状态 / GPU / 日志 / orchestrator / 录像 / 故障分析
  -> 读取 platforms.md 里的路径和命令
  -> 做 SSH 连通性测试
  -> 如果 SSH 失败：自动启动 iNode VPN，3 秒一重试，最多 10 次
  -> 执行远端查询或远端动作
  -> 用“当前状态 -> 指标 -> 健康判断 -> 下一步”格式返回
```

 这个 skill 的本质是把“你脑子里的远程训练排障流程”固定成一套标准操作序列，避免每次都重新拼 SSH 和路径。 

## 4. 命令家族梳理
``

| 家族 | 意图 | 典型输出 |
| --- | --- | --- |
| Connectivity | 确认能否连上 RTX | SSH 是否成功，VPN 是否需要拉起 |
| Training Status | 查训练是否存活 | 进程、PID、run 名、活跃日志 |
| Tail Logs | 看最后 30 行，估计训练健康 | iteration、reward、loss、speed、ETA、中文健康判断 |
| GPU Usage | 查每张卡是否空闲 | 利用率、显存、哪个用户在用、推荐 cuda:<id> |
| My CUDA | 只看当前用户自己的 GPU 进程 | 用户级占卡信息 |
| Slurm Review | 看队列与 bypass 违规 | job、GPU、PID、user、命令 |
| Orchestrator | start / resume / stop / from 某 phase | 状态文件、当前 phase、作业提交结果 |
| Video / Artifact | 为某 checkpoint 录视频、导出并拉回 | 本地输出路径、成功与否 |

## 5. 与 Z1 项目的绑定点
````````````

| 绑定项 | 固定值 |
| --- | --- |
| SSH Host | phh@192.168.120.155 |
| VPN | iNode Client |
| Conda Env | isaaclab |
| 远端项目根 | ~/magiclab_rl_lab |
| Z1 checkpoint 根 | ~/magiclab_rl_lab/logs/rsl_rl/magiclab_z1_12dof_velocity/<run_dir> |
| orchestrator state | ~/magiclab_rl_lab/orchestrator_state.json |

## 6. Orchestrator 子框架

```
/gpu-train --orchestrator --start
  -> bash D:/Desktop_Files/GPU-Train/RTX6000/rtx_submit_orchestrator_train.sh

/gpu-train --orchestrator --start --from p3_fine
  -> bash .../rtx_submit_orchestrator_train.sh --from p3_fine

/gpu-train --orchestrator --resume
  -> 先检查 ~/magiclab_rl_lab/orchestrator_state.json
  -> 再 bash .../rtx_submit_orchestrator_train.sh --resume
```

- 这个 skill 默认更偏向 Slurm wrapper，而不是直接在远端跑 `nohup python ... phase_orchestrator.py`。 
- 只有用户明确要求 manual direct launch，或者 Slurm 不可用时，才应偏向手动 nohup。 
- resume 是一个强约束动作，没有 state file 就不该假装能 resume。 

## 7. Skill 的边界

| 会做 | 不会做 |
| --- | --- |
| 自动拉 VPN、自动重试 SSH、自动读日志、自动判断 GPU 是否空闲 | 未经确认直接 kill 训练、kill orchestrator 或停别人的作业 |
| 总结状态、给出结论和下一步建议 | 把 SSH 原始长输出原封不动扔给用户 |
| 按固定路径找 Z1 日志、视频、checkpoint | 擅自猜测不存在的 run 或跳过 state preflight |