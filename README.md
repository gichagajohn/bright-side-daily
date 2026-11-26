# Bright Side Daily — Facebook Reels upgrade

This is an **in-place upgrade of the existing project**, not a replacement repository.

**Deployment status:** locally tested implementation; not yet approved for live publishing.
Read [deployment and rollback](docs/DEPLOYMENT_V2.md) before merging. Publishing defaults OFF.
The old implementation continues unchanged on your production branch until you merge this patch.

## Active architecture

`GitHub heartbeat → configured due slot → Supabase unique job claim → content → media → QC → Facebook → confirmed job`

- Facebook only. Three Reel slots: **08:00, 16:00, 19:00 Africa/Nairobi**.
- Supporting images: positive quote **10:00**, Bible encouragement **17:00**, engagement question **18:00**.
- Configure times/formats in `config/publishing.json`. A UTC half-hour heartbeat evaluates IANA timezone rules; the job key contains the intended local day and slot. GitHub can delay scheduled jobs.
- Existing curated image libraries and Pexels photo generator are retained. Existing history files are not overwritten.
- Reels use three distinct Pexels portrait videos, crossfades, restrained grading, phrase captions, Bright Side Daily branding, H.264/AAC and a 20–35 second QC gate.
- Edge TTS has a second voice fallback, then gTTS plus validated Whisper timings. Missing or mismatched narration stops publication.
- No unlicensed music is bundled. The current mix is narration-only.
- Direct Facebook Reel upload: start → binary upload → finish → processing confirmation. No Instagram/Supabase-media dependency for video upload.
- Supabase holds unique job, clip and metrics records. Mutating Facebook requests are never blindly repeated after a timeout.
- Weekly reports separate Reels and images, distinguish unavailable metrics from zero, and avoid increasing publishing frequency.

## Honest limits

The package includes **20 original narrative seeds across ten categories**. They are finite and will not be silently recycled. Optional `BSD_LOCAL_MODEL` uses an already-running local Ollama model; a model/runtime is **not** installed by the stock GitHub workflow. Unlimited unattended content research/generation is not complete. Replenish reviewed stories or benchmark/provision a free local model before seed exhaustion.

Natural narration and real Pexels footage must pass a private GitHub artifact preview. The sandbox's live narration test failed; passing synthetic FFmpeg tests does not prove voice quality. Current Meta fields/permissions must be verified on your Page. No live Facebook test has been performed.

## Local engineering tests (Python 3.11, Linux)

```bash
python -m pip install --require-hashes -r requirements-ci.lock
# Install FFmpeg and DejaVu fonts with your OS package manager first.
PYTHONPATH=src python -m pytest -q
python src/scheduler.py --schedule
```

For a credentialed **render-only** preview:

```bash
python src/scheduler.py --slot morning_motivation --dry-run
```

This uses external footage/TTS services but never invokes Facebook or writes the production ledger. Read secrets from the environment; `.env.v2.example` is documentation, not an automatically loaded file.

See [implementation/test results](docs/IMPLEMENTATION_REPORT.md), [deployment](docs/DEPLOYMENT_V2.md), and [original README](docs/LEGACY_README.md). The legacy README's operational commands are archived, not current instructions.
