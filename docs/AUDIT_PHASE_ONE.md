# Bright Side Daily 2.0 — Phase One Repository Audit

**Audit date:** 26 November 2026  
**Repository:** https://github.com/gichagajohn/bright-side-daily  
**Inspected snapshot:** `30cd9de707e74ec2bab2020e782603d2e99ac3fa`  
**Disposition:** Preserve the existing project; repair publishing safety before changing production.

## Scope and evidence

Cloned the public repository read-only. Inventoried all tracked project files, parsed all Python source and content/state JSON, inspected all four workflows, traced active publishing, content, storage, narration and analytics paths, and reviewed supporting generator entry points. Nine isolated checks completed successfully; six of those checks reproduce or confirm defects rather than certify correct production behaviour. No existing automated test suite or test workflow was found.

The public GitHub Actions API returned 15 recent runs marked successful. The committed Facebook history contains 1,235 success records, dated June–November 2026; Instagram history contains 77 records. These are evidence of recorded operation, **not independent verification that every post is live or that videos are classified as Reels**. Error suppression and zero exit statuses make a green workflow insufficient evidence. The committed publisher log contains 218 ERROR occurrences; these are historical, not a diagnosis of the present Page.

**No production changes, API publishing, secret retrieval, database writes, content-library regeneration or live rendering tests were performed.** The source checkout remains clean. This is a repository-level audit, not a completed live infrastructure/security certification. Full Git history, dependency vulnerability scanning, authenticated Meta permissions, actual rendered media, GitHub billing/storage and Supabase bucket policies remain unverified.

## Architecture: what actually runs

```text
post_scheduler.yml (8 daily cron entries)
  -> scheduler.run_slot
     -> ContentAgent.pick -> local JSON history (written immediately)
     -> PexelsPhotoGenerator -> square photo with text
     -> SocialPublisher
        -> FacebookPublisher.publish -> photo (or text fallback on retry)
        -> Instagram enabled/slot checks
           -> _publish_instagram
              -> Reel generator for 3 configured slots
              -> FacebookPublisher.publish_reel -> Supabase -> Facebook video
              -> InstagramPublisher.publish_reel -> Supabase -> Instagram

bible_post.yml (daily)
  -> RSS headline classification -> existing KJV verse -> Pexels image
  -> same SocialPublisher

instagram_analytics.yml -> IG insights + schedule suggestions + comment replies
weekly_report.yml and main posting workflow -> Facebook PerformanceAgent
```

Agents are ordinary Python classes/functions, communicating through dictionaries and filesystem JSON—not autonomous model services. Supabase is used for temporary public media hosting, not durable publishing state. There is no implemented original narrative-writing agent.

## Priority findings

### Critical: fix before disabling Instagram or running deployment tests

1. **Facebook video generation is gated by Instagram.** `src/agents/social_publisher.py:166` renders and publishes Facebook videos inside `_publish_instagram`. Setting `PLATFORMS=facebook` or removing Instagram credentials prevents this path. The Facebook photo still publishes. Extract an independent Facebook Reel route first; preserve the image route. The Facebook Reel result is discarded, so overall success can conceal its failure.

2. **Workflow dry-run can still publish.** The main workflow's `Retry failed posts` step receives Facebook credentials but no `DRY_RUN` value or dry-run guard. It executes before the dry-run-protected posting step. Do not use the current workflow's dry-run as a safe test procedure. Content selection also consumes real history during a dry-run. Isolate state and enforce no-write behaviour across every stage.

3. **Analytics writers have incompatible schemas.** `instagram_insights.py:211` replaces `data/metrics/engagement.json` with only weights and a timestamp. `performance_agent.py:132` expects `engagement_by_category` and other fields. Reproduced a `KeyError` using that schema in temporary storage. Separate platform/format datasets and validate schema versions.

### High: publishing correctness and reliability

4. **The Reel-labelled publisher defaults to `/videos`, not a dedicated verified Reel lifecycle.** `facebook_publisher.py:76` switches to `/video_reels` through an environment option, but still submits the same single `file_url` request; no staged Reel upload lifecycle is implemented. Do not assume either returned IDs or the method name prove Reel classification. Verify the current Meta-supported flow/version and Page eligibility before a controlled test. Facebook API version is hardcoded to `v19.0`; compatibility with the current platform has not been established.

5. **Staged media is deleted immediately after the video submission response.** `publish_reel` does not wait for confirmed remote processing. This creates a fetch/processing race. Persist upload/job IDs, poll terminal state, then clean up; retain failed assets with bounded expiry. Supabase deletion ignores HTTP error statuses.

6. **Duplicate prevention is not publication idempotency.** `ContentAgent.pick` records a choice before rendering or posting and resets category history below 30 remaining entries. There is no unique slot/date/format publishing job, atomic claim or reconciliation after an ambiguous timeout. Facebook photo retries can create duplicates after an accepted request with a lost response. JSON writes and Git commits are not transactional.

7. **Retry jobs lose the original media.** `facebook_publisher.py:276` replays `publish(item['post'])` without the image/video; it can turn a failed photo or video into a text post. Video HTTP failures returning `success=False` are not added to the failure queue, while exceptions are. Preserve format, asset references, stage and retry eligibility.

8. **Workflow success is not publishing success.** `scheduler.py` prints error results without exiting nonzero. Metrics failures are suppressed. State-push failure is tolerated after publishing. The main workflow lacks concurrency protection, and the separate workflow groups do not protect shared state across workflows. Bible workflow only commits verse history, not publisher success/failure history generated in its run.

### High: Reel production and quality

9. **Current videos are animated quote cards, not cinematic footage.** `reel_generator.py` renders black-background PNG frames at 1080×1920/30 fps, then encodes H.264/yuv420p MP4 with faststart and AAC when audio exists. Retain those output settings and useful typography primitives. There is no Pexels video search, scene planner, clip registry, footage cache, scene transition pipeline or licensing manifest.

10. **Narration failure is allowed through.** Edge TTS falls back to gTTS, then music-only/silent output. No 20–35-second requirement, narration-presence gate, loudness measurement, clipping check or final media validation exists. Both current TTS options depend on external services. Preserve Edge TTS as a candidate, but validate service terms/reliability; an offline fallback needs a suitably licensed model and voice, not an assumed free entitlement.

11. **Subtitle alignment can silently lose words.** `_timings` truncates available boundary events; if marks are fewer than display words, `_render_frames` assigns the remaining words an effectively unreachable start time. Confirmed with an isolated check. gTTS timings are uniformly estimated, not accurately aligned. Audio-mix failure can return undelayed voice while caption times still include a 700 ms lead-in. Use phrase captions, verified alignment and bounds checks.

12. **Fail-open rendering and branding need correction.** Render exceptions can call `_static_reel` with `card_path=None` for dictionary inputs. Long text can overflow after minimum-font fallback. The signature defaults to JG at y=1660, not consistent Bright Side Daily branding within validated Facebook safe zones. There is no QC gate for decode integrity, narration, subtitles, branding, duplicates or rights. A missing narrator must stop a Reel, not downgrade it silently.

13. **Rendering is unnecessarily expensive.** The renderer writes one full-size PNG for every frame (600–1,050 frames for a 20–35-second video). Subprocesses lack explicit timeouts. Prefer FFmpeg-native video compositing and subtitles, bounded downloads, cached source footage and measured resource budgets.

### Content and supporting images

14. **Retain curated content, replace synthetic replenishment.** Category files contain 6,542 entries in total, including 457 Bible entries and 732 relatable entries. The self-improvement file contains one exact duplicate. The generator pads base quotes with prefixes, suffixes, truncation, category labels and numbered originals; it is not original storytelling. Running it can overwrite larger current category files with smaller generated sets. Do not regenerate production libraries during migration.

15. **Performance weights do not affect selection.** `ContentAgent.pick` uses `random.choice` within a fixed slot/category mapping; weights are loaded and attached to payloads but do not influence that choice. Do not describe current behaviour as performance-adaptive scheduling.

16. **Pexels photos are worth retaining.** Current images use genuine downloaded photographs, category styling and Bright Side Daily text. Add pixel-measured wrapping, crop/focal-point checks and asset provenance. There is no used-photo tracking or cache. Bible image generation always chooses the first search result, encouraging repetition, and stops drawing lines after y=900, which can truncate text.

17. **Keep Bible references tied to vetted source text.** The world-news path selects existing verses rather than inventing quotations. Preserve this property. Standardise `reference` versus `bible_reference`; keep devotional commentary separate from verbatim scripture. Verify source/translation rights and verse accuracy rather than assuming every library record is correct. RSS classification is keyword-based and feed calls have no explicit timeout at the call site; it is not fact-checked news research.

## Actual schedule versus requested schedule

| Workflow slot | Current EAT | Requested treatment |
|---|---:|---|
| Morning motivation | 08:00 | Reel at 08:00 — matches |
| Positive quote | 10:00 | Supporting image policy |
| Self improvement | 11:00 | Supporting image policy |
| Funny/relatable | 12:00 | Supporting image policy |
| Midday encouragement | 13:00 | **Move Reel to 16:00** |
| Bible (separate workflow) | 17:00 | Preserve pending image policy |
| Engagement question | 18:00 | Supporting image policy |
| Evening reflection | 19:00 | Reel at 19:00 — matches |
| Night inspiration | 21:00 | Supporting image policy |

Three default Reel slots exist, but all are behind the Instagram gate and may also create a Facebook image. README, Python schedule and workflow disagree. The requested three Reel cron hours are **05:00, 13:00 and 16:00 UTC** for Nairobi. Current workflow detects the slot from runner wall-clock hour, so delayed execution can pick the wrong slot or default to morning. Use scheduled-event identity and a timezone-aware configurable schedule with a unique intended-slot key. Nairobi does not require DST conversion; other zones must use IANA timezone rules. GitHub cron is not an exact-time delivery guarantee.

## Analytics assessment

- Existing Facebook collection is basic likes/comments/shares, with `impressions` treated as reach. Supported metrics and permissions have not been verified against the current API.
- Missing token or post ID causes random simulated engagement to be recorded in the same dataset as real results. Remove that production fallback; unavailable must remain unavailable.
- Each collection appends another record for every recent post; `total_posts_tracked` is 188,379 despite 1,235 logged successes. That count is observations, not distinct posts.
- `_find_top_content` assigns the latest category-level score to each item in that category rather than joining per-post metrics. Rankings are therefore not trustworthy.
- IG post success logs do not reliably retain the format that the insights collector expects. IG repeated snapshots also inflate the schedule optimiser's sample count.
- No dedicated Facebook Reel watch-time, average-watch-time, retention, follower-growth or conversion tracking exists. No hook, voice, footage-style or duration metadata supports those comparisons.
- Retain weekly reporting cadence, not its current ranking logic. Build media-ID-keyed observations with collected timestamps, metric availability/error reasons and cohort age. Keep Page follower growth distinct from attributable Reel follower conversion unless the API actually supports attribution.

## Security, dependencies and dead code

- A limited current-tree pattern scan found no matching long Meta, GitHub or JWT token strings. This is **not** a clean security certification or a full-history secret scan.
- The repository now publicly exposes committed publishing history and operational logs. Main workflow force-adds `data/` despite log ignore rules. Retain operational history in restricted durable storage and publish only sanitised reports; review history before deciding what remains public.
- Requests sometimes place tokens in query strings and log raw exceptions/API bodies. Add central redaction before further log collection.
- Manual workflow inputs are interpolated directly into shell source; pass them through environment variables and validate allowed slots instead.
- All seven Python dependencies use lower bounds without lockfiles. An exact deployed dependency set is unknown; no package is labelled vulnerable merely from this file. Add a reproducible tested lock and automated vulnerability updates.
- Action references use version tags rather than immutable commit pins. Restrict write permissions to the state-persistence job; avoid untrusted branch code receiving production secrets.
- `python-dotenv` has no evident active loading path. `.env.example` advertises an OpenAI key but no corresponding active OpenAI implementation was found. Remove obsolete configuration rather than adding a paid API.
- Legacy gradient image and Pexels meme generators, Story generator/publisher and token-refresh helper have no active scheduled caller in the inspected paths. Carousel is disabled by default but can be enabled by environment overrides. Archive only after regression coverage; do not blindly delete shared black-card/font utilities used by the current Reel renderer.
- Repeated font/wrapping/branding logic, duplicated IG publish loops and repeated JSON load/save helpers are consolidation candidates after behaviour is tested.
- Audio README describes controls not implemented by the renderer. No music files are committed. External tracks have no machine-readable licence validation. Generated tones do not justify a guarantee that platforms can never issue a claim.

## Supabase audit boundary

The connector is available and project listing succeeded. None of the listed projects is explicitly named Bright Side Daily; repository configuration injects the project URL via a secret. I did **not** guess which project is production, inspect unrelated database content, fetch keys or alter anything. Confirm the project reference and bucket name (not the service key) to enable targeted read-only checks of bucket access, policies, object retention and usage.

The code uses a privileged service key, public URLs and UUID object names. It does not persist asset provenance or publishing jobs in Supabase. Existing infrastructure can support a small durable job/asset registry, but schema/policy changes require an explicit migration and rollback review.

## Retain / improve / remove

| Retain | Improve | Remove from active operation |
|---|---|---|
| Existing repository and Python structure | Independent FB Reel route and verified lifecycle | IG publishing, analytics and comment workflows |
| Facebook supporting-photo route | Idempotency, typed retries and reconciliation | IG secrets in active workflows after decoupling |
| Pexels integration and curated libraries | Cinematic multi-scene assets and originality checks | Simulated metrics in production |
| FFmpeg, Pillow, Edge TTS candidate | Subtitle alignment, narration fallback, fail-closed QC | Silent/music-only Reel fallback |
| Supabase media-hosting utility | Delayed cleanup, least privilege, durable jobs | Blind media-to-text retries |
| GitHub Actions and weekly reporting | Single schedule configuration and failure alerts | Repetitive library-padding and unused config |

## Proposed implementation sequence (not yet deployed)

1. **Safety branch:** add regression tests; decouple Facebook Reels; disable active Instagram paths; enforce dry-run isolation, nonzero failures and typed job state. Preserve image publishing.
2. **Reel engine:** introduce structured scripts and scene plans, Pexels video cache/provenance, clip reuse limits, natural narration, verified phrase captions, modest transitions and loudness targets. Keep output validation mandatory.
3. **Content:** ten requested categories, hook/story/conclusion records, similarity checks and vetted scripture. Benchmark any local open-source model on available CPU/runtime before adopting it; no paid API or unverifiable claim of endless originality.
4. **Scheduling and analytics:** three daily Reels at requested EAT times, selected images, capability-tested Meta metrics, weekly evidence-based reports. No automatic frequency increase.
5. **Deployment gates:** offline tests -> private artifact review -> read-only permission/metric discovery -> explicitly approved test Page or single controlled live test -> gradual production rollout.

Useful low-risk additions: choose covers from actual scene frames, store hook and scene metadata, keep a 7-day draft calendar, compare topics at equal observation ages, and alert on failed or ambiguous publishing jobs. Defer automatic trending-topic publication and audience targeting until sources, privacy and safety rules are defined.

## Tests and change report

`python /home/user/bright-side-audit/checks.py` — **9/9 audit checks passed**:

- Python syntax; JSON syntax; four workflow YAML parses.
- Reproduced pre-publish history consumption.
- Confirmed Facebook-only routing never calls the Reel generator (mocked publisher; no network).
- Reproduced incompatible metrics-schema exception using a temporary file.
- Confirmed incomplete word-boundary handling.
- Confirmed requested midday cron is absent.
- Confirmed retry step lacks dry-run protection.

These are audit probes, not end-to-end acceptance tests. Narration, Pexels downloads, rendering, subtitle playback, Facebook publishing, failure recovery under real API conditions and GitHub execution remain **untested here**. YAML parsing is not full Actions validation.

**Repository files changed: none.** Audit documents and checks were created outside the checkout in `/home/user/bright-side-audit/`. No branch has yet been pushed. Public access supports clone/read but does not grant authenticated push permissions.

## Deployment and rollback requirements

Before implementation commits, create `upgrade/facebook-reels-v2` from the audited baseline (or re-audit changes if production advances). Test against isolated fixtures and draft assets. Do not copy test state over production history. Capture deployment SHA and back up durable job/state data before migration. Gate production publishing separately from artifact generation.

Rollback should disable the new publisher, reconcile in-flight remote jobs, revert code/workflows to a reviewed baseline and retain the authoritative publish ledger. **Do not restore stale history blindly:** that can republish content already accepted by Facebook. Since the baseline is Instagram-enabled, a rollback must retain the Facebook-only safety switch rather than reactivating Instagram unintentionally.

### Required confirmations/access

- Confirm which Supabase project and bucket belong to Bright Side Daily; no secret values needed in chat.
- Authenticated GitHub write access is needed to push the implementation branch; until then changes can be prepared locally as reviewable patches.
- Existing Meta/Pexels secrets should remain in protected execution environments. A later approved test procedure needs those credentials there, not pasted here.
- Approval is required before experimental live content or production schema changes. No paid services are proposed.
