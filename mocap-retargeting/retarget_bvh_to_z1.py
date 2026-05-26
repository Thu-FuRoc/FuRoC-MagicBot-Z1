#!/usr/bin/env python3
"""
retarget_bvh_to_z1.py
=====================
Retarget CMU-format BVH walking mocap to MagicBot-Z1 joint space.

Produces:
  - walking_retargeted.npy  : (N_frames, 14) array of Z1 joint angles in radians
  - walking_retargeted.csv  : human-readable version with column headers

MagicBot-Z1 actuated joints (14 total):
  Lower body (12):
    0  JOINT_HIP_PITCH_L     (Y-axis)
    1  JOINT_HIP_ROLL_L      (X-axis)
    2  JOINT_HIP_YAW_L       (Z-axis)
    3  JOINT_KNEE_PITCH_L    (Y-axis)
    4  JOINT_ANKLE_PITCH_L   (Y-axis)
    5  JOINT_ANKLE_ROLL_L    (X-axis)
    6  JOINT_HIP_PITCH_R     (Y-axis)
    7  JOINT_HIP_ROLL_R      (X-axis)
    8  JOINT_HIP_YAW_R       (Z-axis)
    9  JOINT_KNEE_PITCH_R    (Y-axis)
    10 JOINT_ANKLE_PITCH_R   (Y-axis)
    11 JOINT_ANKLE_ROLL_R    (X-axis)
  Upper body (2 — only revolute joints):
    12 joint_la1  (shoulder L, axis=[0, 0.99255, -0.12187])
    13 joint_ra1  (shoulder R, axis=[0, 0.99255, -0.12187])

BVH coordinate system:  Y-up, Z-forward
Z1  coordinate system:  Z-up, X-forward

Usage:
    python retarget_bvh_to_z1.py [--bvh PATH] [--target-fps 50] [--output-dir DIR]
"""

import argparse
import os
import re
import sys
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation


# --- Z1 URDF joint limits (radians) -------------------------------------------

Z1_JOINT_NAMES = [
    "JOINT_HIP_PITCH_L",   "JOINT_HIP_ROLL_L",    "JOINT_HIP_YAW_L",
    "JOINT_KNEE_PITCH_L",  "JOINT_ANKLE_PITCH_L",  "JOINT_ANKLE_ROLL_L",
    "JOINT_HIP_PITCH_R",   "JOINT_HIP_ROLL_R",     "JOINT_HIP_YAW_R",
    "JOINT_KNEE_PITCH_R",  "JOINT_ANKLE_PITCH_R",  "JOINT_ANKLE_ROLL_R",
    "joint_la1",           "joint_ra1",
]

Z1_JOINT_LIMITS = np.array([
    # lower,   upper
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
    [-2.88,    2.88  ],   # joint_la1  (shoulder L)
    [-2.88,    2.88  ],   # joint_ra1  (shoulder R)
])


# --- BVH Parser --------------------------------------------------------------

class BVHJoint:
    """Represents a single joint in the BVH hierarchy."""
    def __init__(self, name, parent=None):
        self.name = name
        self.parent = parent
        self.children = []
        self.offset = np.zeros(3)
        self.channels = []
        self.channel_indices = []  # indices into the frame data array

    def __repr__(self):
        return f"BVHJoint({self.name}, channels={self.channels})"


def parse_bvh(filepath):
    """
    Parse a BVH file and return:
      - joints: dict  name -> BVHJoint
      - root_name: str
      - frames: np.ndarray  (num_frames, num_channels)
      - frame_time: float  (seconds per frame)
    """
    with open(filepath, "r") as f:
        lines = f.readlines()

    joints = {}
    joint_stack = []
    root_name = None
    channel_offset = 0
    i = 0

    # -- Parse HIERARCHY --
    while i < len(lines):
        line = lines[i].strip()
        i += 1

        if line.startswith("MOTION"):
            break

        # ROOT or JOINT
        m = re.match(r"(ROOT|JOINT)\s+(\S+)", line)
        if m:
            jtype, jname = m.group(1), m.group(2)
            parent = joint_stack[-1] if joint_stack else None
            joint = BVHJoint(jname, parent)
            if parent:
                parent.children.append(joint)
            joints[jname] = joint
            if jtype == "ROOT":
                root_name = jname
            continue

        if line == "{":
            # push the most recently created joint
            last_joint_name = list(joints.keys())[-1]
            joint_stack.append(joints[last_joint_name])
            continue

        if line == "}":
            joint_stack.pop()
            continue

        if line.startswith("OFFSET"):
            parts = line.split()
            joint_stack[-1].offset = np.array([float(parts[1]), float(parts[2]), float(parts[3])])
            continue

        if line.startswith("CHANNELS"):
            parts = line.split()
            n_channels = int(parts[1])
            channel_names = parts[2:2+n_channels]
            joint_stack[-1].channels = channel_names
            joint_stack[-1].channel_indices = list(range(channel_offset, channel_offset + n_channels))
            channel_offset += n_channels
            continue

        if line.startswith("End Site"):
            # Skip End Site block
            while i < len(lines) and "}" not in lines[i]:
                i += 1
            i += 1  # skip the closing brace
            continue

    # -- Parse MOTION --
    num_frames = 0
    frame_time = 0.0
    frame_data = []

    while i < len(lines):
        line = lines[i].strip()
        i += 1

        if line.startswith("Frames:"):
            num_frames = int(line.split(":")[1].strip())
        elif line.startswith("Frame Time:"):
            frame_time = float(line.split(":")[1].strip())
        elif line:
            values = [float(v) for v in line.split()]
            frame_data.append(values)

    frames = np.array(frame_data)
    assert frames.shape[0] == num_frames, f"Expected {num_frames} frames, got {frames.shape[0]}"

    return joints, root_name, frames, frame_time


# --- Rotation utilities ------------------------------------------------------

def bvh_channels_to_rotation(channels, values):
    """
    Convert BVH channel values (in degrees) to a scipy Rotation.
    BVH channels are applied in the order listed (intrinsic).

    Returns a scipy Rotation object.
    """
    # Build rotation by composing individual axis rotations
    rot = Rotation.identity()

    for ch, val in zip(channels, values):
        angle_rad = np.radians(val)
        ch_lower = ch.lower()
        if "xrotation" in ch_lower:
            rot = rot * Rotation.from_euler("x", angle_rad)
        elif "yrotation" in ch_lower:
            rot = rot * Rotation.from_euler("y", angle_rad)
        elif "zrotation" in ch_lower:
            rot = rot * Rotation.from_euler("z", angle_rad)
        # skip position channels

    return rot


def get_joint_rotation(joint, frame_data):
    """Extract the local rotation for a joint from one frame of BVH data."""
    if not joint.channels:
        return Rotation.identity()

    # Filter only rotation channels
    rot_channels = []
    rot_values = []
    for ch, idx in zip(joint.channels, joint.channel_indices):
        if "rotation" in ch.lower():
            rot_channels.append(ch)
            rot_values.append(frame_data[idx])

    if not rot_channels:
        return Rotation.identity()

    return bvh_channels_to_rotation(rot_channels, rot_values)


def get_chain_rotation(joints, chain_names, frame_data):
    """
    Compute the cumulative local rotation through a chain of BVH joints.
    This is the composed rotation: R_joint1 * R_joint2 * ... * R_jointN
    (used when intermediate joints like LHipJoint have rotation channels that
    need to be combined with the child joint).
    """
    rot = Rotation.identity()
    for name in chain_names:
        if name in joints:
            rot = rot * get_joint_rotation(joints[name], frame_data)
    return rot


# --- Coordinate transform: BVH -> Z1 -----------------------------------------
#
# BVH (CMU):  Y-up, Z-forward, X-right  (right-handed)
# Z1 (URDF):  Z-up, X-forward, Y-left   (right-handed)
#
# Proper rotation (det=+1) mapping:
#   BVH-X (right)   -> Z1-Y (left)     same physical direction
#   BVH-Y (up)      -> Z1-Z (up)       same physical direction
#   BVH-Z (forward) -> Z1-X (forward)  same physical direction
#
# As a rotation matrix (columns = where BVH axes go in Z1):
#   [ 0  0  1 ]   Z1-X = BVH-Z
#   [ 1  0  0 ]   Z1-Y = BVH-X
#   [ 0  1  0 ]   Z1-Z = BVH-Y

R_BVH_TO_Z1 = np.array([
    [0,  0,  1],
    [1,  0,  0],
    [0,  1,  0],
], dtype=float)

R_COORD = Rotation.from_matrix(R_BVH_TO_Z1)


def decompose_to_z1_hip(rot_bvh):
    """
    Decompose a BVH hip rotation into Z1 hip joint angles.

    Z1 hip chain: pelvis -> hip_pitch (Y) -> hip_roll (X) -> hip_yaw (Z)
    We decompose in the Z1 frame using intrinsic YXZ order.

    Returns: (pitch, roll, yaw) in radians
    """
    # Transform rotation from BVH frame to Z1 frame
    rot_z1 = R_COORD * rot_bvh * R_COORD.inv()

    # Decompose as intrinsic Y-X-Z (pitch-roll-yaw)
    # scipy convention: 'YXZ' intrinsic = specify as lowercase 'yxz' with intrinsic
    try:
        angles = rot_z1.as_euler("YXZ", degrees=False)
    except ValueError:
        angles = np.zeros(3)

    pitch, roll, yaw = angles[0], angles[1], angles[2]
    return pitch, roll, yaw


def decompose_to_z1_knee(rot_bvh):
    """
    Decompose BVH knee rotation to Z1 knee pitch.
    Z1 knee is single-axis (Y), range [0, 2.653].
    """
    rot_z1 = R_COORD * rot_bvh * R_COORD.inv()

    # Extract pitch (Y-axis rotation)
    try:
        euler = rot_z1.as_euler("YXZ", degrees=False)
    except ValueError:
        euler = np.zeros(3)

    # Knee pitch: take absolute value or negate depending on convention
    # BVH knee flexion is typically positive X-rotation -> maps to positive Y in Z1
    return euler[0]


def decompose_to_z1_ankle(rot_bvh):
    """
    Decompose BVH ankle rotation to Z1 ankle pitch + roll.
    Z1 ankle chain: ankle_pitch (Y) -> ankle_roll (X)
    """
    rot_z1 = R_COORD * rot_bvh * R_COORD.inv()

    try:
        # Decompose as Y then X (pitch then roll)
        euler = rot_z1.as_euler("YXZ", degrees=False)
    except ValueError:
        euler = np.zeros(3)

    pitch = euler[0]
    roll = euler[1]
    return pitch, roll


def decompose_to_z1_shoulder(rot_bvh, side="left"):
    """
    Decompose BVH shoulder rotation to Z1 shoulder joint (la1 or ra1).

    Z1 shoulder axis = [0, 0.99255, -0.12187] (tilted Y-axis).
    We project the BVH rotation onto this axis to get a single angle.
    """
    rot_z1 = R_COORD * rot_bvh * R_COORD.inv()

    # The shoulder axis in Z1 frame (normalized)
    axis = np.array([0, 0.99255, -0.12187])
    axis = axis / np.linalg.norm(axis)

    # Extract the rotation angle about this axis using axis-angle representation
    rotvec = rot_z1.as_rotvec()
    # Project onto shoulder axis
    angle = np.dot(rotvec, axis)

    return angle


# --- Retargeting --------------------------------------------------------------

def retarget_frame(joints, frame_data):
    """
    Retarget one BVH frame to Z1 joint angles.
    Returns: np.ndarray of shape (14,) — Z1 joint angles in radians.
    """
    z1_joints = np.zeros(14)

    # -- Left leg --
    # BVH chain: Hips -> LHipJoint -> LeftUpLeg -> LeftLeg -> LeftFoot
    # LHipJoint is a virtual joint (zero offset) that adds rotation before LeftUpLeg
    left_hip_rot = get_chain_rotation(joints, ["LHipJoint", "LeftUpLeg"], frame_data)
    pitch, roll, yaw = decompose_to_z1_hip(left_hip_rot)
    z1_joints[0] = pitch   # HIP_PITCH_L
    z1_joints[1] = roll    # HIP_ROLL_L
    z1_joints[2] = yaw     # HIP_YAW_L

    left_knee_rot = get_joint_rotation(joints["LeftLeg"], frame_data)
    z1_joints[3] = decompose_to_z1_knee(left_knee_rot)   # KNEE_PITCH_L

    left_ankle_rot = get_joint_rotation(joints["LeftFoot"], frame_data)
    ankle_pitch, ankle_roll = decompose_to_z1_ankle(left_ankle_rot)
    z1_joints[4] = ankle_pitch   # ANKLE_PITCH_L
    z1_joints[5] = ankle_roll    # ANKLE_ROLL_L

    # -- Right leg --
    right_hip_rot = get_chain_rotation(joints, ["RHipJoint", "RightUpLeg"], frame_data)
    pitch, roll, yaw = decompose_to_z1_hip(right_hip_rot)
    z1_joints[6] = pitch   # HIP_PITCH_R
    z1_joints[7] = roll    # HIP_ROLL_R
    z1_joints[8] = yaw     # HIP_YAW_R

    right_knee_rot = get_joint_rotation(joints["RightLeg"], frame_data)
    z1_joints[9] = decompose_to_z1_knee(right_knee_rot)   # KNEE_PITCH_R

    right_ankle_rot = get_joint_rotation(joints["RightFoot"], frame_data)
    ankle_pitch, ankle_roll = decompose_to_z1_ankle(right_ankle_rot)
    z1_joints[10] = ankle_pitch   # ANKLE_PITCH_R
    z1_joints[11] = ankle_roll    # ANKLE_ROLL_R

    # -- Upper body (shoulders only — other joints are fixed in Z1 URDF) --
    # BVH chain: Spine1 -> LeftShoulder -> LeftArm
    if "LeftShoulder" in joints and "LeftArm" in joints:
        left_shoulder_rot = get_chain_rotation(joints, ["LeftShoulder", "LeftArm"], frame_data)
        z1_joints[12] = decompose_to_z1_shoulder(left_shoulder_rot, "left")

    if "RightShoulder" in joints and "RightArm" in joints:
        right_shoulder_rot = get_chain_rotation(joints, ["RightShoulder", "RightArm"], frame_data)
        z1_joints[13] = decompose_to_z1_shoulder(right_shoulder_rot, "right")

    return z1_joints


def clamp_to_limits(joint_angles):
    """Clamp joint angles to Z1 URDF limits."""
    return np.clip(joint_angles, Z1_JOINT_LIMITS[:, 0], Z1_JOINT_LIMITS[:, 1])


def downsample_fps(frames, source_fps, target_fps):
    """
    Downsample frame data from source_fps to target_fps.
    Uses linear interpolation for smooth resampling.

    The paper runs the policy at 50 Hz, so we downsample the 120 fps BVH data.
    This ensures the AMP discriminator sees transitions at the correct time scale.
    """
    source_dt = 1.0 / source_fps
    target_dt = 1.0 / target_fps
    n_source = frames.shape[0]
    duration = (n_source - 1) * source_dt

    n_target = int(np.floor(duration / target_dt)) + 1
    target_times = np.arange(n_target) * target_dt
    source_times = np.arange(n_source) * source_dt

    # Interpolate each joint dimension
    n_dims = frames.shape[1]
    result = np.zeros((n_target, n_dims))
    for d in range(n_dims):
        result[:, d] = np.interp(target_times, source_times, frames[:, d])

    return result, target_fps


# --- Main ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Retarget CMU BVH to MagicBot-Z1 joints")
    parser.add_argument("--bvh", type=str, default=None,
                        help="Path to BVH file (default: 02_02.bvh in same directory)")
    parser.add_argument("--target-fps", type=float, default=50.0,
                        help="Target frame rate in Hz (default: 50, matching Z1 control frequency)")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Output directory (default: same as BVH file)")
    args = parser.parse_args()

    # Resolve paths
    script_dir = Path(__file__).resolve().parent
    bvh_path = Path(args.bvh) if args.bvh else script_dir / "02_02.bvh"
    output_dir = Path(args.output_dir) if args.output_dir else script_dir

    if not bvh_path.exists():
        print(f"ERROR: BVH file not found: {bvh_path}")
        sys.exit(1)

    print(f"[1/5] Parsing BVH: {bvh_path}")
    joints, root_name, frames, frame_time = parse_bvh(str(bvh_path))

    source_fps = 1.0 / frame_time
    n_frames = frames.shape[0]
    n_channels = frames.shape[1]
    duration = (n_frames - 1) * frame_time

    print(f"       Root: {root_name}")
    print(f"       Joints: {len(joints)}")
    print(f"       Channels: {n_channels}")
    print(f"       Frames: {n_frames}")
    print(f"       Source FPS: {source_fps:.1f}")
    print(f"       Duration: {duration:.2f}s")
    print()

    # List BVH joint hierarchy
    print(f"[2/5] BVH joint hierarchy:")
    def print_joint(j, depth=0):
        prefix = "  " * depth
        ch_str = ", ".join(j.channels) if j.channels else "(no channels)"
        print(f"       {prefix}{j.name}: {ch_str}")
        for child in j.children:
            print_joint(child, depth + 1)
    print_joint(joints[root_name])
    print()

    # Retarget all frames
    print(f"[3/5] Retargeting {n_frames} frames to Z1 joint space (14 DOF)...")
    retargeted = np.zeros((n_frames, 14))
    for f_idx in range(n_frames):
        raw = retarget_frame(joints, frames[f_idx])
        retargeted[f_idx] = clamp_to_limits(raw)

    # Report clamping statistics
    raw_unclamped = np.zeros((n_frames, 14))
    for f_idx in range(n_frames):
        raw_unclamped[f_idx] = retarget_frame(joints, frames[f_idx])

    n_clamped = np.sum(raw_unclamped != retargeted)
    if n_clamped > 0:
        print(f"       WARNING: {n_clamped} values clamped to URDF limits "
              f"({n_clamped / raw_unclamped.size * 100:.1f}% of all values)")
    else:
        print(f"       [OK] No values exceeded URDF joint limits")

    # Downsample FPS
    print(f"\n[4/5] Downsampling: {source_fps:.0f} Hz -> {args.target_fps:.0f} Hz")
    retargeted_ds, actual_fps = downsample_fps(retargeted, source_fps, args.target_fps)
    print(f"       Original frames: {retargeted.shape[0]}")
    print(f"       Downsampled frames: {retargeted_ds.shape[0]}")
    print(f"       Actual FPS: {actual_fps:.1f} Hz")
    print(f"       Duration preserved: {(retargeted_ds.shape[0] - 1) / actual_fps:.2f}s")

    # Save outputs
    print(f"\n[5/5] Saving outputs to {output_dir}/")

    npy_path = output_dir / "walking_retargeted.npy"
    np.save(str(npy_path), retargeted_ds)
    print(f"       [OK] {npy_path.name}: shape {retargeted_ds.shape}")

    csv_path = output_dir / "walking_retargeted.csv"
    header = ",".join(Z1_JOINT_NAMES)
    np.savetxt(str(csv_path), retargeted_ds, delimiter=",", header=header, comments="")
    print(f"       [OK] {csv_path.name}: {retargeted_ds.shape[0]} rows x {retargeted_ds.shape[1]} cols")

    # Also save the full-FPS version for reference
    npy_full_path = output_dir / "walking_retargeted_full_fps.npy"
    np.save(str(npy_full_path), retargeted)
    print(f"       [OK] {npy_full_path.name}: shape {retargeted.shape} (original {source_fps:.0f}Hz)")

    # Summary statistics
    print(f"\n{'-'*70}")
    print(f"Joint angle summary (downsampled, radians):")
    print(f"{'Joint':<25} {'Min':>8} {'Max':>8} {'Mean':>8} {'Std':>8} {'Limit_Lo':>9} {'Limit_Hi':>9}")
    print(f"{'-'*25} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*9} {'-'*9}")
    for j_idx, name in enumerate(Z1_JOINT_NAMES):
        col = retargeted_ds[:, j_idx]
        lo, hi = Z1_JOINT_LIMITS[j_idx]
        print(f"{name:<25} {col.min():>8.4f} {col.max():>8.4f} {col.mean():>8.4f} {col.std():>8.4f} {lo:>9.4f} {hi:>9.4f}")

    print(f"\n[DONE] Retargeting complete!")
    print(f"   Next steps:")
    print(f"   1. Run verify_retarget.py to visualize the joint trajectories")
    print(f"   2. Run generate_amp_dataset.py to create AMP training data")


if __name__ == "__main__":
    main()
