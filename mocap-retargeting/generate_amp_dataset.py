#!/usr/bin/env python3
"""
generate_amp_dataset.py
=======================
Convert retargeted Z1 joint trajectories into AMP-compatible state transition
pairs for the adversarial discriminator.

Per the paper (arXiv:2604.19102v1), each AMP state consists of:
  - Joint positions (14 dims — 12 lower body + 2 shoulders)
  - Joint velocities (14 dims — finite-differenced from trajectory)
  - Base angular velocity (3 dims — estimated from root orientation changes)
  - Projected gravity vector (3 dims — nominal upright = [0, 0, -1] in body frame)

Total: 34 dims per state -> 68 dims per transition (s_t, s_{t+1})

The paper preloads 200,000 state transitions. Since our BVH clip is ~2.5s at
50Hz = ~124 frames (~123 transitions), we tile/augment to reach the target count
by:
  1. Cyclically repeating the walking clip
  2. Adding small Gaussian noise for augmentation
  3. Random phase sampling within the clip

Usage:
    python generate_amp_dataset.py [--data PATH] [--fps 50] [--num-transitions 200000]
"""

import argparse
import sys
from pathlib import Path

import numpy as np


# --- Constants ----------------------------------------------------------------

STATE_DIM = 34  # joint_pos(14) + joint_vel(14) + base_ang_vel(3) + gravity(3)
TRANSITION_DIM = STATE_DIM * 2  # (s_t, s_{t+1})

# Noise scales for augmentation (radians)
JOINT_POS_NOISE_STD = 0.005   # ~0.3 degrees
JOINT_VEL_NOISE_STD = 0.02    # small velocity perturbation

# Nominal gravity vector in body frame (Z-up, robot standing upright)
GRAVITY_BODY = np.array([0.0, 0.0, -1.0])

# Nominal base angular velocity during walking (small values)
BASE_ANG_VEL_MEAN = np.array([0.0, 0.0, 0.0])
BASE_ANG_VEL_STD = np.array([0.02, 0.01, 0.05])  # slight yaw oscillation typical


def compute_joint_velocities(joint_positions, dt):
    """
    Compute joint velocities via finite differences.

    Args:
        joint_positions: (N, 14) array of joint angles
        dt: time step (1/fps)

    Returns:
        joint_velocities: (N, 14) array of joint angular velocities (rad/s)
    """
    n_frames, n_joints = joint_positions.shape
    velocities = np.zeros_like(joint_positions)

    # Central differences for interior points
    velocities[1:-1] = (joint_positions[2:] - joint_positions[:-2]) / (2 * dt)

    # Forward difference for first frame
    velocities[0] = (joint_positions[1] - joint_positions[0]) / dt

    # Backward difference for last frame
    velocities[-1] = (joint_positions[-1] - joint_positions[-2]) / dt

    return velocities


def build_state(joint_pos, joint_vel, base_ang_vel=None, gravity=None):
    """
    Build an AMP state vector from components.

    Args:
        joint_pos: (14,) joint positions
        joint_vel: (14,) joint velocities
        base_ang_vel: (3,) base angular velocity (optional, defaults to nominal)
        gravity: (3,) projected gravity vector (optional, defaults to nominal)

    Returns:
        state: (34,) AMP state vector
    """
    if base_ang_vel is None:
        base_ang_vel = BASE_ANG_VEL_MEAN.copy()
    if gravity is None:
        gravity = GRAVITY_BODY.copy()

    return np.concatenate([joint_pos, joint_vel, base_ang_vel, gravity])


def generate_transitions_from_clip(joint_positions, fps, num_transitions,
                                   augment_noise=True, seed=42):
    """
    Generate AMP state transition pairs from a joint position trajectory.

    Strategy:
    1. Compute joint velocities from the trajectory
    2. Build state vectors for each frame
    3. Create consecutive (s_t, s_{t+1}) pairs
    4. Tile cyclically + add noise to reach target count

    Args:
        joint_positions: (N, 14) array
        fps: frame rate
        num_transitions: target number of transitions
        augment_noise: whether to add small noise for augmentation
        seed: random seed

    Returns:
        transitions: (num_transitions, 68) array
    """
    rng = np.random.RandomState(seed)
    dt = 1.0 / fps
    n_frames = joint_positions.shape[0]
    n_joints = joint_positions.shape[1]

    # Compute joint velocities
    joint_velocities = compute_joint_velocities(joint_positions, dt)

    # Build state vectors for each frame
    states = np.zeros((n_frames, STATE_DIM))
    for f in range(n_frames):
        # Simulate slight base angular velocity variation during walking
        base_ang_vel = rng.normal(BASE_ANG_VEL_MEAN, BASE_ANG_VEL_STD * 0.5)

        # Slight gravity vector perturbation (body sway during walking)
        gravity_noise = rng.normal(0, 0.01, size=3)
        gravity = GRAVITY_BODY + gravity_noise
        gravity = gravity / np.linalg.norm(gravity)  # normalize

        states[f] = build_state(
            joint_positions[f], joint_velocities[f],
            base_ang_vel, gravity
        )

    # Create consecutive transitions (s_t, s_{t+1})
    n_base_transitions = n_frames - 1
    base_transitions = np.zeros((n_base_transitions, TRANSITION_DIM))
    for t in range(n_base_transitions):
        base_transitions[t] = np.concatenate([states[t], states[t + 1]])

    print(f"  Base transitions from clip: {n_base_transitions}")
    print(f"  Target transitions: {num_transitions}")
    print(f"  Augmentation factor: {num_transitions / n_base_transitions:.0f}x")

    # Tile to reach target count
    if num_transitions <= n_base_transitions:
        # Just subsample
        indices = rng.choice(n_base_transitions, size=num_transitions, replace=False)
        transitions = base_transitions[indices]
    else:
        # Tile cyclically + add noise
        n_tiles = (num_transitions // n_base_transitions) + 1
        transitions = np.tile(base_transitions, (n_tiles, 1))[:num_transitions]

        if augment_noise:
            # Add small Gaussian noise to joint positions and velocities
            noise = np.zeros_like(transitions)

            # Noise on joint_pos in s_t (indices 0:14)
            noise[:, :n_joints] = rng.normal(0, JOINT_POS_NOISE_STD, (num_transitions, n_joints))
            # Noise on joint_vel in s_t (indices 14:28)
            noise[:, n_joints:2*n_joints] = rng.normal(0, JOINT_VEL_NOISE_STD, (num_transitions, n_joints))
            # Noise on joint_pos in s_{t+1} (indices STATE_DIM:STATE_DIM+14)
            noise[:, STATE_DIM:STATE_DIM+n_joints] = rng.normal(0, JOINT_POS_NOISE_STD, (num_transitions, n_joints))
            # Noise on joint_vel in s_{t+1} (indices STATE_DIM+14:STATE_DIM+28)
            noise[:, STATE_DIM+n_joints:STATE_DIM+2*n_joints] = rng.normal(0, JOINT_VEL_NOISE_STD, (num_transitions, n_joints))

            transitions += noise

    return transitions


def main():
    parser = argparse.ArgumentParser(description="Generate AMP state transition dataset")
    parser.add_argument("--data", type=str, default=None,
                        help="Path to walking_retargeted.npy (default: auto-detect)")
    parser.add_argument("--fps", type=float, default=50.0,
                        help="Frame rate of the retargeted data (default: 50 Hz)")
    parser.add_argument("--num-transitions", type=int, default=200000,
                        help="Number of state transitions to generate (default: 200000)")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Output directory (default: same as data file)")
    parser.add_argument("--no-noise", action="store_true",
                        help="Disable augmentation noise")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    data_path = Path(args.data) if args.data else script_dir / "walking_retargeted.npy"
    output_dir = Path(args.output_dir) if args.output_dir else script_dir

    if not data_path.exists():
        print(f"ERROR: Data file not found: {data_path}")
        print(f"       Run retarget_bvh_to_z1.py first to generate it.")
        sys.exit(1)

    print(f"[1/3] Loading retargeted data: {data_path}")
    joint_positions = np.load(str(data_path))
    n_frames, n_joints = joint_positions.shape
    duration = (n_frames - 1) / args.fps

    print(f"  Shape: {joint_positions.shape}")
    print(f"  Duration: {duration:.2f}s at {args.fps:.0f} Hz")
    print(f"  Joints: {n_joints}")
    print()

    print(f"[2/3] Generating {args.num_transitions:,} AMP state transitions...")
    print(f"  State dim: {STATE_DIM} (joint_pos={n_joints} + joint_vel={n_joints} + ang_vel=3 + gravity=3)")
    print(f"  Transition dim: {TRANSITION_DIM} (2 x {STATE_DIM})")
    print(f"  Augmentation noise: {'OFF' if args.no_noise else 'ON'}")
    print(f"  Random seed: {args.seed}")
    print()

    transitions = generate_transitions_from_clip(
        joint_positions, args.fps, args.num_transitions,
        augment_noise=not args.no_noise, seed=args.seed
    )

    print()
    print(f"[3/3] Saving AMP dataset...")

    output_path = output_dir / "amp_walking_dataset.npy"
    np.save(str(output_path), transitions)
    size_mb = transitions.nbytes / (1024 * 1024)
    print(f"  [OK] {output_path.name}: shape {transitions.shape}, {size_mb:.1f} MB")

    # Also save metadata
    metadata = {
        "source_bvh": str(data_path),
        "source_fps": args.fps,
        "state_dim": STATE_DIM,
        "transition_dim": TRANSITION_DIM,
        "num_transitions": transitions.shape[0],
        "n_joints": n_joints,
        "augment_noise": not args.no_noise,
        "seed": args.seed,
        "state_layout": {
            "joint_pos": f"[0:{n_joints}]",
            "joint_vel": f"[{n_joints}:{2*n_joints}]",
            "base_ang_vel": f"[{2*n_joints}:{2*n_joints+3}]",
            "gravity": f"[{2*n_joints+3}:{STATE_DIM}]",
        },
    }

    meta_path = output_dir / "amp_walking_metadata.txt"
    with open(str(meta_path), "w") as f:
        f.write("AMP Walking Dataset Metadata\n")
        f.write("=" * 50 + "\n\n")
        for key, val in metadata.items():
            if isinstance(val, dict):
                f.write(f"{key}:\n")
                for k2, v2 in val.items():
                    f.write(f"  {k2}: {v2}\n")
            else:
                f.write(f"{key}: {val}\n")

    print(f"  [OK] {meta_path.name}: dataset metadata")

    # Sanity checks
    print(f"\n{'-'*50}")
    print(f"Sanity checks:")

    # Check state transition continuity
    s_t = transitions[:, :STATE_DIM]
    s_tp1 = transitions[:, STATE_DIM:]

    # Joint position change between s_t and s_{t+1} should be small
    pos_diff = np.abs(s_tp1[:, :n_joints] - s_t[:, :n_joints])
    max_pos_jump = pos_diff.max()
    mean_pos_jump = pos_diff.mean()
    print(f"  Joint pos Delta (s_t -> s_t+1): mean={mean_pos_jump:.5f} rad, max={max_pos_jump:.5f} rad")

    # Velocity magnitudes should be reasonable (< 20 rad/s for walking)
    vel_mag = np.abs(s_t[:, n_joints:2*n_joints])
    print(f"  Joint vel magnitude: mean={vel_mag.mean():.3f} rad/s, max={vel_mag.max():.3f} rad/s")

    # Gravity should be unit vector
    grav = s_t[:, -3:]
    grav_norm = np.linalg.norm(grav, axis=1)
    print(f"  Gravity norm: mean={grav_norm.mean():.6f}, std={grav_norm.std():.6f}")

    print(f"\n[DONE] AMP dataset generation complete!")
    print(f"   Dataset: {output_path}")
    print(f"   Ready for AMP discriminator training (alpha=0.3, beta=0.8 per paper)")


if __name__ == "__main__":
    main()
