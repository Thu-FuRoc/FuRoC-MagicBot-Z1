# Z1 Locomotion 鲁棒训练整理

更新时间：2026-05-19

本文整理以下几部分内容：

1. 当前 Z1 locomotion 训练状态与 checkpoint
2. 这次为了“突然减速到 0 后保持静止”和“受扰动后自平衡”所做的训练改动
3. 一般 locomotion 训练的常见做法
4. 外力扰动、站立恢复、初速度归零这类鲁棒性能力通常怎么加
5. 奖励权重和扰动强度通常怎么调
6. 这些做法与当前 Z1 配置的对应关系

---

## 1. 当前训练状态

截至 2026-05-19，本次实际在跑的是：

- Slurm Job：`52`
- 当前 sub-phase：`p3_coarse`
- 当前状态：`running`
- 当前 run_dir：`/home/phh/magiclab_rl_lab/logs/rsl_rl/magiclab_z1_12dof_velocity/2026-05-19_14-28-31_p3_coarse`
- 续训来源 checkpoint：`/home/phh/magiclab_rl_lab/logs/rsl_rl/magiclab_z1_12dof_velocity/2026-05-18_19-35-30_p2_fine/model_3600.pt`

目前已确认：

- 不是从头训练，而是从 `p2_fine/model_3600.pt` 接着训
- 这是当前最合理的做法，因为这次新增的是鲁棒性课程，不是更换整个 locomotion 基础目标
- 新加入的扰动已经部署到当前计划中，训练不是停留在旧配置

远端状态文件记录：

- orchestrator state：`~/magiclab_rl_lab/orchestrator_state.json`
- 本地 tracking：`D:\Desktop_Files\GPU-Train\RTX6000\Magicbot_Z1\docs\tracking\bestmodel_phase.json`

当前训练快照显示：

- `p3_coarse` 已从 `iter=3600` 继续往上跑
- 在 `2026-05-19 14:39` 左右已到 `iteration 3930`
- 训练未再出现之前的 `locs is not defined` 崩溃
- 新生成配置里已经包含 `base_external_force_torque_interval`

---

## 2. 这次训练目标到底是什么

这次不是在做“摔倒后起身”训练，而是优先做两类能力：

1. 命令速度突然减小到 0 时，机器人不要继续晃动或多走几步，而是尽量停住并站稳
2. 机器人在行进或站立过程中受到突发外扰时，不要立刻倒下，而是尽量恢复平衡

因此，这次训练重点是：

- `stand still` 能力
- `push recovery / disturbance rejection`
- `zero-command stabilization`

这和“跌倒后爬起”是不同课题。

“跌倒后爬起”通常需要单独的 recovery/get-up 任务，往往会额外加入：

- 从侧躺、趴卧、仰卧开始的 reset
- 更宽的姿态初始化范围
- 不同的终止逻辑
- 专门的起身奖励

当前这条训练线还没有进入这个课题。

---

## 3. 这次部署的核心改动

用户要求是：

- 保留现有 `velocity push`
- 再加一个真正的 `interval force/torque` 扰动
- 扰动幅度要保守，不要一下把训练打崩

本次实际已经落地的方向就是这个。

### 3.1 原来已有的扰动

原配置里本来就有两类相关机制：

1. `push_robot = mdp.push_by_setting_velocity`
   - 这是 interval 事件
   - 本质上更像“突然给底座一个速度扰动”
   - 它对 policy 来说是有效的，但不是物理意义上的持续外力/外力矩

2. `reset_root_state_uniform`
   - 在 episode reset 时直接给根部速度范围
   - 这能训练“带初速度起步后如何恢复”
   - 但它只发生在 reset，不是训练过程中的持续干扰

原模板中的 `base_external_force_torque` 之前主要是 `mode="reset"`，不是训练过程中的 interval 扰动。

### 3.2 这次新增的扰动

这次新增的是：

- `base_external_force_torque_interval = EventTerm(... mode="interval" ...)`

含义是：

- 训练过程中，按一定时间间隔
- 直接给机器人底座施加外力和外力矩
- 它和 `push_by_setting_velocity` 不同，是真正意义上的 force/torque 扰动

这就是前面说的 “interval 事件”。

### 3.3 为什么要同时保留两种扰动

两种扰动分别覆盖的东西不同：

- `velocity push`
  - 更像瞬时速度状态被打乱
  - 容易训练“被推一下后速度误差如何纠正”

- `interval force/torque`
  - 更像机器人真的受到了外部推挤、冲击、偏航扭矩
  - 更容易训练姿态恢复、抗干扰、站稳

保留两者的原因是：

- 前者对速度跟踪恢复有帮助
- 后者对姿态恢复和抗扰动更直接
- 只留其中一种，覆盖面不够

### 3.4 为什么这次不建议从头训练

当前建议是继续从 `p2_fine/model_3600.pt` 续训，而不是从头开始。

原因：

1. `p2_fine` 已经学到了较稳定的平地速度跟踪基础
2. 这次改的是 terrain + disturbance curriculum，不是重写 locomotion 目标
3. 从头训练会把大量算力浪费在重新学习基础步态上
4. 当前更合理的做法是基于已有步态做鲁棒性扩展

只有在以下情况才更像是要考虑从头训：

- 奖励结构大改
- 动作空间/观测空间大改
- 机器人模型、关节定义、控制接口发生明显变化
- 现有策略已经形成很难纠正的坏习惯，且微调长期无改善

目前还没到这个程度。

---

## 4. 当前配置中与鲁棒性最相关的项

下面只摘最关键的，不把整份 YAML 原样展开。

### 4.1 `p2_fine`：当前续训的基础

`p2_fine` 主要是平地速度跟踪基础：

- `track_lin_vel_xy: 2.0`
- `track_ang_vel_z: 1.0`
- `stand_still: -3.5`
- `flat_orientation_l2: -5.0`
- `base_height: -10.0`
- `action_rate_l1: -0.05`
- `joint_deviation_hip_knee: -0.8`

这里已经有一定的 `stand_still` 惩罚，所以并不是完全没有“停住”意识，但强度还不足以覆盖 terrain + disturbance 下的更复杂情况。

### 4.2 `p3_coarse`：当前正在训练的鲁棒过渡阶段

当前 `p3_coarse` 里与本次目标直接相关的项：

命令与站立样本：

- `resampling_time_range: [3.0, 5.0]`
- `rel_standing_envs: 0.30`

含义：

- 命令切换更频繁
- 30% 环境会采到站立/接近零速度命令
- 这对“从移动到静止”的学习很关键

新增 interval 力/力矩扰动：

- `interval_force_torque.interval_range_s: [3.0, 4.5]`
- `interval_force_torque.force_range: [-18.0, 18.0]`
- `interval_force_torque.torque_range: [-4.0, 4.0]`

保留的 velocity push：

- `push_robot.interval_range_s: [2.0, 3.0]`
- `push_robot.velocity_range.x: [-1.5, 1.5]`
- `push_robot.velocity_range.y: [-1.2, 1.2]`

更强的 reset 初速度扰动：

- `reset_base.velocity_range.x/y: [-1.0, 1.0]`
- `reset_base.velocity_range.roll/pitch/yaw` 扩大到 `[-0.8, 0.8]`

奖励项：

- `track_lin_vel_xy: 1.6`
- `track_ang_vel_z: 0.6`
- `stand_still: -3.0`
- `flat_orientation_l2: -5.5`
- `feet_slide: -0.1`
- `feet_clearance: 1.0`
- `undesired_contacts: -0.8`

这里的总体思路是：

- 跟踪奖励略降一点
- 稳定、抗滑、足部抬脚、站稳类约束更强
- 让策略先学会“别倒”和“被打扰后还能收回来”

### 4.3 `p3_fine`：后续更强的鲁棒阶段

`p3_fine` 会进一步增强：

- `rel_standing_envs: 0.35`
- `interval_force_torque.force_range: [-28.0, 28.0]`
- `interval_force_torque.torque_range: [-6.0, 6.0]`
- `base_external_force_torque.force_range: [-35.0, 35.0]`
- `base_external_force_torque.torque_range: [-8.0, 8.0]`
- `push_robot.interval_range_s: [1.8, 2.8]`
- `stand_still: -4.0`
- `undesired_contacts: -1.8`

也就是：

- 站立样本更多
- 干扰更频繁更强
- 站稳和不发生坏接触的约束更强

### 4.4 后续 `p4 / p5`

`p4`、`p5` 里也已经布了更强的 interval force/torque、push 和 reset 难度，但这属于后续 rough/full terrain 课程，不是当前最先要吃透的阶段。

---

## 5. 一般 locomotion 训练是怎么做的

这一部分是对常见 RL locomotion 训练思路的归纳，不局限于某一个仓库。

### 5.1 常见总体流程

最常见的是 curriculum learning：

1. 先在平地学站稳、学基本步态
2. 再学速度跟踪
3. 再上不同地形
4. 再加更强的随机化和扰动
5. 最后做更高速度、更复杂地形、更强恢复能力

这和当前 Z1 的 `P1 -> P2 -> P3 -> P4 -> P5` 思路是一致的。

### 5.2 常见奖励结构

locomotion 常见奖励通常由以下几类组成：

1. 任务主奖励
   - 线速度跟踪
   - 角速度跟踪

2. 生存/姿态稳定
   - `alive`
   - base height
   - 姿态误差

3. 动作平滑和物理可控性
   - action rate
   - joint velocity
   - joint acceleration
   - energy / torque / power

4. 足端相关
   - 脚接触数量
   - 脚滑移
   - 抬脚高度/clearance

5. 结构约束
   - 关节偏离默认位姿
   - 关节极限惩罚
   - 不期望碰撞

6. 停止命令下的稳定
   - `stand_still`
   - zero-command drift penalty

### 5.3 常见课程设计

常见课程通常同时沿几个轴逐步加难：

- 地形难度
- 命令速度范围
- 扰动强度
- reset 初始状态范围
- 域随机化强度

这类训练很少一开始就把所有难度开满，否则 PPO 很容易直接学崩。

---

## 6. 训练 locomotion 时，通常会不会考虑不同地形之外的内容

会，而且在成熟 locomotion 训练里，这通常是非常重要的一块。

除了 terrain 之外，常见还会加：

### 6.1 外力或冲击扰动

这是最直接的 push recovery 训练方式之一。

常见做法：

- interval velocity push
- interval external force
- interval external torque
- random shove during motion or standing

目的：

- 不要一受扰动就倒
- 让策略学会把 COM、足步和躯干姿态重新拉回来

### 6.2 reset 时初始速度和姿态扰动

常见做法：

- reset 时给根部线速度/角速度
- reset 时给一定 roll/pitch/yaw 偏差

目的：

- 让机器人不是永远从“标准站姿、零速度”开始
- 学会从轻度失衡状态回到稳定状态

### 6.3 站立命令样本

很多训练都会显式保留一部分 `standing environments` 或零速度命令样本。

目的：

- 防止策略只会“走”
- 让它学会“该停的时候停住”
- 避免命令变成 0 后还保持残余摆动和步伐

### 6.4 域随机化

常见内容：

- 质量
- 摩擦
- 电机参数
- 接触参数
- 延迟/噪声

目的：

- 增强 sim-to-real 鲁棒性
- 防止策略只适应一个非常干净的仿真条件

### 6.5 会不会训练“摔倒后再站起”

有，但不是默认都会做。

很多 locomotion 仓库只做到：

- 不那么容易摔倒
- 轻度受扰动后能恢复

而不会默认做到：

- 已经摔下去后再爬起来

“摔倒后起身”通常是单独任务，不是普通 velocity locomotion 配置默认顺带就学会的东西。

---

## 7. 针对“突然速度归零”和“受扰动后自平衡”，一般怎么做

如果只针对这个问题，一般会优先加以下三类东西。

### 7.1 增加零命令样本比例

核心做法：

- 提高 `rel_standing_envs`
- 缩短 `resampling_time_range`

这样策略会更频繁地遇到：

- 前一段时间在走
- 下一段命令突然接近 0
- 必须从运动状态过渡到静止

这比只靠奖励项更直接。

### 7.2 增加 `stand_still` 惩罚

只在命令接近 0 时生效，鼓励：

- 少余振
- 少多余步态
- 少关节乱晃

如果没有这个项，policy 常会出现：

- 虽然速度跟踪没错太多
- 但停下时仍然不安静，甚至左右晃动

### 7.3 增加过程中的 interval 扰动

这次新加的 `interval force/torque` 就属于这一类。

它比只在 reset 时打乱更有效，因为它发生在 episode 进行中，策略必须在线恢复。

常见经验是：

- 先小幅度
- 先低频
- 看 reward 和 termination 是否还能维持
- 再逐渐放大

不建议一上来就用很大的 force/torque。

### 7.4 保留 reset 初速度扰动

这个很有必要，因为它能覆盖：

- 一开始就带速度
- 一开始姿态就有点偏
- 需要先把自身稳定下来再继续任务

它和 interval push 不是互相替代，而是互补。

---

## 8. 一般这些权重怎么调

这一部分回答“他们一般会怎么调整第二个问题里的这些权重”。

### 8.1 总原则

不是靠一次把某个惩罚拉得特别大，而是按课程渐进调整：

1. 先保证能走
2. 再保证走得稳
3. 再保证在更难条件下也不容易倒
4. 最后再抠停止质量、抗扰性和复杂地形性能

### 8.2 任务奖励和稳定性约束的平衡

常见做法是：

- 在早期阶段，速度跟踪奖励占主导
- 但姿态、base height、action smoothness 不能太弱
- 到更难阶段，通常会稍微降低“只追速度”的激进程度，增强稳定性和接触质量约束

如果跟踪奖励过强，常见问题是：

- 策略为了追命令过于激进
- 受扰动后先冲着速度误差去修，而不是先稳住

### 8.3 `stand_still` 怎么调

常见经验：

- 平地基础阶段先有但不必太大
- 当开始强调 stop-to-stand 时再逐步加大
- 要结合 `rel_standing_envs` 一起调

如果只加大 `stand_still`，但很少出现零速度命令样本，训练信号不充分。

### 8.4 扰动强度怎么调

常见做法是 curriculum：

- 先加轻微 push
- 再加更频繁的 push
- 再加真实 force/torque
- 再把 reset 姿态和初速度范围放大

调节顺序通常比“精确绝对数值”更重要。

如果出现以下现象，说明扰动过强：

- reward 长时间塌到很低
- episode length 显著掉下去
- `bad_orientation` 持续接近 100%
- 几乎没有有效步态恢复

### 8.5 终止项和恢复项的平衡

如果 termination 太苛刻，policy 还没来得及学恢复就被切 episode。

如果 termination 太松，策略可能会在非常差的姿态里浪费大量样本。

因此常见做法是：

- 对轻度失衡保留恢复机会
- 对明显无解姿态及时终止

这一点对“想不想学起身”尤为重要。

若目标真的是跌倒后再起，需要重新设计 termination 和 reset，而不只是微调 reward。

---

## 9. 训练时一般关注哪些指标

除了总 reward，真正有用的通常是以下几类。

### 9.1 任务指标

- `track_lin_vel_xy`
- `track_ang_vel_z`
- velocity error

### 9.2 稳定性指标

- episode length
- `bad_orientation`
- `base_height`
- `time_out`

其中：

- `time_out` 高，通常说明更稳定
- `bad_orientation` 高，通常说明更容易姿态失稳

### 9.3 行为质量指标

- `stand_still`
- `feet_slide`
- `feet_clearance`
- `undesired_contacts`
- `action_rate_l1`

### 9.4 抗扰恢复能力

如果单独做 robustness 分析，建议额外观察：

- 受扰动后是否快速恢复到目标速度
- 受扰动后是否能回到小姿态误差
- 命令归零后是否存在长期漂移
- 站立时是否还会持续迈步

---

## 10. 当前 Z1 配置与常见做法的对应关系

当前 Z1 已经覆盖了比较标准的一套 locomotion 训练组件：

### 已有

- curriculum 分阶段训练
- 平地到复杂地形的 progression
- 速度命令随机化
- `standing envs`
- reset 姿态/速度扰动
- velocity push
- friction / mass randomization
- 姿态、base height、action smoothness、足端接触等常见奖励

### 这次补上的关键缺口

- 真正的 `interval force/torque` 扰动

这一步很关键，因为它让“抗外力扰动”从间接训练变成直接训练。

### 当前还没有专门覆盖的内容

- 跌倒后起身
- 从躺倒姿态恢复到站立
- 专门的 recovery controller 课程

如果未来要做这一块，建议另开一条 recovery curriculum，而不是硬塞进当前 velocity locomotion 任务里。

---

## 11. 本次代码/配置落点

本次已涉及的关键文件：

- 训练计划：
  - `D:\Desktop_Files\GPU-Train\RTX6000\Magicbot_Z1\magiclab_rl_lab\training_plans\z1_5phase_plan.yaml`

- 配置生成器：
  - `D:\Desktop_Files\GPU-Train\RTX6000\Magicbot_Z1\magiclab_rl_lab\scripts\automation\config_generator.py`

生成器中已经加入：

- 读取 `env.events`
- 生成 `base_external_force_torque_interval = EventTerm(... mode="interval" ...)`

也就是说，现在 training plan 里写的：

- `interval_force_torque`
- `push_robot`
- `reset_base`

都可以被正确写入生成配置。

---

## 12. 目前训练健康度的一个简单判断

当前 `p3_coarse` 已经启动并在继续推进，但从最近训练日志看，现阶段还处在“刚把难度抬起来后的适应期”。

当前可见现象：

- `Mean reward` 仍然是负值附近
- `stand_still` 已经开始贡献明显惩罚项
- `Episode_Termination/bad_orientation` 目前非常高

这通常意味着：

- 扰动和 terrain 已经真的生效了
- 策略正在重新适应更难的阶段
- 接下来要重点观察是否能逐步把 `bad_orientation` 压下来，并让 reward 回升

所以当前最重要的不是继续加更强扰动，而是先观察 `p3_coarse` 这组保守幅度能否稳定吸收。

---

## 13. 对后续训练的建议

当前建议顺序：

1. 先让 `p3_coarse` 跑一段，观察 reward、episode length、`bad_orientation` 是否改善
2. 如果能稳住，再进入 `p3_fine`
3. 不建议现在立刻从头训练
4. 也不建议现在就把 interval force/torque 再大幅加重
5. 如果后面发现“停住”仍然不够好，可继续增加：
   - `rel_standing_envs`
   - `stand_still`
   - 零速度命令切换频率
6. 如果未来目标升级为“跌倒后爬起”，建议单独开 recovery 任务，不要直接混进当前 velocity locomotion 主线

---

## 14. 参考资料

以下是这次整理时参考过、并且与当前问题最相关的资料：

1. legged_gym
   - https://github.com/leggedrobotics/legged_gym

2. Rudin et al., 2022, Learning to Walk in Minutes Using Massively Parallel Deep Reinforcement Learning
   - https://proceedings.mlr.press/v164/rudin22a.html

3. Isaac Lab Spot locomotion velocity config
   - https://github.com/isaac-sim/IsaacLab/blob/main/source/isaaclab_tasks/isaaclab_tasks/manager_based/locomotion/velocity/config/spot/flat_env_cfg.py

4. Atalante push-recovery related work
   - https://arxiv.org/abs/2203.01148

5. iCub whole-body push recovery related work
   - https://arxiv.org/abs/2104.14534

这些资料共同说明的趋势基本一致：

- locomotion 不只是地形课程
- 抗扰动和站稳能力通常需要显式训练
- 零速度站立、push recovery、reset 随机化、domain randomization 都是常用手段
- “跌倒后起身”通常是单独问题，不是默认自然学会

---

## 15. 一句话结论

当前路线是正确的：

- 不从头训
- 保留 `velocity push`
- 增加真实 `interval force/torque`
- 提高 standing 比例
- 通过 `stand_still + reset velocity + disturbance curriculum` 去学“突然停住”和“受扰动后自平衡”

这条路线比单纯继续原配置训练，更接近你要的目标。
