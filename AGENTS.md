# dwm agent notes

If you change any dwm key/button binding or any st-reflow shortcut displayed by the keymap, update `dwm-keymap` in the same change. `Super+Shift+K` opens this help, so stale entries are user-visible bugs.

Keep `config.def.h` and tracked `config.h` synchronized.

## Change-size history (required)

After each modification, run `python3 scripts/update_cloc_by_commit.py` and include
`scripts/cloc_by_commit.md` in the change. Run it again after committing or changing
branches so WORKTREE is replaced by the actual commit row. Do not commit on the
user's behalf merely to update this report.

Use `python3 scripts/update_cloc_by_commit.py --check` to verify freshness and
`python3 scripts/test_cloc_history.py` when changing reporting machinery.
Report the latest runtime C and runtime-script totals and net deltas in the final
response; mention support C/scripts/build deltas when nonzero. Documentation-only
and reporting-only changes should explicitly report zero measured change.

Preserve the fork baseline and counting policy in `scripts/cloc-history.json`.
Add reviewed descriptions there for unclear commit subjects; new commits otherwise
use their subjects. Keep runtime vs support categories and effective-config
exclusions consistent. Include staged/unstaged and nonignored new source files in
the WORKTREE measurement; do not attribute them to an existing commit.
