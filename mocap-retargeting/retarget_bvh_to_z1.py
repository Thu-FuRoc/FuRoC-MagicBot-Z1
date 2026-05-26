#!/usr/bin/env python3
"""
retarget_bvh_to_z1.py — Retarget CMU BVH mocap to MagicBot-Z1 (14 actuated DOF)
=================================================================================

MagicBot-Z1 actuated joints (14 total):
  Legs (12):  HIP_PITCH, HIP_ROLL, HIP_YAW, KNEE_PITCH, ANKLE_PITCH, ANKLE_ROLL  × L/R
  Arms (2):   joint_la1 (left shoulder pitch), joint_ra1 (right shoulder pitch)

All other joints (waist, head, arm joints 2–5) are type="fixed" in the URDF.

CMU BVH skeleton is in T-pose (arms sideways). The key challenge is extracting
the shoulder forward/backward swing from the BVH's coupled ZYX Euler angles
where the dominant Z-rotation (~90°) represents bringing the arm from T-pose down.

Output: walking_retargeted.npy  — shape (N, 14) at 50 Hz
"""

import argparse
import os
import numpy as np
from scipy.spatial.transform import Rotation

# ═══════════════════════════════════════════════════════════════════════════════
# Z1 Joint Definition (14 actuated DOF)
# ═══════════════════════════════════════════════════════════════════════════════

Z1_JOINT_NAMES = [
    # Left leg (0–5)
    "JOINT_HIP_PITCH_L",   # axis Y
    "JOINT_HIP_ROLL_L",    # axis X
    "JOINT_HIP_YAW_L",     # axis Z
    "JOINT_KNEE_PITCH_L",  # axis Y, lower=0
    "JOINT_ANKLE_PITCH_L", # axis Y
    "JOINT_ANKLE_ROLL_L",  # axis X
    # Right leg (6–11)
    "JOINT_HIP_PITCH_R",   # axis Y
    "JOINT_HIP_ROLL_R",    # axis X
    "JOINT_HIP_YAW_R",     # axis Z
    "JOINT_KNEE_PITCH_R",  # axis Y, lower=0
    "JOINT_ANKLE_PITCH_R", # axis Y
    "JOINT_ANKLE_ROLL_R",  # axis X
    # Arms (12–13)
    "joint_la1",           # axis ~Y (shoulder pitch left)
    "joint_ra1",           # axis ~Y (shoulder pitch right)
]

Z1_JOINT_INDEX = {name: i for i, name in enumerate(Z1_JOINT_NAMES)}

# URDF joint limits (radians)
Z1_JOINT_LIMITS = {
    "JOINT_HIP_PITCH_L":   (-2.7925, 2.7925),
    "JOINT_HIP_ROLL_L":    (-0.524,  2.967),
    "JOINT_HIP_YAW_L":     (-2.7925, 2.7925),
    "JOINT_KNEE_PITCH_L":  ( 0.0,    2.653),
    "JOINT_ANKLE_PITCH_L": (-0.873,  0.524),
    "JOINT_ANKLE_ROLL_L":  (-0.262,  0.262),
    "JOINT_HIP_PITCH_R":   (-2.7925, 2.7925),
    "JOINT_HIP_ROLL_R":    (-2.967,  0.524),
    "JOINT_HIP_YAW_R":     (-2.7925, 2.7925),
    "JOINT_KNEE_PITCH_R":  ( 0.0,    2.653),
    "JOINT_ANKLE_PITCH_R": (-0.873,  0.524),
    "JOINT_ANKLE_ROLL_R":  (-0.262,  0.262),
    "joint_la1":           (-2.88,   2.88),
    "joint_ra1":           (-2.88,   2.88),
}

# ═══════════════════════════════════════════════════════════════════════════════
# BVH Parser
# ═══════════════════════════════════════════════════════════════════════════════

class BVHJoint:
    """Represents one joint in the BVH hierarchy."""
    def __init__(self, name):
        self.name = name
        self.offset = np.zeros(3)
        self.channels = []          # e.g. ['Zrotation', 'Yrotation', 'Xrotation']
        self.channel_indices = []   # indices into the per-frame data array
        self.children = []
        self.parent = None


def parse_bvh(filepath):
    """
    Parse a BVH file. Returns:
        joints: dict name -> BVHJoint
        root_name: str
        frames: list of np arrays (one per frame)
        frame_time: float (seconds per frame)
    """
    with open(filepath, 'r') as f:
        lines = f.readlines()

    joints = {}
    root_name = None
    stack = []
    channel_counter = 0
    i = 0

    # --- Parse HIERARCHY ---
    while i < len(lines):
        line = lines[i].strip()
        i += 1

        if line.startswith('ROOT') or line.startswith('JOINT'):
            name = line.split()[-1]
            joint = BVHJoint(name)
            if line.startswith('ROOT'):
                root_name = name
            if stack:
                parent = stack[-1]
                parent.children.append(joint)
                joint.parent = parent
            joints[name] = joint
            stack.append(joint)

        elif line.startswith('End Site'):
            # skip until closing brace
            while i < len(lines) and '}' not in lines[i]:
                i += 1
            i += 1  # skip the }

        elif line.startswith('OFFSET'):
            vals = line.split()[1:]
            stack[-1].offset = np.array([float(v) for v in vals])

        elif line.startswith('CHANNELS'):
            parts = line.split()
            n_ch = int(parts[1])
            ch_names = parts[2:2+n_ch]
            stack[-1].channels = ch_names
            stack[-1].channel_indices = list(range(channel_counter, channel_counter + n_ch))
            channel_counter += n_ch

        elif line == '}':
            stack.pop()

        elif line.startswith('MOTION'):
            break

    # --- Parse MOTION ---
    # Next line: "Frames: N"
    n_frames = int(lines[i].strip().split(':')[1])
    i += 1
    # Next line: "Frame Time: T"
    frame_time = float(lines[i].strip().split(':')[1])
    i += 1

    frames = []
    for fi in range(n_frames):
        vals = np.array([float(x) for x in lines[i].strip().split()])
        frames.append(vals)
        i += 1

    return joints, root_name, frames, frame_time


# ═══════════════════════════════════════════════════════════════════════════════
# BVH Rotation Utilities
# ═══════════════════════════════════════════════════════════════════════════════

def get_joint_rotation(joints, joint_name, frame_data):
    """
    Get the local rotation matrix for a BVH joint at a given frame.
    Returns scipy Rotation object.
    """
    joint = joints[joint_name]
    if not joint.channels:
        return Rotation.identity()

    # Build the Euler angle string and values
    angles = []
    axes = ""
    for ch_name, ch_idx in zip(joint.channels, joint.channel_indices):
        if 'rotation' in ch_name.lower():
            axis_char = ch_name[0].upper()  # 'X', 'Y', or 'Z'
            axes += axis_char
            angles.append(frame_data[ch_idx])

    if not axes:
        return Rotation.identity()

    # BVH uses intrinsic rotations in the listed order
    return Rotation.from_euler(axes, angles, degrees=True)


def get_world_rotation(joints, joint_name, frame_data):
    """
    Compute the world-frame rotation for a joint by chaining parent rotations.
    """
    chain = []
    j = joints[joint_name]
    while j is not None:
        chain.append(j.name)
        j = j.parent
    chain.reverse()

    R_world = Rotation.identity()
    for name in chain:
        R_local = get_joint_rotation(joints, name, frame_data)
        R_world = R_world * R_local

    return R_world


def extract_axis_angle(joints, joint_name, axis, frame_data):
    """
    Extract a single-axis rotation component from a BVH joint's Euler channels.
    
    For BVH joints with ZYX order, this decomposes the full rotation into
    individual axis contributions. 'axis' is 'X', 'Y', or 'Z'.
    
    Returns angle in radians.
    """
    R = get_joint_rotation(joints, joint_name, frame_data)
    
    # Decompose using intrinsic ZYX (which is what CMU BVH uses)
    euler_zyx = R.as_euler('ZYX', degrees=False)
    
    if axis == 'Z':
        return euler_zyx[0]
    elif axis == 'Y':
        return euler_zyx[1]
    elif axis == 'X':
        return euler_zyx[2]
    else:
        raise ValueError(f"Unknown axis: {axis}")


# ═══════════════════════════════════════════════════════════════════════════════
# Arm Retargeting — Proper Swing Extraction
# ═══════════════════════════════════════════════════════════════════════════════

def extract_arm_swing_angle(joints, arm_name, frame_data, side='left'):
    """
    Extract the forward/backward shoulder pitch angle from CMU BVH data.
    
    The CMU skeleton has arms pointing sideways in T-pose. During walking:
    - LeftArm Z-rotation goes to ~-90° to bring arm down
    - Then X-rotation adds the forward/backward swing
    
    We compute the arm direction in the torso frame, then measure the 
    pitch angle relative to straight-down.
    
    Returns: angle in radians (positive = forward, negative = backward)
    """
    # Get the rotation of the arm joint in the torso frame
    # We need the rotation relative to the parent (Spine1/LeftShoulder chain)
    
    # Compute world rotation of the arm's parent
    parent_name = joints[arm_name].parent.name  # LeftShoulder or RightShoulder
    R_parent_world = get_world_rotation(joints, parent_name, frame_data)
    
    # Compute world rotation of the arm
    R_arm_world = get_world_rotation(joints, arm_name, frame_data)
    
    # Arm direction in T-pose: +X for left arm, -X for right arm
    if side == 'left':
        t_pose_dir = np.array([1.0, 0.0, 0.0])
    else:
        t_pose_dir = np.array([-1.0, 0.0, 0.0])
    
    # Current arm direction in world frame
    arm_dir = R_arm_world.apply(t_pose_dir)
    
    # Transform to torso-local frame
    # Get torso world rotation (use Spine1 as the torso reference)
    R_torso = get_world_rotation(joints, 'Spine1', frame_data)
    arm_dir_local = R_torso.inv().apply(arm_dir)
    
    # In the torso local frame:
    #   Y is up, X is lateral, Z is forward (CMU convention: Y-up)
    # The Z1 convention: X is forward, Z is up
    # CMU BVH: Y-up, Z-forward at rest
    
    # Project onto sagittal plane (forward-down plane in CMU frame)
    # Forward = Z, Down = -Y
    forward = arm_dir_local[2]   # Z component = how far forward
    down = -arm_dir_local[1]     # -Y component = how far down
    
    # Pitch angle: 0 = straight down, positive = forward
    pitch = np.arctan2(forward, down)
    
    return pitch


# ═══════════════════════════════════════════════════════════════════════════════
# Leg Retargeting — Per-Axis Mapping
# ═══════════════════════════════════════════════════════════════════════════════

# CMU BVH coordinate system: Y=up, Z=forward, X=right
# BVH Xrotation = sagittal pitch    → Z1 hip/knee/ankle PITCH (Y-axis on robot)
# BVH Zrotation = frontal roll      → Z1 hip/ankle ROLL (X-axis on robot)
# BVH Yrotation = transverse yaw    → Z1 hip YAW (Z-axis on robot)
#
# Note: Right leg in CMU BVH has inverted X-axis pitch convention

LEG_MAPPING = {
    # Left leg
    "JOINT_HIP_PITCH_L":   ("LeftUpLeg",  "X",  0.8),   # Pitch (+0.8 is correct for forward swing)
    "JOINT_HIP_ROLL_L":    ("LeftUpLeg",  "Z",  0.0),   # Zero out horizontal sway
    "JOINT_HIP_YAW_L":     ("LeftUpLeg",  "Y",  0.0),   # Zero out horizontal sway
    "JOINT_KNEE_PITCH_L":  ("LeftLeg",    "X",  0.8),   # Knee flexion
    "JOINT_ANKLE_PITCH_L": ("LeftFoot",   "X",  0.6),   # Ankle pitch
    "JOINT_ANKLE_ROLL_L":  ("LeftFoot",   "Z",  0.0),   # Zero out ankle roll
    # Right leg
    "JOINT_HIP_PITCH_R":   ("RightUpLeg", "X",  0.8),   # Pitch (+0.8 is correct for forward swing)
    "JOINT_HIP_ROLL_R":    ("RightUpLeg", "Z",  0.0),   # Zero out horizontal sway
    "JOINT_HIP_YAW_R":     ("RightUpLeg", "Y",  0.0),   # Zero out horizontal sway
    "JOINT_KNEE_PITCH_R":  ("RightLeg",   "X",  0.8),   # Knee flexion
    "JOINT_ANKLE_PITCH_R": ("RightFoot",  "X",  0.6),   # Ankle pitch
    "JOINT_ANKLE_ROLL_R":  ("RightFoot",  "Z",  0.0),   # Zero out ankle roll
}

# Arm scale — controls how much of the human swing maps to robot
ARM_SWING_SCALE = 0.5


# ═══════════════════════════════════════════════════════════════════════════════
# Main Retargeting
# ═══════════════════════════════════════════════════════════════════════════════

def retarget_frame(joints, frame_data, frame0_data):
    """
    Retarget a single BVH frame to Z1's 14-DOF joint space.
    Subtracts frame0_data angles to compute motion relative to the rest pose.
    Returns np.array of shape (14,).
    """
    z1_angles = np.zeros(14)
    
    # --- Legs (indices 0–11) ---
    for z1_joint, (bvh_joint, axis, scale) in LEG_MAPPING.items():
        idx = Z1_JOINT_INDEX[z1_joint]
        
        # Get absolute angle for this frame
        angle_rad = extract_axis_angle(joints, bvh_joint, axis, frame_data)
        
        # Get base pose angle (T-pose / A-pose)
        base_rad = extract_axis_angle(joints, bvh_joint, axis, frame0_data)
        
        # The true motion is relative to the base pose
        rel_angle = angle_rad - base_rad
        
        z1_angles[idx] = rel_angle * scale
    
    # --- Arms (indices 12–13) ---
    # Extract forward/backward swing from BVH arm rotations
    left_pitch = extract_arm_swing_angle(joints, 'LeftArm', frame_data, side='left')
    right_pitch = extract_arm_swing_angle(joints, 'RightArm', frame_data, side='right')
    
    z1_angles[12] = left_pitch * ARM_SWING_SCALE    # joint_la1
    z1_angles[13] = right_pitch * ARM_SWING_SCALE   # joint_ra1
    
    # --- Enforce joint limits ---
    for name, (lo, hi) in Z1_JOINT_LIMITS.items():
        idx = Z1_JOINT_INDEX[name]
        z1_angles[idx] = np.clip(z1_angles[idx], lo, hi)
    
    return z1_angles


def retarget_bvh(bvh_path, target_fps=50.0):
    """
    Retarget a full BVH file to Z1 joint angles.
    Downsamples from BVH frame rate to target_fps.
    
    Returns: np.array of shape (N_out, 14)
    """
    joints, root_name, frames, frame_time = parse_bvh(bvh_path)
    bvh_fps = 1.0 / frame_time
    n_frames = len(frames)
    
    print(f"Parsing {os.path.basename(bvh_path)} ({n_frames} frames @ {bvh_fps:.0f}Hz)")
    
    # Downsample indices
    ratio = bvh_fps / target_fps
    out_indices = []
    t = 0.0
    while int(t) < n_frames:
        out_indices.append(int(t))
        t += ratio
    
    # Retarget each selected frame
    result = np.zeros((len(out_indices), 14))
    frame0_data = frames[0]
    for out_i, bvh_i in enumerate(out_indices):
        result[out_i] = retarget_frame(joints, frames[bvh_i], frame0_data)
    
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# CLI Entry Point
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Retarget CMU BVH to MagicBot-Z1 (14 DOF)")
    parser.add_argument('--bvh', type=str, default='walk/02_02.bvh',
                        help='Path to input BVH file')
    parser.add_argument('--fps', type=float, default=50.0,
                        help='Output frame rate (Hz)')
    parser.add_argument('--out', type=str, default='walking_retargeted.npy',
                        help='Output .npy file path')
    args = parser.parse_args()
    
    result = retarget_bvh(args.bvh, target_fps=args.fps)
    
    np.save(args.out, result)
    print(f"[OK] {args.out}: shape {result.shape}")
    
    # Also save CSV for inspection
    csv_path = args.out.replace('.npy', '.csv')
    header = ','.join(Z1_JOINT_NAMES)
    np.savetxt(csv_path, np.degrees(result), delimiter=',', header=header, fmt='%.4f')
    print(f"[OK] {csv_path}")


if __name__ == '__main__':
    main()
