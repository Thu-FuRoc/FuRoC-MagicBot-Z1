# `$plot-train-Z1` Skill Framework

这个 skill 是 “训练曲线与报告生产线”。它不负责训练本身，而负责从 RTX 服务器读取 TensorBoard 数据，生成曲线 PNG，把结果按 run 组织到本地，再编译成单页 PDF 报告。
核心定位：训练分析流水线 输入：远端 event files + 本地 best_models.json 强依赖 VPN / SSH / MikTeX / best_models.json 刷新 

## 1. Skill 的平台真源
``````````````

| 项 | 值 | 用途 |
| --- | --- | --- |
| SSH Host | phh@192.168.120.155 | 所有 TensorBoard 数据和曲线计算都从这台 RTX 拉 |
| Conda Env | isaaclab | 运行远端 plot 和 monitor 脚本 |
| Remote Project Root | ~/magiclab_rl_lab | 远端脚本和 logs 根 |
| Remote Log Root | ~/magiclab_rl_lab/logs/rsl_rl/magiclab_z1_12dof_velocity | event files、checkpoint、best_models 真正来源 |
| Remote Plot Script | ~/magiclab_rl_lab/scripts/plot_learning_curves.py | 远端生成 4 张曲线图 |
| Local Plot Root | D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/plots/ | 本地归档曲线目录 |
| Local PDF Script | D:/Desktop_Files/GPU-Train/RTX6000/Magicbot_Z1/scripts/gen_report_pdf.py | 本地把 PNG 组装成 PDF/TEX/MD |

## 2. Skill 的核心数据流

```
远端 TensorBoard event files
  -> 远端 plot_learning_curves.py
  -> 远端 plots/*.png
  -> scp 回本地
  -> 本地按 alias 整理到 plots//
  -> 刷新 best_models.json
  -> 本地 gen_report_pdf.py
  -> 产出 report_.pdf / .tex / .md
```

 这个 skill 的真正目标不是“画一张图”，而是生成一整套可交付的训练分析包：4 图、PDF、TEX、MD，以及必要时更新 README / tracking。 

## 3. Skill 的命令模式
``````````````````````

| 模式 | 意图 | 典型动作 |
| --- | --- | --- |
| 默认 | 重画全部图并生成一个当前 run 报告 | 远端跑 plot，下载 PNG，刷新 best_models.json，本地编 PDF |
| --focus <RUN> | 聚焦某个 run | 用 --focus_run 在远端只画该 run |
| --sync | 显式强调“重新同步” | 本质上还是重跑默认流程 |
| --update-readme | 只更新本地 plot README | 不重新跑远端图，仅读已有结果 + best_models.json |
| --all-runs | 批量产出所有显著 run 的图和 PDF | 多次 focus 循环 |
| --pipeline | 按 bestmodel_phase.json 批量为 pipeline 出报告 | 读取 tracking JSON，再按 alias 批量跑 |
| --pdf-only <RUN> | 已有 PNG，只重编 PDF | 刷新 best_models.json 后直接本地编译 |

## 4. 本地目录结构含义
````````````````

| 路径 | 角色 |
| --- | --- |
| plots/B_custom_curriculum/<alias>/ | 旧 5-phase coarse/fine 方案的报告目录 |
| plots/p1、plots/p2、plots/p3 | A_legged_gym 这条线的本地单 phase 报告目录 |
| plots/phase/p1..p3 | phase 简化镜像目录，更多偏展示组织层 |
| best_models.json | 聚合训练健康状态，PDF 里的 peak / latest / overfitting 说明都依赖它 |
| docs/tracking/bestmodel_phase.json | 给 --pipeline 提供 run alias 级别的 phase 路由信息 |

## 5. 图表子系统是什么
``````````````

| 输出文件 | 意义 |
| --- | --- |
| 1_reward_trend.png | 总 reward 随训练变化，标出 peak、best checkpoint、current |
| 2_reward_decomposition.png | reward component 分解，看哪些项在主导训练 |
| 3_termination.png | 终止原因和 episode length，适合判断是否摔倒、是否超时占主导 |
| 4_efficiency.png | 吞吐、学习率、熵等训练效率信号 |
| report_*.pdf | 给人看的单页分析报告 |
| report_*.tex | 可追踪 LaTeX 源 |
| report_*.md | 可读文本摘要 |

## 6. 为什么总要先刷新 `best_models.json`

- 因为单纯读 TensorBoard 只能画出曲线，不足以稳定给出“best checkpoint、peak reward、latest reward、overfitting”这些摘要指标。 
- `train_monitor.py --once` 会把这些汇总成结构化 JSON。 
- `gen_report_pdf.py` 再消费这个 JSON，生成更完整的中文/英文叙述。 
 所以这个 skill 实际上由两个子系统组成：**远端曲线生成器** + **本地报告编译器**。中间的桥就是 `best_models.json`。 

## 7. 失败模式
````

| 失败点 | 表现 | 应对 |
| --- | --- | --- |
| VPN / SSH 不通 | 无法连上 RTX | 先确认 aTrust VPN |
| 远端脚本不存在 | plot_learning_curves.py 找不到 | 用本地同名脚本补齐到远端 |
| 事件文件缺失 | 没有可画的 run | 检查训练是否真的跑过，或日志是否被清理 |
| best_models 未刷新 | PDF 里只有 fallback 信息或指标过旧 | 先跑 train_monitor.py --once |
| MikTeX / pdflatex 缺失 | PDF 编译失败 | 本地只保留 PNG / MD / TEX，或修好 TeX 环境 |

## 8. Skill 的边界
``

| 会做 | 不会做 |
| --- | --- |
| 组织分析产物、生成 PDF 报告、按 run 切分曲线 | 启动训练、修改 reward、替你决定训练策略 |
| 批量同步 pipeline 的图和报告 | 在无 event files 的情况下凭空造曲线 |
| 把训练指标标准化为可读文档 | 替代 gpu-train 去做进程运维和 GPU 管理 |