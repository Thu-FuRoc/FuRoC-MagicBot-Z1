# Z1 常用终端指令速查

> `local_play` 指本地 Windows / MuJoCo，不是 RTX 远端。下面都是可以直接复制执行的命令。 

## 1. 本地 local_play / MuJoCo

```
cd D:\Desktop_Files\GPU-Train\RTX6000\Magicbot_Z1

# 启动 GUI
python .\scripts\local_play_gui.py

# 本地交互回放：对应 local_play
python sim2sim\mujoco_manual.py --mjcf magicbot-z1_description\mjcf\MAGICBOTZ1.xml --policy models\p\p2_fine\p2_fine_policy.pt --deploy_cfg videos\p\p2_fine\params\deploy.yaml --keyboard --num_steps 10000

# p2_coarse 记录 CSV
python sim2sim\mujoco_manual.py --mjcf magicbot-z1_description\mjcf\MAGICBOTZ1.xml --policy models\p\p2_coarse\p2_coarse_policy.pt --deploy_cfg videos\p\p2_coarse\params\deploy.yaml --phase p2 --csv

# p2_coarse CSV 分析
python scripts\analyze_csv.py logs\p\p2_coarse\20260515_014555\p2_coarse.csv
```

## 2. 远端 RTX 查询

```
/gpu-train --status
/gpu-train --tail
/gpu-train --gpu
/gpu-train --idle
/gpu-train --mycuda
/gpu-train --slurm
```

## 3. Orchestrator

```
/gpu-train --orchestrator --start
/gpu-train --orchestrator --start --from p3_fine
/gpu-train --orchestrator --resume
```

## 4. Windows 本地提交远端 RTX

```
& 'C:\Program Files\Git\bin\bash.exe' 'D:\Desktop_Files\GPU-Train\RTX6000\rtx_submit_orchestrator_train.sh' --resume
& 'C:\Program Files\Git\bin\bash.exe' 'D:\Desktop_Files\GPU-Train\RTX6000\rtx_submit_resume_train.sh' --phase p3_fine --load-run 2026-05-16_12-13-26_p3_fine --checkpoint model_5500.pt --gpus 4 --num-envs 4096 --max-iterations 15000 --master-port 29522 --no-hold
```

## 5. 本地提示

```
/gpu-train --sim
```

Standalone quick reference for common terminal commands.