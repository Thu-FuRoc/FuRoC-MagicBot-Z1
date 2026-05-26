#!/usr/bin/env python3
"""
verify_retarget.py
==================
Visualize retargeted Z1 joint trajectories from walking_retargeted.npy.

Produces:
  - retarget_verify.png    : 14-subplot figure of joint angle time-series
  - retarget_symmetry.png  : L/R symmetry comparison
  - Console summary of per-joint statistics

Usage:
    python verify_retarget.py [--data PATH] [--fps 50]
"""

import argparse
import sys
from pathlib import Path

import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")  # Non-interactive backend for headless envs
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    print("WARNING: matplotlib not installed. Skipping plot generation.")
    print("         Install with: pip install matplotlib")


# --- Constants (must match retarget_bvh_to_z1.py) ----------------------------

Z1_JOINT_NAMES = [
    "JOINT_HIP_PITCH_L",   "JOINT_HIP_ROLL_L",    "JOINT_HIP_YAW_L",
    "JOINT_KNEE_PITCH_L",  "JOINT_ANKLE_PITCH_L",  "JOINT_ANKLE_ROLL_L",
    "JOINT_HIP_PITCH_R",   "JOINT_HIP_ROLL_R",     "JOINT_HIP_YAW_R",
    "JOINT_KNEE_PITCH_R",  "JOINT_ANKLE_PITCH_R",  "JOINT_ANKLE_ROLL_R",
    "joint_la1",           "joint_ra1",
]

Z1_JOINT_LIMITS = np.array([
    [-2.7925,  2.7925],   # HIP_PITCH_L
    [-0.524,   2.967 ],   # HIP_ROLL_L
    [-2.7925,  2.7925],   # HIP_YAW_L
    [ 0.0,     2.653 ],   # KNEE_PITCH_L
    [-0.873,   0.524 ],   # ANKLE_PITCH_L
    [-0.262,   0.262 ],   # ANKLE_ROLL_L
    [-2.7925,  2.7925],   # HIP_PITCH_R
    [-2.967,   0.524 ],   # HIP_ROLL_R
    [-2.7925,  2.7925],   # HIP_YAW_R
    [ 0.0,     2.653 ],   # KNEE_PITCH_R
    [-0.873,   0.524 ],   # ANKLE_PITCH_R
    [-0.262,   0.262 ],   # ANKLE_ROLL_R
    [-2.88,    2.88  ],   # joint_la1
    [-2.88,    2.88  ],   # joint_ra1
])

# Left/Right pairs for symmetry analysis
LR_PAIRS = [
    (0, 6,  "Hip Pitch"),
    (1, 7,  "Hip Roll"),
    (2, 8,  "Hip Yaw"),
    (3, 9,  "Knee Pitch"),
    (4, 10, "Ankle Pitch"),
    (5, 11, "Ankle Roll"),
    (12, 13, "Shoulder"),
]

# Joint groups for color coding
JOINT_GROUPS = {
    "Hip":      [0, 1, 2, 6, 7, 8],
    "Knee":     [3, 9],
    "Ankle":    [4, 5, 10, 11],
    "Shoulder": [12, 13],
}

GROUP_COLORS = {
    "Hip":      "#2196F3",
    "Knee":     "#FF9800",
    "Ankle":    "#4CAF50",
    "Shoulder": "#E91E63",
}


def get_joint_color(idx):
    for group, indices in JOINT_GROUPS.items():
        if idx in indices:
            return GROUP_COLORS[group]
    return "#666666"


def get_joint_group(idx):
    for group, indices in JOINT_GROUPS.items():
        if idx in indices:
            return group
    return "Unknown"


def plot_joint_trajectories(data, fps, output_path):
    """Plot all 14 joint angle trajectories with URDF limit bands."""
    n_frames, n_joints = data.shape
    time = np.arange(n_frames) / fps

    fig, axes = plt.subplots(7, 2, figsize=(16, 20))
    fig.suptitle("MagicBot-Z1 Retargeted Joint Trajectories", fontsize=16, fontweight="bold")

    for j_idx in range(n_joints):
        row = j_idx % 7
        col = j_idx // 7
        ax = axes[row, col]

        color = get_joint_color(j_idx)
        group = get_joint_group(j_idx)

        # Joint limit band
        lo, hi = Z1_JOINT_LIMITS[j_idx]
        ax.axhspan(lo, hi, alpha=0.08, color=color, label="URDF limits")
        ax.axhline(lo, color=color, alpha=0.3, linestyle="--", linewidth=0.8)
        ax.axhline(hi, color=color, alpha=0.3, linestyle="--", linewidth=0.8)

        # Zero line
        ax.axhline(0, color="#999999", alpha=0.4, linewidth=0.5)

        # Joint trajectory
        ax.plot(time, data[:, j_idx], color=color, linewidth=1.2, label=Z1_JOINT_NAMES[j_idx])

        ax.set_ylabel("rad", fontsize=8)
        ax.set_title(f"{Z1_JOINT_NAMES[j_idx]}  [{group}]", fontsize=9, fontweight="bold")
        ax.legend(fontsize=7, loc="upper right")
        ax.grid(True, alpha=0.2)
        ax.tick_params(labelsize=7)

        if row == 6:
            ax.set_xlabel("Time (s)", fontsize=9)

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.savefig(str(output_path), dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  [OK] Saved: {output_path}")


def plot_symmetry(data, fps, output_path):
    """Plot L vs R leg symmetry for each joint pair."""
    n_frames = data.shape[0]
    time = np.arange(n_frames) / fps

    n_pairs = len(LR_PAIRS)
    fig, axes = plt.subplots(n_pairs, 1, figsize=(14, 3 * n_pairs))
    fig.suptitle("Left vs Right Joint Symmetry Analysis", fontsize=16, fontweight="bold")

    for p_idx, (l_idx, r_idx, label) in enumerate(LR_PAIRS):
        ax = axes[p_idx]

        left_data = data[:, l_idx]
        right_data = data[:, r_idx]

        # For walking, L and R should be ~anti-phase (shifted by half cycle)
        ax.plot(time, left_data, color="#2196F3", linewidth=1.2, label=f"Left ({Z1_JOINT_NAMES[l_idx]})")
        ax.plot(time, right_data, color="#F44336", linewidth=1.2, alpha=0.8,
                label=f"Right ({Z1_JOINT_NAMES[r_idx]})")

        # Compute mean absolute difference (rough symmetry metric)
        diff = np.abs(left_data - right_data)
        mean_diff = np.mean(diff)
        ax.set_title(f"{label}  |  Mean |L-R| = {mean_diff:.4f} rad", fontsize=10, fontweight="bold")

        ax.set_ylabel("rad", fontsize=8)
        ax.legend(fontsize=7, loc="upper right")
        ax.grid(True, alpha=0.2)
        ax.axhline(0, color="#999999", alpha=0.4, linewidth=0.5)
        ax.tick_params(labelsize=7)

    axes[-1].set_xlabel("Time (s)", fontsize=9)

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.savefig(str(output_path), dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  [OK] Saved: {output_path}")


def print_summary(data, fps):
    """Print per-joint statistics to console."""
    n_frames, n_joints = data.shape
    duration = (n_frames - 1) / fps

    print(f"\n{'='*80}")
    print(f"  RETARGETED MOTION SUMMARY")
    print(f"{'='*80}")
    print(f"  Frames: {n_frames}  |  FPS: {fps:.0f} Hz  |  Duration: {duration:.2f}s")
    print(f"{'-'*80}")
    print(f"  {'Joint':<25} {'Min':>8} {'Max':>8} {'Range':>8} {'Mean':>8} {'Std':>8} {'AtLim%':>7}")
    print(f"  {'-'*25} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*7}")

    for j_idx in range(n_joints):
        col = data[:, j_idx]
        lo, hi = Z1_JOINT_LIMITS[j_idx]
        at_limit = np.sum((np.abs(col - lo) < 1e-6) | (np.abs(col - hi) < 1e-6))
        at_limit_pct = at_limit / n_frames * 100

        rng = col.max() - col.min()
        print(f"  {Z1_JOINT_NAMES[j_idx]:<25} {col.min():>8.4f} {col.max():>8.4f} "
              f"{rng:>8.4f} {col.mean():>8.4f} {col.std():>8.4f} {at_limit_pct:>6.1f}%")

    # Symmetry check
    print(f"\n  {'-'*80}")
    print(f"  SYMMETRY ANALYSIS (L vs R)")
    print(f"  {'-'*80}")
    print(f"  {'Pair':<20} {'Mean|L-R|':>10} {'Max|L-R|':>10} {'Corr(L,R)':>10}")
    print(f"  {'-'*20} {'-'*10} {'-'*10} {'-'*10}")

    for l_idx, r_idx, label in LR_PAIRS:
        left = data[:, l_idx]
        right = data[:, r_idx]
        diff = np.abs(left - right)
        corr = np.corrcoef(left, right)[0, 1] if left.std() > 1e-8 and right.std() > 1e-8 else 0.0
        print(f"  {label:<20} {diff.mean():>10.4f} {diff.max():>10.4f} {corr:>10.4f}")

    # Walking periodicity check
    print(f"\n  {'-'*80}")
    print(f"  PERIODICITY CHECK")
    print(f"  {'-'*80}")

    # Use hip pitch as the primary periodic signal
    for side, j_idx in [("Left Hip Pitch", 0), ("Right Hip Pitch", 6)]:
        signal = data[:, j_idx]
        if signal.std() < 1e-6:
            print(f"  {side}: no variation detected (constant signal)")
            continue

        # Simple zero-crossing based period detection
        mean_val = signal.mean()
        centered = signal - mean_val
        crossings = np.where(np.diff(np.sign(centered)))[0]
        if len(crossings) >= 4:
            # Full cycles = pairs of zero crossings
            half_periods = np.diff(crossings) / fps
            full_period = np.mean(half_periods) * 2
            print(f"  {side}: estimated period = {full_period:.3f}s "
                  f"({1/full_period:.1f} Hz, {len(crossings)//2} full cycles)")
        else:
            print(f"  {side}: too few zero-crossings to estimate period")

    print(f"\n{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(description="Verify retargeted Z1 joint trajectories")
    parser.add_argument("--data", type=str, default=None,
                        help="Path to walking_retargeted.npy (default: auto-detect)")
    parser.add_argument("--fps", type=float, default=50.0,
                        help="Frame rate of the retargeted data (default: 50 Hz)")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    data_path = Path(args.data) if args.data else script_dir / "walking_retargeted.npy"

    if not data_path.exists():
        print(f"ERROR: Data file not found: {data_path}")
        print(f"       Run retarget_bvh_to_z1.py first to generate it.")
        sys.exit(1)

    print(f"Loading retargeted data: {data_path}")
    data = np.load(str(data_path))
    print(f"  Shape: {data.shape}  ({data.shape[0]} frames x {data.shape[1]} joints)")

    assert data.shape[1] == 14, f"Expected 14 joints, got {data.shape[1]}"

    # Print summary
    print_summary(data, args.fps)

    # Generate plots
    if HAS_MPL:
        print("\nGenerating plots...")
        out_dir = Path("plots")
        out_dir.mkdir(exist_ok=True)
        
        # We need to recreate the plots calling the helper functions or directly
        # based on existing logic.
        plot_joint_trajectories(data, args.fps, out_dir / "retarget_verify.png")
        plot_symmetry(data, args.fps, out_dir / "retarget_symmetry.png")
    else:
        print("Skipping plots (matplotlib not available)")

    print("[DONE] Verification complete!")


if __name__ == "__main__":
    main()
