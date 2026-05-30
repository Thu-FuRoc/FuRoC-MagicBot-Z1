#!/bin/bash
#SBATCH --job-name=z1_p3_fine
#SBATCH --partition=gpu
#SBATCH --gres=gpu:4
#SBATCH --time=24:00:00
#SBATCH --output=/home/phh/magiclab_rl_lab/logs/slurm/%j.out
#SBATCH --error=/home/phh/magiclab_rl_lab/logs/slurm/%j.err
#SBATCH --chdir=/home/phh/magiclab_rl_lab

export CUDA_VISIBLE_DEVICES=0,1,2,3
source ~/miniconda3/etc/profile.d/conda.sh
conda activate isaaclab

PYTHON=/home/phh/miniconda3/envs/isaaclab/bin/python3.10
LOG=/tmp/z1_p3_fine_resume.log

echo "[$(date)] Waiting for P3 Coarse (PID 768642) to finish..." | tee -a $LOG

while kill -0 768642 2>/dev/null; do
    sleep 60
done

echo "[$(date)] P3 Coarse finished. Finding best checkpoint..." | tee -a $LOG

RUN_DIR=logs/rsl_rl/magiclab_z1_12dof_velocity/2026-05-29_17-45-26_p3_coarse

# Find best reward and corresponding checkpoint
BEST_INFO=$($PYTHON -c "
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
import os, glob
ea = EventAccumulator(os.path.expanduser('~/magiclab_rl_lab/$RUN_DIR'))
ea.Reload()
events = ea.Scalars('Train/mean_reward')
rewards = [(e.step, e.value) for e in events]
best_step, best_r = max(rewards, key=lambda x: x[1])
print(f'{best_step}:{best_r:.2f}')
")

BEST_STEP=$(echo $BEST_INFO | cut -d: -f1)
BEST_REWARD=$(echo $BEST_INFO | cut -d: -f2)
BEST_MODEL=model_${BEST_STEP}.pt
BEST_PATH=/home/phh/magiclab_rl_lab/$RUN_DIR/$BEST_MODEL

echo "[$(date)] Best: $BEST_PATH (reward $BEST_REWARD)" | tee -a $LOG

if [ ! -f "$BEST_PATH" ]; then
    echo "[$(date)] ERROR: $BEST_PATH not found!" | tee -a $LOG
    exit 1
fi

# Write orchestrator state
$PYTHON -c "
import json
best_path = '$BEST_PATH'
best_reward = float('$BEST_REWARD')
state = {
    'plan_name': 'z1_5phase',
    'current_stage_id': 'p3_fine',
    'current_stage_status': 'pending',
    'training_pid': None,
    'training_run_dir': None,
    'best_checkpoint_path': None,
    'best_reward': None,
    'stage_history': [
        {'sub_phase_id': 'p2_fine', 'best_checkpoint_path': '/home/phh/magiclab_rl_lab/logs/rsl_rl/magiclab_z1_12dof_velocity/2026-05-18_19-35-30_p2_fine/model_4800.pt', 'best_reward': 38.21},
        {'sub_phase_id': 'p3_coarse', 'best_checkpoint_path': best_path, 'best_reward': best_reward}
    ],
    'retry_count': 0,
    'started_at': None,
    'updated_at': None,
    'current_phase_id': 'p3',
    'starting_reward': None,
    'rollback_count': 0,
    'error_message': None,
    'phase_history': []
}
for p in ['/home/phh/magiclab_rl_lab/orchestrator_state.json', '/home/phh/magiclab_rl_lab/scripts/orchestrator_state.json']:
    with open(p, 'w') as f:
        json.dump(state, f, indent=2)
    print(f'Wrote state to {p}')
"

echo "[$(date)] Starting P3 Fine via orchestrator --resume..." | tee -a $LOG

PYTHONPATH=scripts python -u scripts/automation/phase_orchestrator.py \
    --plan config/pipeline/z1_custom_5phase_plan.yaml \
    --num-gpus 4 \
    --poll-interval 120

echo "[$(date)] Orchestrator exited." | tee -a $LOG
