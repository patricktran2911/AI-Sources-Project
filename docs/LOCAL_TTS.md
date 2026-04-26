# Local Voice Cloning

This project can use a self-hosted voice-cloning service behind the existing `/api/v1/ai/speech` endpoint.

The first supported local engine is F5-TTS. The official F5-TTS project supports zero-shot voice cloning from a reference audio clip and transcript through `f5-tts_infer-cli`.

## Backend Flow

```text
Frontend
  -> POST /api/v1/ai/chat
  -> POST /api/v1/ai/speech
  -> LocalSpeechProvider
  -> Self-Host /v1/voice/synthesize
  -> f5-tts_infer-cli
  -> audio bytes
```

## Prepare Reference Audio

The prepared sample from the earlier recording step is:

```powershell
$env:TEMP\ai-sources-voice-samples\patrick_voice_sample.wav
```

Use the exact transcript for the reference audio in the sibling `Self-Host` repo's `.env`. Better transcript quality usually means better voice cloning.

## Install F5-TTS

Use the standalone PC voice-server project because its ML dependencies are heavier than the main backend:

```powershell
cd "E:\DevProj\AI Personal Projects\Self-Host"
py -3.10 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install torch==2.8.0+cu128 torchaudio==2.8.0+cu128 --extra-index-url https://download.pytorch.org/whl/cu128
pip install -r requirements.txt
```

For NVIDIA GPU, install the PyTorch build that matches your CUDA version before installing `f5-tts`.

## Configure Main Backend

Set these values in `.env`:

```env
SPEECH_PROVIDER=local
LOCAL_TTS_URL=http://127.0.0.1:7861/v1/voice/synthesize
LOCAL_TTS_API_KEY=the-same-value-as-LOCAL_AI_API_KEY
LOCAL_TTS_REFERENCE_AUDIO_PATH=
LOCAL_TTS_REFERENCE_TEXT=
LOCAL_TTS_MODEL=F5TTS_v1_Base
```

When using the standalone `Self-Host` project, reference audio and reference text are configured inside that project. This backend only needs the server URL and API key.

## Start The Local TTS Server

In the standalone `Self-Host` project:

```powershell
cd "E:\DevProj\AI Personal Projects\Self-Host"
.\run.ps1
```

Then run the main backend normally:

```powershell
uvicorn main:app --reload
```

Open:

```text
http://localhost:8000/voice-test
```

## Notes

- First generation can be slow because models need to download and warm up.
- CPU can work but will be slow. A CUDA-capable NVIDIA GPU is the practical production path.
- Keep your ElevenLabs provider configured as a fallback until the local voice is fast and stable enough.
