# musicgen-backend

Vercel serverless backend for MusicGen AI music generation.
Powers all SoundSplash and Aether apps.

## Deploy

1. Import this repo into Vercel
2. Add environment variable: `HUGGINGFACE_API_TOKEN` = your HF token
3. Deploy

## API

**POST** `/api/generate`

```json
{
  "mode": "Deep Focus",
  "texture": "Minimal Piano",
  "duration": 30
}
```

For SoundSplash Script (3-layer):
```json
{
  "mode": "Drama",
  "texture": "Sparse Strings",
  "genre": "Prestige Drama",
  "scene": "Quiet Moment",
  "duration": 30
}
```

**Returns:** `audio/flac` — real AI-generated music

## Notes
- Model: facebook/musicgen-small (free, HF Inference API)
- Rate limit: ~1 req/20-30 seconds on free tier
- Results cached in-memory per cold start
- Tone.js fallback built into all frontend apps
