# Implementation and validation report

Date: 26 November 2026. Branch: `upgrade/facebook-reels-v2`. Base: `30cd9de`.

## Implemented locally

| Area | Implementation |
|---|---|
| Facebook-only safety | Removed active IG routes/workflows/secrets; legacy SocialPublisher is a fail-closed guard. Unified image/Bible/Reel scheduler. |
| Durable history | Additive Supabase ledger migration; unique date/slot jobs and content hashes; atomic clip claims; held ambiguous submissions. Migration not applied. |
| Publishing | Separate Facebook photo and staged direct Reel uploads; persistent stages/IDs; terminal processing poll; read-only reconciliation tool. |
| Reel production | Three portrait Pexels scenes; cache/provenance/30-day reuse exclusion; restrained grading and crossfades; 1080×1920 H.264/AAC; measured phrase captions; brand and cover-frame output. |
| Narration | Edge TTS two-voice fallback; gTTS/Whisper independent-service fallback; validated timing coverage; no silent-video fallback. |
| Content | 20 authored narrative seeds across all ten requested categories; beginning/middle/end; repetition checks; optional local Ollama adapter; existing scripture sources retained. |
| Quality gates | Decode integrity, file size/hash, codec/resolution/duration, AAC presence, measured loudness/peaks, caption bounds, source metadata and distinct clip hashes. |
| Scheduling | Central local-time configuration, DST-aware due selection, 90-minute lateness window, 3 Reels/day and 3 selected supporting images. |
| Analytics | Separate Reel/image observations; per-metric capability probes; unavailable != zero; watch/share/follow comparisons and cohort-aware weekly report; Page follower snapshots. |
| Security/cost | Pinned Actions SHAs, hashed Python dependency locks, read-only repository permissions, redacted errors, no committed runtime data, bounded caching/retention, idle-run dependency skip. |

## Preserved and deliberately changed

Preserved existing content/state files, photo generation, Bible verse lookup, supporting Facebook images and source modules useful for rollback. No existing production records were overwritten. The old README is archived rather than silently misleading users.

Deliberately retired the old multi-platform entry point, blind retries and automatically scheduled Instagram analytics/replies. The new main runner will not call the old Facebook publisher; that module remains historical code, not the active deployment path. Old redundant image slots are replaced by three selected supporting slots; their libraries remain intact. External background music is omitted until licensed tracks and provenance are supplied. No guaranteed legal clearance is inferred merely from a Pexels URL.

## Actual verification

- **31/31 tests pass on Python 3.11.18/Linux**, matching the workflow Python family. Also passed on Python 3.13.18.
- Includes a **real FFmpeg 1080×1920 render** with three synthetic source clips, captions, crossfades, H.264/AAC, cover extraction, decoding and loudness analysis. This is an engineering fixture, not a finished brand Reel or a real narration test.
- Real Pillow image layout tested with a local fixture; oversized text rejected rather than truncated.
- Mocked Meta lifecycle, failure handling, read metrics and duplicate claims tested with network disabled. These are not live Facebook tests.
- Checked configured Nairobi hours, delayed slots and a DST timezone.
- `actionlint` 1.7.7 passed all workflows. Shellcheck was unavailable and not run. The workflows have not been executed by GitHub in this environment.
- Python compilation and dependency consistency checks passed.
- Initial dependency audit flagged old Pillow/Requests pins. Updated to Pillow 13.0.0 and Requests 2.34.2, retested, and the final resolved/hash-locked runtime dependency audit reported **no known vulnerabilities** at check time. This does not guarantee absence of vulnerabilities.
- Current Supabase bucket configuration and empty object inventory inspected read-only. No secrets fetched and no schema/data writes performed.
- A live Edge TTS request failed with `WSServerHandshakeError`. The complete fallback chain also failed to produce aligned narration in this sandbox. Those failures were not suppressed or counted as successful voice generation.
- No live Pexels request, Facebook post, Graph metric capability discovery, Supabase migration/ledger integration test or authenticated GitHub push was performed. Existing GitHub secrets are not readable from the public clone.

## Not complete / release gates

1. **Professional output approval:** a real stock-footage/natural-voice preview must run in GitHub with your Pexels secret and working narration services. Inspect the artifact before enabling live Reels. Automated geometry checks cannot certify pronunciation, emotional tone, perfect subtitle sync, brand aesthetics or copyright suitability.
2. **Unlimited content generation:** the finite seeds cover roughly six days at three/day if every story renders successfully. The optional local-model adapter is implemented but not model-benchmarked or provisioned in Actions. General trending-topic research, autonomous editorial fact-checking and unlimited original scripts are not finished.
3. **Live API verification:** staged Reel requests match the documented shape, but Page permissions, selected Graph version and real metric support must still be checked. Controlled live image and Reel tests require explicit approval.
4. **Production persistence:** the supplied migration and REST ledger are not yet live-tested. Duplicate safety relies on its unique constraints, checkpoint availability and the conservative hold-on-uncertainty policy. SQL migration is not automatically executed by GitHub.
5. **Analytics maturity:** no real performance recommendations can be justified yet. Reports refuse automatic volume increases. Grouping by exact hooks/queries often yields sparse cohorts; attribution, confidence intervals, richer dashboards and automatic calendar research remain future work.
6. **Rights and service terms:** no external music bundled; review stock-use context, TTS usage terms and any chosen local model/voice licence before production.
7. **Observability:** runtime seconds, artifact bytes and failure artifacts exist; full GitHub billing, Supabase quota alerts, a scheduled unresolved-job reconciler and an operations dashboard are not implemented. Reconciliation is deliberately explicit.

## Source references for implementation shape

Meta's Page Reel reference specifies start/finish phases, video IDs, upload URLs and publication state. [1](https://developers.facebook.com/docs/graph-api/reference/page/video_reels/)

Meta's Video Insights reference lists Reel play, watch-time, social-action, follow and retention metric candidates. The implementation probes them individually; documentation is not proof of availability on this Page. [1](https://developers.facebook.com/docs/graph-api/reference/video/video_insights/)

## Files and deployment

See the package's changed-file manifest and `docs/DEPLOYMENT_V2.md`. Patches apply to the existing repository and are supplied for review/push; they are not a claim that the entire Bright Side Daily 2.0 objective is already deployed or fully complete.
