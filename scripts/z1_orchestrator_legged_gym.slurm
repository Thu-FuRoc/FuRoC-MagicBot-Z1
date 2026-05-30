#!/bin/bash
#SBATCH --job-name=z1_4phase
#SBATCH --partition=gpu
#SBATCH --gres=gpu:4
#SBATCH --time=24:00:00
#SBATCH --output=/home/phh/magiclab_rl_lab/logs/slurm/%j.out
#SBATCH --error=/home/phh/magiclab_rl_lab/logs/slurm/%j.err
#SBATCH --chdir=/home/phh/magiclab_rl_lab

# Force GPU 0-3 (avoid GPU 6 which has bypass process)
export CUDA_VISIBLE_DEVICES=0,1,2,3

# Activate conda
source ~/miniconda3/etc/profile.d/conda.sh
conda activate isaaclab

# Run legged_gym 4-phase orchestrator
python -u scripts/automation/phase_orchestrator.py \
    --plan config/pipeline/z1_legged_gym_4phase_plan.yaml \
    --num-gpus 4 \
    --poll-interval 120
