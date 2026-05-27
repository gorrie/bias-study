#!/usr/bin/env python3
"""
dl_model.py — Robust HuggingFace model downloader (host-side, resume-until-valid).

Why this exists: the Docker huggingface_hub path strangles large LFS pulls (WSL2
NAT), and even host downloads hit intermittent TLS drops mid-shard
("server closed abruptly"). Paying HF doesn't fix connection-path instability.
The fix is Range-resume + per-file retry + safetensors integrity validation,
looped until each file is provably complete. Downloads to a flat local dir for
offline abliteration (HF_HUB_OFFLINE=1).

Auth for gated models: an HF token is resolved (in priority order) from the
HF_TOKEN environment variable, a repo-root .env (HF_TOKEN=...), an explicit
--token-file, or the standard HF CLI cache (~/.cache/huggingface/token).

Usage:
    python3 dl_model.py <repo_id> <dest_dir> [--token-file PATH] [--max-retries 30]

Examples (MODELS_DIR defaults to ./models; set it in your .env or environment):
    python3 dl_model.py google/gemma-2-9b-it "$MODELS_DIR/gemma-2-9b-it"
    python3 dl_model.py deepseek-ai/DeepSeek-R1-Distill-Qwen-7B "$MODELS_DIR/deepseek-r1-distill-qwen-7b"
"""
from __future__ import annotations

import argparse
import json
import os
import struct
import sys
import time
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).parent
STUDY_DIR = SCRIPT_DIR.parent
# Standard cross-platform HF token cache (Linux/macOS/Windows all use Path.home()).
DEFAULT_HF_TOKEN_FILE = Path.home() / ".cache" / "huggingface" / "token"

META_FILES = [
    "config.json", "generation_config.json", "tokenizer.json",
    "tokenizer_config.json", "special_tokens_map.json", "tokenizer.model",
    "model.safetensors.index.json", "vocab.json", "merges.txt", "chat_template.jinja",
]


def hf_url(repo: str, fname: str) -> str:
    return f"https://huggingface.co/{repo}/resolve/main/{fname}"


def resolve_hf_token(token_file_arg: str | None) -> str | None:
    """Resolve an HF token portably: HF_TOKEN env var, then a repo-root .env
    (HF_TOKEN=...), then an explicit --token-file, then the standard HF CLI cache."""
    if os.environ.get("HF_TOKEN"):
        return os.environ["HF_TOKEN"].strip()
    env_path = STUDY_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("HF_TOKEN=") and "=" in line:
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val:
                    return val
    candidates = []
    if token_file_arg:
        candidates.append(Path(token_file_arg))
    candidates.append(DEFAULT_HF_TOKEN_FILE)
    for tf in candidates:
        if tf.exists():
            tok = tf.read_text().strip()
            if tok:
                return tok
    return None


def validate_safetensors(path: Path) -> bool:
    """True if the safetensors header's declared tensor extent matches the file size."""
    try:
        with open(path, "rb") as fh:
            n = struct.unpack("<Q", fh.read(8))[0]
            hdr = json.loads(fh.read(n))
        maxend = max((v["data_offsets"][1] for k, v in hdr.items() if k != "__metadata__"), default=0)
        return path.stat().st_size == 8 + n + maxend
    except Exception:
        return False


def download_file(repo: str, fname: str, dest: Path, headers: dict, max_retries: int,
                  is_shard: bool) -> bool:
    """Range-resume download of one file, retrying until complete (and valid if a shard)."""
    target = dest / fname
    url = hf_url(repo, fname)
    for attempt in range(1, max_retries + 1):
        have = target.stat().st_size if target.exists() else 0
        h = dict(headers)
        if have:
            h["Range"] = f"bytes={have}-"
        try:
            r = requests.get(url, headers=h, stream=True, timeout=30)
            if r.status_code == 404:
                print(f"    {fname}: 404 (not in repo) — skip")
                return False
            if r.status_code == 416:  # range not satisfiable = already complete
                pass
            elif r.status_code not in (200, 206):
                print(f"    {fname}: HTTP {r.status_code} (attempt {attempt})")
                time.sleep(2)
                continue
            mode = "ab" if (have and r.status_code == 206) else "wb"
            if mode == "wb":
                have = 0
            with open(target, mode) as out:
                for chunk in r.iter_content(chunk_size=8 << 20):
                    if chunk:
                        out.write(chunk)
        except Exception as e:
            print(f"    {fname}: {type(e).__name__} at {target.stat().st_size if target.exists() else 0}B "
                  f"(attempt {attempt}) — resuming")
            time.sleep(2)
            continue
        # success path: validate
        if is_shard:
            if validate_safetensors(target):
                print(f"    {fname}: OK {target.stat().st_size // 1048576}MB (validated)")
                return True
            else:
                print(f"    {fname}: size/header mismatch at {target.stat().st_size // 1048576}MB "
                      f"(attempt {attempt}) — resuming")
                time.sleep(1)
                continue
        else:
            print(f"    {fname}: OK {target.stat().st_size}B")
            return True
    print(f"    {fname}: FAILED after {max_retries} attempts")
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("dest")
    ap.add_argument("--token-file", default=None,
                    help="Explicit HF token file. Default resolution: HF_TOKEN env, "
                         "repo .env, then ~/.cache/huggingface/token.")
    ap.add_argument("--max-retries", type=int, default=30)
    args = ap.parse_args()

    dest = Path(args.dest)
    dest.mkdir(parents=True, exist_ok=True)
    headers = {}
    token = resolve_hf_token(args.token_file)
    if token:
        headers["Authorization"] = f"Bearer {token}"

    print(f"=== {args.repo} -> {dest} ===")
    # 1. metadata + tokenizer files (best-effort)
    for f in META_FILES:
        download_file(args.repo, f, dest, headers, args.max_retries, is_shard=False)

    # 2. shard list from the index (authoritative); fallback to single model.safetensors
    idx = dest / "model.safetensors.index.json"
    if idx.exists():
        wm = json.loads(idx.read_text())["weight_map"]
        shards = sorted(set(wm.values()))
    else:
        shards = ["model.safetensors"]
    print(f"  shards to fetch: {len(shards)}")
    ok = True
    for sh in shards:
        if not download_file(args.repo, sh, dest, headers, args.max_retries, is_shard=True):
            ok = False

    # 3. final validation
    bad = [s for s in shards if not validate_safetensors(dest / s)]
    total_mb = sum((dest / s).stat().st_size for s in shards if (dest / s).exists()) // 1048576
    print(f"=== {'PASS' if ok and not bad else 'FAIL'}: {len(shards)-len(bad)}/{len(shards)} shards valid, {total_mb}MB ===")
    if bad:
        print(f"  invalid: {bad}")
    return 0 if (ok and not bad) else 1


if __name__ == "__main__":
    sys.exit(main())
