# Z1 当前地形加载状态

基于当前有效模型跟踪文件 `docs/tracking/bestmodel_phase.json`、训练计划 `training_plans/z1_5phase_plan.yaml`、以及本地 MuJoCo 脚本 `sim2sim/mujoco_manual.py` 汇总。
当前有效 best model: p1_fine / p2_fine / p3_fine p4 / p5 仅在训练计划中，尚无最新 best model p3b 已从跟踪文件归档，但 MuJoCo 代码仍残留 legacy 映射 Tracking Source bestmodel_phase.json 更新时间 2026-05-16 23:00 +08:00。当前 phase_best 分别是 p1_fine、p2_fine、p3_fine。 Isaac Lab Current Plan P1/P2 Flat, P3 Gentle P1/P2 使用 plane；P3 使用 generator: 70% flat + 30% random_grid。P3 fine 将 random_grid difficulty 上限从 0.25 提到 0.35。 MuJoCo Current Code Flat + P3 + Legacy P3b 代码仍支持 `p3b`，并把 `p4` 映射到旧的 `p3b` 近似地形；`p5` 没有专门映射。 

## 1. 当前有效 phase / best model 视角
**** ``````**** ``````**** ````````**** ````**** ````**** 

| Phase | Tracking 状态 | 当前 best model | Isaac Lab 实际训练地形 | MuJoCo 当前会加载什么 |
| --- | --- | --- | --- | --- |
| p1 | COMPLETE | p1_fine/model_2800.pt | 100% 平地，terrain_type=plane | --phase p1 -> flat ground |
| p2 | COMPLETE | p2_fine/model_4800.pt | 100% 平地，terrain_type=plane | --phase p2 -> flat ground |
| p3 | COMPLETE | p3_fine/model_5500.pt | Gentle terrain，70% flat + 30% random_grid | --phase p3 -> MuJoCo p3 gentle hfield |
| p4 | PLANNED | 暂无 | Rough terrain，训练计划已定义 | 当前代码仍是 --phase p4 -> legacy p3b |
| p5 | PLANNED | 暂无 | Full terrain，训练计划已定义 | 当前 PHASE_TERRAIN 没有 p5 项，默认会退回 flat |
| p3b | ARCHIVED | 已废弃 | 不再是当前 pipeline phase | MuJoCo 代码中仍保留 legacy terrain 生成路径 |

 结论：以当前跟踪文件为准，活跃 phase 只有 p1/p2/p3。MuJoCo 端的 phase 映射还没有完全追上当前训练计划，尤其是 p4/p5。 

## 2. Isaac Lab 当前加载的地形高度与分布

这里列的是当前训练计划 `z1_5phase_plan.yaml` 中定义的 terrain 配置，也就是 Isaac Lab 训练时真正使用的分布。重点看当前有效模型对应的 p1、p2、p3。
**** ````**** ````**** ``````**** ``````**** ``````**** ``````**** ``````

| Phase / Sub-phase | terrain_type | 分布 | 高度 / 几何参数 | 来源说明 |
| --- | --- | --- | --- | --- |
| p1_coarse / p1_fine | plane | 100% flat | 无 heightmap；平地 | terrain_generator: null |
| p2_coarse / p2_fine | plane | 100% flat | 无 heightmap；平地 | terrain_generator: null |
| p3_coarse | generator | flat 70% + random_grid 30% | random_grid difficulty_range=[0.0, 0.25] | 基础 gentle terrain |
| p3_fine | generator | flat 70% + random_grid 30% | random_grid difficulty_range=[0.0, 0.35] | 在 p3 基础上抬高 random_grid 上限 |
| p4_coarse | generator | flat 30% + random_grid 30% + stairs 20% + gap 10% + boxes 10% | difficulty_range=[0.0, 0.8] | rough terrain，当前仅计划态 |
| p4_fine | generator | flat 30% + random_grid 30% + stairs 20% + gap 10% + boxes 10% | difficulty_range=[0.0, 1.0] | 在 p4_coarse 上放开高度 / 难度上限 |
| p5_coarse / p5_fine | generator | flat 20% + random_grid 20% + stairs 20% + gap 20% + boxes 20% | phase 级别 difficulty_range=[0.0, 1.0] | full terrain，当前仅计划态 |

### Isaac Lab 参数如何落成实际 terrain 类

- `training_plans/z1_5phase_plan.yaml` 提供 `terrain_type` 与 `terrain_generator`。 
- `magiclab_rl_lab/scripts/automation/config_generator.py` 会把这些 plan 参数翻译成 Isaac Lab 的 `TerrainGeneratorCfg`。 
- `RandomGridTerrainCfg` 会被写成 `grid_height_range=(low, high)`。 
- `StairsTerrainCfg` 会被写成 `step_height_range=(0.05, d_max*0.25)`。 
- `GapTerrainCfg` 会被写成 `gap_width_range=(0.1, d_max*0.5)`。 
- `BoxesTerrainCfg` 会被写成 `box_height_range=(0.05, d_max*0.3)`。 
 也就是说，Isaac Lab 那边地形“怎么长出来”由训练计划决定，最终不是看 `deploy.yaml`，而是看 `training_plans/z1_5phase_plan.yaml` 经过 `config_generator.py` 生成后的 env cfg。 

## 3. MuJoCo 当前加载的地形高度与分布

这里列的是 `sim2sim/mujoco_manual.py` 当前真正实现的逻辑，不是“计划中应该有”的逻辑。MuJoCo 不从 `deploy.yaml` 读取 terrain，而是根据 `--phase` / `--terrain` 在 Python 里现生成 hfield。
````````````````````````````````````````````````

| 命令入口 | 实际 terrain | 分布 | 高度定义 | 备注 |
| --- | --- | --- | --- | --- |
| --phase p1 | flat | 100% flat | 无 hfield | 与 Isaac p1 一致 |
| --phase p2 | flat | 100% flat | 无 hfield | 与 Isaac p2 一致 |
| --phase p3 | p3 | 代码切片是约 flat 66.7% + random_grid 33.3% | MAX_ELEV=0.4m，再乘 terrain_difficulty | 注释写 70/30，但实际 section 切法更接近 2/3 + 1/3 |
| --phase p4 | legacy p3b | 约 flat 33.3% + random_grid 33.3% + stairs 16.7% + boxes 16.7% | MAX_ELEV=0.6m，再乘 terrain_difficulty | 没有 gap；与当前 Isaac p4 不一致 |
| --phase p5 | flat | 100% flat | 无专门映射 | 因为 PHASE_TERRAIN 里没有 p5 |
| --terrain p3 | p3 | 同上 | random_grid 高度大致 0.0~0.4m | 显式 terrain 优先于 phase |
| --terrain p3b | legacy p3b | 同上 | stairs 约 0.05~0.23m，boxes 约 0.0~0.4m | 旧代码路径仍保留 |

 关键不一致：当前 MuJoCo 没有实现与训练计划中 p4/p5 对应的 rough/full terrain 分布，也没有 gap。它目前只有 flat、gentle p3、以及 legacy p3b 近似地形。 

## 4. 当前最重要的结论

- 如果你现在按 `bestmodel_phase.json` 走，活跃模型只有 `p1_fine`、`p2_fine`、`p3_fine`。 
- `p3b` 已经是归档 phase，不应再作为“当前模型体系”的一部分。 
- Isaac Lab 当前 gentle terrain 是 `p3: 70% flat + 30% random_grid`，p3_fine 把 random_grid 上限提到 `0.35`。 
- MuJoCo 当前代码仍残留旧的 `p3b` 逻辑，并把 `p4` 错映射到它；`p5` 还没有接入。 
- 因此，当前 HTML 能回答“现在实际加载的是什么”，同时也明确暴露出 MuJoCo 端和当前训练计划之间的缺口。 
 Source files: `docs/tracking/bestmodel_phase.json`, `training_plans/z1_5phase_plan.yaml`, `sim2sim/mujoco_manual.py`, `magiclab_rl_lab/scripts/automation/config_generator.py`.