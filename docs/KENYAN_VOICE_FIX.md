# Verified Kenyan voice dependency fix

Compared edge-tts 7.2.7 and 7.3.1 with the same supporting dependencies:
- 7.2.7 lists en-KE-ChilembaNeural, Male, but synthesis fails with WSServerHandshakeError HTTP 403.
- 7.3.1 lists the same voice and synthesizes 29,376 audio bytes with 11 word boundaries.
- Actual legacy renderer using 7.3.1 produced an 8-second 1080x1920 H.264/AAC Reel, 240 frames, with the Kenyan male voice at +0% rate. Technical QC and full decode passed.
- Full offline suite: 46 passed (including FFmpeg test). Actionlint passed with shellcheck disabled.

Update both hash locks, requirements-v2.txt and voice diagnostic install pin.
Hashes taken from PyPI 7.3.1 release metadata. Dependencies remain compatible.
No different voice, pitch modification or paid provider introduced. No production
writes or Facebook publication made during this verification. GitHub-runner
verification and user approval of pacing are still required.
