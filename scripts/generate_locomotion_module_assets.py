from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib import rcParams


ROOT = Path(r"D:\Desktop_Files\GPU-Train\RTX6000\Magicbot_Z1\docs\plans\locomotion_module")
PNG_DIR = ROOT / "assets" / "png"

rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
rcParams["axes.unicode_minus"] = False


def box(ax, x, y, w, h, fc, ec, title, lines, title_color="#0f172a"):
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.03",
        linewidth=2.2, facecolor=fc, edgecolor=ec
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h * 0.78, title, ha="center", va="center", fontsize=18, weight="bold", color=title_color)
    base_y = y + h * 0.54
    for i, line in enumerate(lines):
        ax.text(x + w / 2, base_y - i * h * 0.16, line, ha="center", va="center", fontsize=11.5, color="#334155")


def save(fig, name):
    PNG_DIR.mkdir(parents=True, exist_ok=True)
    out = PNG_DIR / name
    fig.savefig(out, dpi=180, bbox_inches="tight", facecolor="#f8fafc")
    plt.close(fig)


def phase_map():
    fig, ax = plt.subplots(figsize=(14, 8.5))
    fig.patch.set_facecolor("#f8fafc")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.5, 0.95, "Locomotion 训练阶段路线图", ha="center", fontsize=24, weight="bold", color="#0f172a")
    ax.text(0.5, 0.91, "从平地站稳与速度跟踪，逐步过渡到地形与鲁棒性训练", ha="center", fontsize=11, color="#475569")

    xs = [0.05, 0.24, 0.43, 0.62, 0.81]
    titles = ["P1", "P2", "P3", "P4", "P5"]
    subtitles = [
        ["平地 Bootstrap", "站稳、基本平衡"],
        ["平地速度跟踪", "基础 checkpoint: P2 Fine"],
        ["轻地形 + 轻扰动", "当前训练: P3 Coarse"],
        ["粗糙地形", "复杂接触与姿态恢复"],
        ["全地形 + 打磨", "综合性能与泛化"],
    ]
    colors = [
        ("#dbeafe", "#2563eb"),
        ("#dcfce7", "#16a34a"),
        ("#fef3c7", "#d97706"),
        ("#fde68a", "#ca8a04"),
        ("#fee2e2", "#dc2626"),
    ]
    for x, t, sub, c in zip(xs, titles, subtitles, colors):
        box(ax, x, 0.63, 0.14, 0.18, c[0], c[1], t, sub, title_color=c[1])
    for x in [0.19, 0.38, 0.57, 0.76]:
        ax.annotate("", xy=(x + 0.04, 0.72), xytext=(x, 0.72), arrowprops=dict(arrowstyle="->", lw=2.2, color="#64748b"))

    box(ax, 0.09, 0.18, 0.24, 0.23, "#ecfccb", "#65a30d", "已有基础", ["平地速度跟踪", "基本 stop 能力", "基础姿态稳定"], title_color="#3f6212")
    box(ax, 0.38, 0.18, 0.24, 0.23, "#fff7ed", "#ea580c", "新增课程", ["standing envs 增加", "interval force / torque", "更频繁命令切换"], title_color="#c2410c")
    box(ax, 0.67, 0.18, 0.24, 0.23, "#eff6ff", "#2563eb", "目标能力", ["速度归零后站稳", "受扰动后自平衡", "进入复杂 terrain 前稳住"], title_color="#1d4ed8")
    save(fig, "locomotion_phase_map.png")


def disturbance_map():
    fig, ax = plt.subplots(figsize=(14, 8.8))
    fig.patch.set_facecolor("#f8fafc")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.5, 0.95, "Locomotion 鲁棒策略分解图", ha="center", fontsize=24, weight="bold", color="#0f172a")
    ax.text(0.5, 0.91, "将停得住与抗干扰拆成不同训练信号，而不是只靠单一 reward", ha="center", fontsize=11, color="#475569")

    box(ax, 0.08, 0.54, 0.38, 0.3, "#ffffff", "#cbd5e1", "A. 速度归零后保持静止", [], title_color="#0f172a")
    box(ax, 0.12, 0.64, 0.12, 0.1, "#dcfce7", "#16a34a", "standing envs", ["增加零命令样本"], title_color="#166534")
    box(ax, 0.29, 0.64, 0.12, 0.1, "#dbeafe", "#2563eb", "resampling", ["更频繁切换命令"], title_color="#1d4ed8")
    box(ax, 0.205, 0.56, 0.12, 0.08, "#fef3c7", "#d97706", "stand_still", ["抑制残余动作"], title_color="#b45309")

    box(ax, 0.54, 0.54, 0.38, 0.3, "#ffffff", "#cbd5e1", "B. 受到扰动后自平衡", [], title_color="#0f172a")
    box(ax, 0.58, 0.64, 0.12, 0.1, "#fee2e2", "#dc2626", "velocity push", ["速度状态恢复"], title_color="#b91c1c")
    box(ax, 0.75, 0.64, 0.12, 0.1, "#ffedd5", "#ea580c", "force / torque", ["真实外力外矩"], title_color="#c2410c")
    box(ax, 0.665, 0.56, 0.12, 0.08, "#e0f2fe", "#0284c7", "reset", ["轻度失衡恢复"], title_color="#0369a1")

    box(ax, 0.16, 0.16, 0.24, 0.16, "#f1f5f9", "#64748b", "velocity push", ["更偏向速度误差如何收回来", "相当于状态层面的冲击"], title_color="#334155")
    box(ax, 0.60, 0.16, 0.24, 0.16, "#f1f5f9", "#64748b", "interval force / torque", ["更偏向姿态与支撑如何恢复", "相当于物理层面的冲击"], title_color="#334155")
    ax.text(0.5, 0.38, "两类扰动不是替代关系，而是互补关系", ha="center", fontsize=16, weight="bold", color="#0f172a")
    save(fig, "disturbance_strategy_map.png")


def tuning_map():
    fig, ax = plt.subplots(figsize=(14, 8.5))
    fig.patch.set_facecolor("#f8fafc")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.5, 0.95, "Locomotion 调参逻辑图", ha="center", fontsize=24, weight="bold", color="#0f172a")
    ax.text(0.5, 0.91, "先判断问题属于跟踪、静止还是抗扰，再决定调 reward、课程还是扰动强度", ha="center", fontsize=11, color="#475569")

    box(ax, 0.08, 0.60, 0.84, 0.18, "#ffffff", "#cbd5e1", "先看什么", [], title_color="#0f172a")
    box(ax, 0.12, 0.64, 0.12, 0.08, "#dbeafe", "#2563eb", "reward", ["趋势"], title_color="#1d4ed8")
    box(ax, 0.30, 0.64, 0.12, 0.08, "#dcfce7", "#16a34a", "episode length", ["稳定性"], title_color="#15803d")
    box(ax, 0.48, 0.64, 0.12, 0.08, "#fef3c7", "#d97706", "bad_orientation", ["失稳来源"], title_color="#b45309")
    box(ax, 0.66, 0.64, 0.18, 0.08, "#fee2e2", "#dc2626", "stand_still / feet_slide", ["行为质量"], title_color="#b91c1c")

    box(ax, 0.05, 0.16, 0.26, 0.30, "#ffffff", "#cbd5e1", "问题 1：跟踪差", ["先查扰动是否过强", "再看跟踪 reward 是否太低", "最后再看 PPO 超参数"], title_color="#0f172a")
    box(ax, 0.37, 0.16, 0.26, 0.30, "#ffffff", "#cbd5e1", "问题 2：停不稳", ["增加 rel_standing_envs", "缩短命令切换时间", "适度加大 stand_still"], title_color="#0f172a")
    box(ax, 0.69, 0.16, 0.26, 0.30, "#ffffff", "#cbd5e1", "问题 3：一受扰就倒", ["保留轻 push，再加 force/torque", "扩大 reset 速度与姿态范围", "观察 bad_orientation 是否回落"], title_color="#0f172a")
    save(fig, "tuning_logic_map.png")


def recovery_map():
    fig, ax = plt.subplots(figsize=(14, 8.5))
    fig.patch.set_facecolor("#f8fafc")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.5, 0.95, "Recovery / Get-up 任务边界图", ha="center", fontsize=24, weight="bold", color="#0f172a")
    ax.text(0.5, 0.91, "区分当前主线正在解决的轻度失衡恢复，与后续可能单开的跌倒起身任务", ha="center", fontsize=11, color="#475569")

    box(ax, 0.08, 0.22, 0.35, 0.56, "#ffffff", "#cbd5e1", "A. 当前 locomotion 主线", ["速度偏差恢复", "轻度姿态偏差恢复", "站立与行进中的外扰恢复"], title_color="#0f172a")
    box(ax, 0.57, 0.22, 0.35, 0.56, "#ffffff", "#cbd5e1", "B. 单开的 recovery / get-up", ["侧躺 / 仰卧 / 趴卧起身", "更宽松 termination", "单独的起身 reward 与课程"], title_color="#0f172a")
    box(ax, 0.18, 0.08, 0.64, 0.09, "#ffffff", "#94a3b8", "结论", ["当前先把 stop-to-stand 和 push recovery 做稳；跌倒起身更适合单开任务"], title_color="#334155")
    save(fig, "recovery_getup_map.png")


def module_landscape_map():
    fig, ax = plt.subplots(figsize=(14, 9))
    fig.patch.set_facecolor("#f8fafc")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.text(0.5, 0.95, "运动控制小脑训练模块地图", ha="center", fontsize=24, weight="bold", color="#0f172a")
    ax.text(0.5, 0.91, "当前 Locomotion 专题只是一个入门样例，后续还可以并列扩展更多训练模块", ha="center", fontsize=11, color="#475569")

    center = plt.Circle((0.5, 0.48), 0.10, color="#dbeafe", ec="#2563eb", lw=3)
    ax.add_patch(center)
    ax.text(0.5, 0.50, "Locomotion", ha="center", va="center", fontsize=20, weight="bold", color="#1d4ed8")
    ax.text(0.5, 0.45, "入门样例", ha="center", va="center", fontsize=15, color="#1e293b")

    box(ax, 0.08, 0.20, 0.18, 0.12, "#ffffff", "#94a3b8", "Recovery / Get-up", ["跌倒后恢复 / 起身"], title_color="#334155")
    box(ax, 0.10, 0.72, 0.18, 0.12, "#ffffff", "#94a3b8", "基础 Locomotion", ["站稳 / 走路 / 停止"], title_color="#334155")
    box(ax, 0.39, 0.76, 0.22, 0.12, "#ecfccb", "#65a30d", "当前 Z1 样例", ["P1-P5 + robustness"], title_color="#3f6212")
    box(ax, 0.72, 0.72, 0.18, 0.12, "#ffffff", "#94a3b8", "Terrain Robustness", ["地形泛化 / 抗扰动"], title_color="#334155")
    box(ax, 0.74, 0.20, 0.18, 0.12, "#ffffff", "#94a3b8", "Perception-Conditioned", ["结合感知的运动控制"], title_color="#334155")
    box(ax, 0.29, 0.06, 0.18, 0.12, "#ffffff", "#94a3b8", "Imitation", ["演示学习步态"], title_color="#334155")
    box(ax, 0.53, 0.06, 0.18, 0.12, "#ffffff", "#94a3b8", "Sim-to-Real", ["域随机化 / 参数泛化"], title_color="#334155")

    for (x, y) in [(0.19, 0.32), (0.19, 0.72), (0.50, 0.76), (0.81, 0.72), (0.83, 0.32), (0.38, 0.18), (0.62, 0.18)]:
        ax.annotate("", xy=(x, y), xytext=(0.5, 0.48), arrowprops=dict(arrowstyle="-", lw=2.2, color="#94a3b8"))
    save(fig, "module_landscape_map.png")


if __name__ == "__main__":
    phase_map()
    disturbance_map()
    tuning_map()
    recovery_map()
    module_landscape_map()
    print("generated", PNG_DIR)
