# Editorial follow-up — 26 November 2026

Applies on top of the two existing upgrade commits. Does not alter main, publishing
flags, Supabase schema, narration providers or transition effects.

## Changes

- Captions use the approved script, retaining timestamps from the successful
  provider/recognizer. Same-count number formatting is reconciled (ten/10).
- A small near-spelling discrepancy such as spent/spend is restored from the
  script and recorded in `voice.alignment_changes`. This is a conservative ASR
  reconciliation, not evidence that the spoken waveform is verbatim. Missing,
  extra, materially different, or excessive discrepant words fail closed.
- Phrase groups respect sentence punctuation and pauses; line wrapping balances
  two lines and penalizes isolated trailing words. Short phrases remain possible
  when they are complete sentences or needed to preserve timing.
- Captions no longer linger throughout long speech pauses. Meaningful phrase
  emphasis replaces unconditional last-word highlighting.
- Pexels candidates are ranked/filtered by source-title keywords, with explicit
  sunrise/sunset contradiction checks. The bus story uses scene-specific
  commuter, phone and traffic requirements. No fallback to unrelated footage.
  Metadata can be incomplete: a suitable clip may be rejected, and metadata
  filtering cannot guarantee visual relevance, model releases or rights clearance.
- Workflow preview defaults to `bsd-story-010` for a comparable second preview.
  The workflow supplies that default even when the main-branch UI has not yet
  displayed the new story_id field. Only dry runs honor the story ID; live content
  selection remains unchanged.

## Validation

40/40 tests passed on Python 3.11, including real synthetic-media FFmpeg rendering.
Actionlint passed (without shellcheck). The user's uploaded manifest was replayed
locally: exact approved caption text recovered without changing word timestamps;
spent/spend and ten/10 changes recorded. This does not re-render the actual video
because its audio/source files were not uploaded. No live Pexels or Meta requests
were made by this patch test. No production data changed.

## Apply from Windows CMD

Download `bright-side-daily-editorial-fix.patch` into Downloads. In your EXISTING
review clone, run each line separately; stop on any error:

```cmd
cd /d "%USERPROFILE%\Downloads\bright-side-daily-v2-review"
git status
git switch upgrade/facebook-reels-v2
git pull --ff-only origin upgrade/facebook-reels-v2
git am --3way --whitespace=nowarn "%USERPROFILE%\Downloads\bright-side-daily-editorial-fix.patch"
git push origin upgrade/facebook-reels-v2
```

Before applying, `git status` must show a clean working tree. Do not apply the
original two-commit patch again. This new commit updates the existing PR.
If patch application conflicts, stop; `git am --abort` cancels this patch attempt.
Never force-push main.

Once CI is green, run post_scheduler.yml on `upgrade/facebook-reels-v2`, select
`morning_motivation`, and set `dry_run=true`. If shown, keep story_id as
`bsd-story-010`. Review the new cover/video and upload manifest.json and preview.json.
Keep the PR unmerged and live publishing disabled during this review.
