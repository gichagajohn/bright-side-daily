# Controlled Facebook visual/schedule rollback

Restores the existing quote-card Reel generator and legacy quote libraries,
not a blind git revert. Retains the Facebook staged uploader that has completed
a live publication, durable job keys/history, and Facebook-only automation.

Schedule (Africa/Nairobi): Reels 08:00, 13:00, 19:00; images 10:00, 11:00,
12:00, 17:00 (Bible), 18:00, 21:00. This matches the old workflow cron times,
including its 13:00 midday slot (not the newer 16:00 slot). One format per
slot: unlike the old coupled system, Reel slots do not also publish a photo.

Explicit cron-to-slot dispatch replaces idle heartbeat filtering. Late starts
still select their named slot instead of being rejected by the 90-minute window.
This cannot guarantee GitHub delivers every cron event. Cross-midnight delays
still use the runner's local date; do not manually backfill without reviewing
ledger and Page history.

Old appearance: dark quote card, animated words, original Edge/gTTS voice
selection, generated ambient pad. No cinematic stock scenes. Original gTTS
fallback uses approximate word timing. Require successful narration and a valid
H.264/AAC 1080x1920 video; reject silent/static fallbacks. Do not use arbitrary
assets/audio tracks. Legacy duration validation is 3–90 seconds, not cinematic
20–35 seconds; legacy QC does not certify cinematic caption bounds/loudness.

Instagram stays disabled. Existing content and Supabase rows are untouched.
No old failed-post queue is replayed. Existing safe preflight retry rules remain.
New Reel selections use legacy libraries, not the finite 20 cinematic story seeds;
exhausted legacy categories still stop instead of silently recycling content.

Validation: 44 tests pass, 1 synthetic media test skipped (FFmpeg absent in this
sandbox); actionlint passes with shellcheck disabled; Python compile checks pass.
Narration failure, missing renderer output, three-Reel limit, schedule mapping
and unknown cron rejection tested. No live post or actual video render was made
while preparing this patch. GitHub preview and one live check remain required.

Deployment: keep BSD_ENABLE_PUBLISH=false. Apply patch on rollback branch based
on main; push and open PR, wait for CI. Run morning_motivation with dry_run=true
on the rollback branch and inspect the artifact. Merge only after preview review.
Then enable publishing and run one explicit live slot; verify Page and ledger.
Never delete ledger rows to force a retry. Analytics stays off pending validation.
