#!/usr/bin/env python3
"""
generate_amp_dataset.py — Generate AMP state transitions from retargeted data
==============================================================================

Takes retargeted joint angles (14-DOF @ 50Hz) and produces AMP state transitions.

Each state sₜ has 34 dimensions:
  - Joint positions (14): the 14 actuated joint angles
  - Joint velocities (14): finite-difference approximation
  - Base angular velocity (3): [0, 0, 0] (no global rotation in retargeting)
  - Projected gravity (3): [0, 0, -1] (upright standing)

Each transition is (sₜ, sₜ₊₁) = 68 dimensions.
"""

import argparse
import numpy as np
import retarget_bvh_to_z1


STATE_DIM = 34  # 14 + 14 + 3 + 3
TRANSITION_DIM = STATE_DIM * 2  # 68


def compute_states(joint_angles, dt=0.02):
    """
    Compute AMP states from joint angle trajectories.
    
    Args:
        joint_angles: np.array of shape (N, 14) — retargeted joint angles in radians
        dt: timestep (1/50 Hz = 0.02s)
    
    Returns:
        states: np.array of shape (N, 34)
    """
    n_frames = joint_angles.shape[0]
    n_joints = joint_angles.shape[1]
    
    # Joint velocities via finite differences
    velocities = np.zeros_like(joint_angles)
    if n_frames > 1:
        velocities[1:] = (joint_angles[1:] - joint_angles[:-1]) / dt
        velocities[0] = velocities[1]  # copy first velocity
    
    # Base angular velocity (zeros — we don't track global rotation)
    ang_vel = np.zeros((n_frames, 3))
    
    # Projected gravity (constant upright: [0, 0, -1])
    gravity = np.tile(np.array([0.0, 0.0, -1.0]), (n_frames, 1))
    
    # Concatenate: [positions(14), velocities(14), ang_vel(3), gravity(3)]
    states = np.concatenate([joint_angles, velocities, ang_vel, gravity], axis=1)
    
    assert states.shape == (n_frames, STATE_DIM), f"Expected ({n_frames}, {STATE_DIM}), got {states.shape}"
    
    return states


def compute_transitions(states):
    """
    Build (sₜ, sₜ₊₁) transition pairs.
    
    Args:
        states: np.array of shape (N, 34)
    
    Returns:
        transitions: np.array of shape (N-1, 68)
    """
    s_t = states[:-1]
    s_tp1 = states[1:]
    transitions = np.concatenate([s_t, s_tp1], axis=1)
    
    assert transitions.shape[1] == TRANSITION_DIM
    
    return transitions


def process_bvh(bvh_path, target_fps=50.0):
    """
    Full pipeline: BVH -> retarget -> AMP transitions.
    Returns transitions array of shape (N-1, 68).
    """
    joint_angles = retarget_bvh_to_z1.retarget_bvh(bvh_path, target_fps=target_fps)
    states = compute_states(joint_angles, dt=1.0/target_fps)
    transitions = compute_transitions(states)
    return transitions


def main():
    parser = argparse.ArgumentParser(description="Generate AMP transitions from BVH")
    parser.add_argument('--bvh', type=str, default='walk/02_02.bvh')
    parser.add_argument('--fps', type=float, default=50.0)
    parser.add_argument('--out', type=str, default='amp_transitions.npy')
    args = parser.parse_args()
    
    transitions = process_bvh(args.bvh, args.fps)
    np.save(args.out, transitions)
    print(f"[OK] {args.out}: shape {transitions.shape}")
    print(f"     State dim: {STATE_DIM}, Transition dim: {TRANSITION_DIM}")


if __name__ == '__main__':
    main()
