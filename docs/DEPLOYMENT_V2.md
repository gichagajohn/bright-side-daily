# Deployment and rollback — Bright Side Daily v2

## Before you merge

This branch is an in-place upgrade based on `30cd9de707e74ec2bab2020e782603d2e99ac3fa`.
**Applying/pushing a patch does not activate production. Merging replaces the old workflows; the new publisher remains off until enabled. Plan the cutover so this deliberate safety gate does not surprise you.**

Do not force-push main, reset production history, delete held jobs, or remove the old GitHub secrets before validation. Historical source and records remain available; legacy multi-platform entry points are deliberately blocked. Old blind `--retry-failed`, `--all` and `--platforms` commands are no longer supported. Existing image generation and the selected image slots are preserved through the unified runner. Retired slots are not deleted from the content libraries.

## 1. Apply and push the supplied patches

Use the accompanying `PUSH-WINDOWS-CMD.txt` or `PUSH-BASH.sh` instructions. Both use a new branch and open a pull request. If there are conflicts, `git am --abort` returns you to the pre-apply state; do not guess at workflow conflict resolution.

The repository can continue publishing and updating history while you prepare the branch. Fetch current main before merge and resolve changed application/workflow files deliberately. Do not replace the newer `data/` state with an old checkout.

## 2. Prepare the existing Supabase project

Identified from existing publisher logs and checked read-only:

- Project reference: `lvadrzrbfxpizvwimqtf`
- URL: `https://lvadrzrbfxpizvwimqtf.supabase.co`
- Existing bucket: `social-images`; public; 50 MB limit; JPEG, PNG, MP4 allowed.
- No storage objects and no explicit storage policies were returned at inspection time. This is a snapshot, not a claim about future usage or other access controls.

Open **https://supabase.com/dashboard/project/lvadrzrbfxpizvwimqtf/sql/new**.
Paste and run `migrations/001_bsd_v2.sql` once. It only adds the `bsd_jobs`, `bsd_assets`, and `bsd_metrics` tables and restrictive grants/RLS; it does not modify existing content or buckets. The migration has **not** been run by the assistant, and SQL execution has not been integration-tested against production.

Do not paste the service key into a GitHub file, terminal command history, issue, or this chat. Existing repository secrets should already contain `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`. Check the URL matches the project above. A project API key is distinct from an Edge Function secret; the connector's project listing does not reveal your GitHub secret values.

If the migration fails, stop and inspect the error. Do not run a destructive reset. Rolling back code should leave these tables and their publish ledger intact.

## 3. GitHub configuration

Create a GitHub environment named `facebook-production`. Restrict deployments to trusted branches and require approval during testing. Existing repository secrets can remain; environment-specific secrets may override them.

Required secrets:

- `FB_PAGE_ID`
- `FB_PAGE_ACCESS_TOKEN`
- `PEXELS_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`

No `IG_*` secret is referenced by active workflows. Do not delete Supabase secrets when removing Instagram: the durable Facebook ledger now needs them.

Set repository variables initially:

| Variable | Initial value |
|---|---|
| `BSD_ENABLE_PUBLISH` | `false` |
| `BSD_ENABLE_REELS` | `false` |
| `BSD_ENABLE_ANALYTICS` | `false` |
| `FB_API_VERSION` | `v26.0` (verify against your app/Page) |

Only the default branch can publish through the shipped workflow, and live mode requires explicit enablement. The code does not infer permission from a working read-only request.

## 4. Validate before live publishing

1. Review the pull request and let the offline regression workflow pass.
2. Run the existing `post_scheduler.yml` workflow on `upgrade/facebook-reels-v2`, select `morning_motivation`, and set `dry_run=true`. The upgraded branch workflow defaults to render-only and has a default-branch live guard. This needs Pexels access and working TTS but no schema writes or Facebook publishing.
3. Download the `facebook-*` artifact. Check pronunciation, pacing, stock footage relevance, identifiable people/brands, transitions, caption timing and safe zones on a phone. Automated bounds checks do not certify artistic quality or every licence/legal consideration.
4. Preview the other Reel styles and each image slot with `dry_run=true`. No silent/music-only Reel fallback is allowed. If narration fails, fix service access/voice setup; do not bypass QC.
5. Apply the additive migration, then run the read-only preflight after the new workflow is available on main, or locally with protected environment variables: `PYTHONPATH=src python -m bsd.preflight`. This checks table readability and Page identity, not publication permission.
6. Review actual Meta permissions and app access for Page posting and insights. Confirm current Reel metric availability with read-only probes after a real approved media ID exists. Missing metrics remain null with error codes.
7. **Only after explicit approval**, perform one controlled test on a designated test Page or one agreed production slot. Test image and Reel paths separately. The shipped workflow has no automatic test-post creation or deletion. Do not assume a fake/synthetic offline fixture is suitable for Facebook.
8. Confirm the post in Facebook, its Reel classification where applicable, the recorded remote ID, and terminal ledger status. A request accepted by Meta is not enough.

You can invoke a branch preview with GitHub CLI (after pushing):

```text
gh workflow run post_scheduler.yml --ref upgrade/facebook-reels-v2 -f slot=morning_motivation -f dry_run=true
```

The patch does not automatically install a local text model on GitHub. Stock Actions uses the 20 unseen narrative seeds. Before they run out, add reviewed scripts to `content/reel_stories.json` or provision and benchmark an open-source model/runtime. A local Ollama process and `BSD_LOCAL_MODEL` are supported by `bsd.stories`; the environment variable alone does not install or run a model. Do not claim infinite original generation from these seeds.

## 5. Controlled activation

Merge only once the staging artifacts and planned cutover are approved. Enable `BSD_ENABLE_PUBLISH=true` to allow image jobs after their controlled test. Leave `BSD_ENABLE_REELS=false` until Reel rendering and a controlled live test are accepted. Enable Reels only after that approval; enable analytics separately after table/API checks.

The schedule stays three Reels/day. Supporting images run at 10:00, 17:00 and 18:00 EAT. No image is automatically published as a fallback for a failed Reel. Configured times are target times; GitHub's half-hour heartbeat and execution delays can make actual publication later. Due windows expire after 90 minutes instead of dumping missed content later. DST follows the configured IANA timezone; repeated clock hours share one date/slot key and cannot publish twice.

The new workflow never commits runtime state/logs to the public repository. Existing public history is retained rather than rewritten. Separately review historical exposure and rotate any credential found in a full-history secret scan. That complete historical scan is not part of the supplied verification.

## Recovery behaviour

- Network reads retry bounded transient failures.
- One automatic regeneration retry is permitted for a known `failed_preflight` job during its due window. It retains the same story and chooses fresh available assets. A persistent duration/voice defect needs correction, not unlimited retries.
- A crash leaving `claimed`/`rendering` is held for inspection. This deliberately favours avoiding duplicates over guaranteeing every slot.
- After a mutation begins, any uncertainty is held. Never delete the row or reset its status to replay it blindly.
- For a Reel with a recorded video ID, use `PYTHONPATH=src python -m bsd.reconcile --job-key "facebook:YYYY-MM-DD:morning_motivation:REELS"`. This only reads Meta. Add `--record-confirmed` only to persist a remotely confirmed completion; it does not upload or publish.
- A photo timeout without a remote ID requires manual Page inspection. Exactly-once delivery cannot be promised across an external API with an ambiguous response.
- Failed jobs exit nonzero; enable GitHub Actions failure notifications. Failure JSON and timing/storage summaries are included in artifacts without tokens/raw request logs.

## Performance and cost

FFmpeg normalises scenes sequentially to bound memory. No full-frame PNG sequence is generated. Footage is cached and pruned to an 800 MB soft cap; Actions cache keys roll daily, so monitor cache storage/quota and evictions. Artifacts retain for seven days (analytics 30 days). Idle heartbeats skip media dependency installation. Per-job elapsed seconds and artifact bytes are recorded. This is not a GitHub billing or Supabase quota dashboard; inspect account usage regularly.

Dependency locks include hashes and were tested on Python 3.11/Linux. To update them intentionally, use `uv pip compile` with Python 3.11 and `--generate-hashes`, rerun tests and a dependency audit. Keep free-tool model/service licensing and usage terms under review. No paid AI API is introduced.

## Rollback

1. Set `BSD_ENABLE_PUBLISH=false` and `BSD_ENABLE_ANALYTICS=false`; do not start another publisher while a run is in flight.
2. Inspect/reconcile in-flight jobs and save a protected ledger backup.
3. Revert the upgrade commits through a review branch, **but retain disabled Instagram workflows and a Facebook-only safety gate**. A blind full revert to the old main would restore Instagram and the unsafe dry-run retry step.
4. Prefer a reviewed image-only fallback through the new runner (`BSD_ENABLE_REELS=false`) while investigating video failures. This preserves the new duplicate protections and avoids returning to the original coupling.
5. Do not restore stale JSON state over the authoritative ledger or drop the v2 tables. Successful posts cannot be un-published by reverting Git commits.

No deployment, live publishing, remote schema changes or automatic rollback has been performed by this patch package.
