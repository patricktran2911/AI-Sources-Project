"""Create an ElevenLabs instant voice clone from local audio samples.

Usage:
    py -3.12 scripts/create_elevenlabs_voice.py \
        --name "Patrick Tran Voice" \
        --sample "C:\\path\\to\\sample.wav"
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create an ElevenLabs instant voice clone.")
    parser.add_argument("--name", default="Patrick Tran Voice", help="Voice name shown in ElevenLabs.")
    parser.add_argument(
        "--description",
        default="Custom chatbot voice created from Patrick Tran's approved voice samples.",
        help="Voice description shown in ElevenLabs.",
    )
    parser.add_argument(
        "--sample",
        action="append",
        required=True,
        help="Path to a voice sample file. Pass multiple --sample arguments to upload several files.",
    )
    parser.add_argument(
        "--remove-background-noise",
        action="store_true",
        help="Ask ElevenLabs to remove background noise from the uploaded sample.",
    )
    return parser.parse_args()


def main() -> int:
    load_dotenv()
    args = parse_args()
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print("ELEVENLABS_API_KEY is not configured in .env.")
        return 1

    sample_paths = [Path(sample).expanduser().resolve() for sample in args.sample]
    missing = [str(path) for path in sample_paths if not path.exists()]
    if missing:
        print("Missing sample file(s): " + ", ".join(missing))
        return 1

    files = []
    handles = []
    try:
        for path in sample_paths:
            handle = path.open("rb")
            handles.append(handle)
            files.append(("files", (path.name, handle, "application/octet-stream")))

        response = httpx.post(
            "https://api.elevenlabs.io/v1/voices/add",
            headers={"xi-api-key": api_key},
            data={
                "name": args.name,
                "description": args.description,
                "remove_background_noise": str(args.remove_background_noise).lower(),
            },
            files=files,
            timeout=180.0,
        )
    finally:
        for handle in handles:
            handle.close()

    if response.status_code >= 400:
        print(f"ElevenLabs voice creation failed with HTTP {response.status_code}.")
        print(response.text[:1200])
        return 1

    payload = response.json()
    print(json.dumps(payload, indent=2))
    voice_id = payload.get("voice_id")
    if voice_id:
        print()
        print("Add these to .env:")
        print("SPEECH_PROVIDER=elevenlabs")
        print(f"ELEVENLABS_VOICE_ID={voice_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
