# Self-Host Voice Integration

`AI Sources Project` can call an external `Self-Host` service behind the existing `/api/v1/ai/speech` and voice-chat endpoints. The cloud backend never loads CosyVoice, F5-TTS, model weights, checkpoints, or private reference audio.

The current production default is:

```env
SPEECH_PROVIDER=openai
LOCAL_TTS_URL=
LOCAL_TTS_API_KEY=
```

Use `SPEECH_PROVIDER=local` only after `Self-Host` is deployed somewhere reachable by this backend.

## Backend Flow

```text
Frontend
  -> AI Sources /api/v1/ai/chat or voice endpoint
  -> LocalSpeechProvider
  -> hosted Self-Host /v1/voice/synthesize
  -> CosyVoice runtime, or F5-TTS fallback
  -> audio bytes
```

## Voice Safety

- Only use voice samples from the person who owns this AI and has explicitly consented to cloning their voice.
- Record consent metadata through `POST /api/v1/ai/voice/consent` before enabling local voice output.
- Keep actual reference audio and model artifacts on the Self-Host machine only.
- Keep `VOICE_ALLOW_REQUEST_REFERENCE_OVERRIDE=false` in Self-Host production environments.
- Use a strong shared secret: `LOCAL_TTS_API_KEY` in this backend must match `LOCAL_AI_API_KEY` in Self-Host.

## Configure AI Sources

Set these values only after the external voice host is ready:

```env
SPEECH_PROVIDER=local
LOCAL_TTS_URL=https://self-host.example.com/v1/voice/synthesize
LOCAL_TTS_API_KEY=the-same-value-as-LOCAL_AI_API_KEY
LOCAL_TTS_REFERENCE_AUDIO_PATH=
LOCAL_TTS_REFERENCE_TEXT=
LOCAL_TTS_MODEL=
```

When using the standalone `Self-Host` project, reference audio, reference text, engine, and model selection are configured inside that project. This backend only needs the service URL and API key.

## Verify The Integration

Check Self-Host directly:

```bash
curl -s https://self-host.example.com/health
curl -s -H "Authorization: Bearer $LOCAL_TTS_API_KEY" https://self-host.example.com/v1/capabilities
```

Check through this backend:

```bash
curl -s -H "Authorization: Bearer $APP_API_KEY" http://127.0.0.1:8000/api/v1/ai/voice/local-health
```

Then test speech:

```bash
curl -s -H "Authorization: Bearer $APP_API_KEY" \
  -H "Content-Type: application/json" \
  -X POST http://127.0.0.1:8000/api/v1/ai/speech \
  -d '{"text":"Self-Host integration test.","response_format":"mp3"}' \
  --output voice-test.mp3
```

## Development Notes

- First generation can be slow because models need to download and warm up.
- CPU can work but will be slow; a CUDA-capable NVIDIA GPU is the practical production path for cloned voice.
- Keep OpenAI speech configured as the default fallback until the hosted Self-Host service is reliable.
- Do not commit `.env`, private voice samples, generated audio, model weights, or checkpoints.
