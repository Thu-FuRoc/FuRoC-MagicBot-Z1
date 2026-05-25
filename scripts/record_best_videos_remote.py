import argparse
import json
import subprocess
from pathlib import Path


REMOTE_HOST = "phh@192.168.120.155"
REMOTE_PROJECT_ROOT = "~/magiclab_rl_lab"
REMOTE_MANIFEST = "~/magiclab_rl_lab/configs/video_record_targets_current.json"
REMOTE_BATCH_SCRIPT = "~/magiclab_rl_lab/scripts/rsl_rl/record_z1_batch.py"
REMOTE_PLAY_SCRIPT = "~/magiclab_rl_lab/scripts/rsl_rl/play_z1_video.py"


def run(cmd: list[str]) -> None:
    print("[LOCAL]", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync batch recording scripts to RTX, run recording, and SCP videos back.")
    parser.add_argument("--manifest", default="configs/video_record_targets_current.json", help="Local manifest path.")
    parser.add_argument("--video-length", type=int, default=1000, help="Video length in simulation steps.")
    parser.add_argument(
        "--command-resample-time",
        type=float,
        default=3.0,
        help="Override base velocity command resampling period during recording.",
    )
    parser.add_argument("--device", default="cuda:0", help="Remote torch device.")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Sync and print only.")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    manifest_path = (repo_root / args.manifest).resolve()
    batch_script = repo_root / "magiclab_rl_lab" / "scripts" / "rsl_rl" / "record_z1_batch.py"
    play_script = repo_root / "magiclab_rl_lab" / "scripts" / "rsl_rl" / "play_z1_video.py"

    with manifest_path.open("r", encoding="utf-8") as f:
        manifest = json.load(f)

    local_output_dir = repo_root / manifest["local_output_dir"]
    local_output_dir.mkdir(parents=True, exist_ok=True)

    remote_prepare_cmd = (
        "mkdir -p ~/magiclab_rl_lab/configs "
        f"~/magiclab_rl_lab/{manifest['remote_output_dir']}"
    )
    run(["ssh", REMOTE_HOST, remote_prepare_cmd])

    run(["scp", str(manifest_path), f"{REMOTE_HOST}:{REMOTE_MANIFEST}"])
    run(["scp", str(batch_script), f"{REMOTE_HOST}:{REMOTE_BATCH_SCRIPT}"])
    run(["scp", str(play_script), f"{REMOTE_HOST}:{REMOTE_PLAY_SCRIPT}"])

    remote_cmd = (
        "source ~/miniconda3/etc/profile.d/conda.sh && "
        "conda activate isaaclab && "
        "cd ~/magiclab_rl_lab && "
        f"python -u {REMOTE_BATCH_SCRIPT} --manifest {REMOTE_MANIFEST} "
        f"--video-length {args.video_length} --command-resample-time {args.command_resample_time} "
        f"--device {args.device} --headless"
    )
    if args.dry_run:
        remote_cmd += " --dry-run"
    run(["ssh", REMOTE_HOST, remote_cmd])

    if args.dry_run:
        return 0

    remote_output_dir = manifest["remote_output_dir"]
    for target in manifest["targets"]:
        remote_video = f"{REMOTE_HOST}:{REMOTE_PROJECT_ROOT}/{remote_output_dir}/{target['output_name']}"
        local_video = local_output_dir / target["output_name"]
        remote_meta = f"{REMOTE_HOST}:{REMOTE_PROJECT_ROOT}/{remote_output_dir}/{Path(target['output_name']).stem}.json"
        local_meta = local_output_dir / f"{Path(target['output_name']).stem}.json"
        run(["scp", remote_video, str(local_video)])
        run(["scp", remote_meta, str(local_meta)])

    print(f"[LOCAL] All videos pulled to {local_output_dir}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
