# RTX 与本地配置对照

目的：区分三类配置来源，并验证 `p1 / p2 / p3` 在 RTX 上实际训练使用的 artifact，和本地 `training_plans/z1_5phase_plan.yaml`、当前 `source/.../velocity_env_cfg.py` 的关系。
deploy.yaml: RTX 与本地下载件一致 p3 实际训练地形: 与本地 plan 一致 历史 run 的 velocity_env_cfg.py 是训练快照，不等于你当前 source 模板 

## 1. 三类文件分别代表什么
**** ``**** ``**** ``**** ``

| 类型 | 路径示例 | 含义 | 判断优先级 |
| --- | --- | --- | --- |
| RTX 训练快照 | ~/magiclab_rl_lab/logs/rsl_rl/.../<run_dir>/params/velocity_env_cfg.py | 某次训练当时真正使用的环境配置，随 run 一起固化保存。 | 最高。判断“那次训练到底跑了什么”优先看它。 |
| 本地训练计划 | Magicbot_Z1/training_plans/z1_5phase_plan.yaml | 当前 pipeline 的 phase 设计稿。由 orchestrator 读入，再生成具体 env cfg。 | 高。判断“当前计划应该跑什么”看它。 |
| 本地 source 模板 | Magicbot_Z1/magiclab_rl_lab/source/.../velocity_env_cfg.py | 当前源码树里放着的 active 模板，后续可能继续被替换或修改。 | 低。不能直接反推旧 run 当时的配置。 |
| deploy.yaml | .../params/deploy.yaml | 部署侧参数：关节映射、step_dt、PD、动作缩放、观测缩放、命令范围。 | 用于部署验证；不记录 terrain generator 细节。 |

 “历史训练快照”和“当前 source 模板”不相等是正常现象。因为每次训练都会把当时生成出来的 env cfg 单独存进 run 目录，之后你本地源码继续改了，历史快照不会跟着变。 

## 2. deploy.yaml 一致性
**** ``````**** ``````**** ``````**** ``````

| Sub-phase | RTX run_dir | RTX deploy SHA256 | 本地 deploy SHA256 | 结论 |
| --- | --- | --- | --- | --- |
| p1_coarse | 2026-05-06_15-47-12_p1_coarse | b2a60f3e...456021b | b2a60f3e...456021b | 一致 |
| p1_fine | 2026-05-06_17-40-13_p1_fine | b2a60f3e...456021b | b2a60f3e...456021b | 一致 |
| p2_coarse | 2026-05-15_17-44-46_p2_coarse | e98639bc...c0648c2 | e98639bc...c0648c2 | 一致 |
| p2_fine | 2026-05-15_19-58-42_p2_fine | e98639bc...c0648c2 | e98639bc...c0648c2 | 一致 |

说明：这里的“一致”只说明部署参数一致，不说明环境 terrain 一定从 deploy.yaml 读取。实际上 terrain 细节不在 deploy.yaml 里。

## 3. p1 / p2 实际环境对照
**** ``````````**** ``````````

| Phase | RTX 历史训练快照 | 本地 plan | 本地当前 source 模板 | 结论 |
| --- | --- | --- | --- | --- |
| p1_coarse / p1_fine | COBBLESTONE_ROAD_CFG = Noneterrain_type="plane"terrain_generator=None | terrain_type: planeterrain_generator: null | 当前 source 不是 p1 快照，不能拿它反推 p1 历史 run。 | RTX 实际训练与 plan 一致，都是平地 |
| p2_coarse / p2_fine | COBBLESTONE_ROAD_CFG = Noneterrain_type="plane"terrain_generator=None | terrain_type: planeterrain_generator: null | 当前 source 不是 p2 快照，不能拿它反推 p2 历史 run。 | RTX 实际训练与 plan 一致，都是平地 |

## 4. p3 实际环境对照
**** ````````````````````````````````**** ````````````````````````````````

| Sub-phase | RTX 历史训练快照 | 本地 plan | 本地当前 source 模板 | 结论 |
| --- | --- | --- | --- | --- |
| p3_coarse | terrain_type="generator"
              terrain_generator=COBBLESTONE_ROAD_CFG
              flat proportion=0.7
              random_grid proportion=0.3
              grid_height_range=(0.0, 0.25)
              size=[8.0, 8.0], num_rows=9, num_cols=21
              horizontal_scale=0.1, vertical_scale=0.005 | terrain: gentle
              terrain_type: generator
              flat 0.7 + random_grid 0.3
              difficulty_range: [0.0, 0.25] | 当前本地 source 头部是：
              terrain_type="generator"
              sub_terrains={"flat": proportion=0.5}
              不是 p3_coarse 的历史快照 | RTX 实际训练与本地 plan 一致与当前 source 模板不一致 |
| p3_fine | terrain_type="generator"
              terrain_generator=COBBLESTONE_ROAD_CFG
              flat proportion=0.7
              random_grid proportion=0.3
              grid_height_range=(0.0, 0.35)
              size=[8.0, 8.0], num_rows=9, num_cols=21
              horizontal_scale=0.1, vertical_scale=0.005 | terrain: gentle
              terrain_type: generator
              flat 0.7 + random_grid 0.3
              difficulty_range: [0.0, 0.35] | 当前本地 source 头部是：
              terrain_type="generator"
              sub_terrains={"flat": proportion=0.5}
              不是 p3_fine 的历史快照 | RTX 实际训练与本地 plan 一致与当前 source 模板不一致 |

 p3 这里的“一致”，是指 RTX run 目录里的 `params/velocity_env_cfg.py` 和本地 `training_plans/z1_5phase_plan.yaml` 一致。不是指它和你当前 source 树里的 `velocity_env_cfg.py` 一致。 

## 5. 最短结论

- **p1 / p2**：RTX 上实际训练用的是平地，和本地 plan 一致。 
- **p3_coarse**：RTX 上实际训练用的是 `generator`，`70% flat + 30% random_grid`，高度上限 `0.25`，和本地 plan 一致。 
- **p3_fine**：RTX 上实际训练用的是 `generator`，`70% flat + 30% random_grid`，高度上限 `0.35`，和本地 plan 一致。 
- **deploy.yaml**：本地下载件和 RTX run 目录里的部署参数一致。 
- **当前本地 source 模板**：不是这些历史 run 的快照，不能用它去反推当时实际训练配置。 
 现在如果你要继续追“当前到底应以谁为准”，答案是：看历史训练事实用 RTX run 目录里的 `params/velocity_env_cfg.py`；看当前 pipeline 设计用本地 `z1_5phase_plan.yaml`；不要直接拿当前 source 模板替代这两者。 

## 6. 关键路径

- 本地 plan: `Magicbot_Z1/training_plans/z1_5phase_plan.yaml`
- 本地当前 source 模板: `Magicbot_Z1/magiclab_rl_lab/source/magiclab_rl_lab/magiclab_rl_lab/tasks/locomotion/robots/z1/12dof/velocity_env_cfg.py`
- RTX 历史 run 示例: `~/magiclab_rl_lab/logs/rsl_rl/magiclab_z1_12dof_velocity/2026-05-16_12-13-26_p3_fine/params/velocity_env_cfg.py`
- 本地 deploy 下载件: `Magicbot_Z1/videos/p/*/params/deploy.yaml`