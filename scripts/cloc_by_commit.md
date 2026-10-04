# dwm: changes and cloc since the fork

Committed history through `937f79a7a7dcf06551685a2a358c7959a8cf0913`; cloc **2.10**.

## Provenance and method

- Upstream: https://git.suckless.org/dwm.
- Original fork baseline: `44dbc6809d05b8f2addc483f882e670db0b6b8e9`.
- Upstream HEAD verified during this review: `44dbc6809d05b8f2addc483f882e670db0b6b8e9`.
- Baseline verified as the upstream/local merge-base.
- transient.c is an upstream diagnostic, not part of the dwm binary; it is counted as support C. dwm-spawn.c is runtime C.
- The spawn/swallow branch commit b6df683 is integrated at merge 850a415 and detailed separately below.
- Main tables follow first-parent history, oldest first; dates are author dates. Merge rows include their complete first-parent delta, including conflict resolutions. Side commits are detailed separately, not added again to totals.
- C = runtime .c/.h files; one effective configuration header (tracked config.h/blocks.h, otherwise its .def.h template). Support C = test/diagnostic C sources. Runtime scripts are counted separately from build/test/update scripts.
- cloc code lines exclude blanks/comments. Deltas are signed net changes vs the preceding row, not diff insertion/deletion counts. Zero does not imply no behavior change. Embedded shell strings in C count as C; shell help heredocs follow cloc classification.
- Build = Makefile/config.mk. Docs, terminfo, binaries, images, generated buildinfo.h, unused configuration templates, and reporting files under scripts/ are excluded. --skip-uniqueness prevents duplicate-file suppression.
- Historical counts use Git blobs. WORKTREE, when present, includes staged/unstaged changes and nonignored untracked regular files; delta is vs HEAD, never folded into committed history. Report-only edits do not create a WORKTREE row.
- Requires Python 3.9+, Git and cloc. Regenerate: `python3 scripts/update_cloc_by_commit.py`. Validate freshness: `python3 scripts/update_cloc_by_commit.py --check`.
- Regeneration is offline: upstream provenance records the review-time verification, not a fresh network check.
- Add reviewed descriptions to scripts/cloc-history.json when a commit subject is unclear. Otherwise new commits automatically use their subjects. Keep baseline fixed; do not move it to a later upstream merge-base.

## Runtime changes

| Commit | Date | C code | Δ C | Script code | Δ scripts | Change |
|---|---|---:|---:|---:|---:|---|
| `44dbc68` | 2026-03-13 | 2466 | — | 0 | — | Upstream dwm 6.8 plus upstream fixes; fork baseline. |
| `6760c0c` | 2026-06-24 | 2466 | 0 | 0 | 0 | Track local config.h and add build-artifact ignores. |
| `476bda3` | 2026-06-25 | 2468 | +2 | 0 | 0 | Customize fonts/keybindings; add build script. |
| `630a973` | 2026-06-25 | 2486 | +18 | 0 | 0 | Add audio/media controls and launcher configuration. |
| `4f0230b` | 2026-06-26 | 2486 | 0 | 0 | 0 | Switch configured fonts to DroidSansM. |
| `625ca95` | 2026-06-26 | 2486 | 0 | 0 | 0 | Reduce configured font size. |
| `8bc9886` | 2026-07-06 | 2518 | +32 | 0 | 0 | Add configurable floating terminal launch support. |
| `fd4af73` | 2026-07-19 | 2544 | +26 | 42 | +42 | Add Super+Shift+K keymap menu and per-tag bar visibility tracking. |
| `e39092c` | 2026-07-20 | 2544 | 0 | 42 | 0 | Start spawned terminals in HOME. |
| `9d2fb98` | 2026-07-20 | 2548 | +4 | 66 | +24 | Add brightness-up/down scripts and bindings. |
| `c751510` | 2026-08-06 | 2595 | +47 | 66 | 0 | Add per-tag layout/master/bar state. |
| `e27aee9` | 2026-08-06 | 2597 | +2 | 88 | +22 | Refresh help and Brave launch fallback. |
| `409b7b0` | 2026-08-10 | 2624 | +27 | 93 | +5 | Add runtime tag renaming; synchronize config template; update help/build script. |
| `6630daa` | 2026-08-15 | 2628 | +4 | 97 | +4 | Add region/full-screen screenshot helpers and bindings. |
| `850a415` | 2026-08-15 | 2916 | +288 | 97 | 0 | Merge spawn-swallow: window swallowing, dwm-spawn IPC helper, build/install integration (b6df683). |
| `6d383a5` | 2026-08-25 | 2918 | +2 | 99 | +2 | Add suspend binding and help entry. |
| `eb26f97` | 2026-08-31 | 2918 | 0 | 113 | +14 | Add dwm-suspend backend wrapper; refresh docs/help and maintenance instructions. |
| `600ed7c` | 2026-09-04 | 2921 | +3 | 113 | 0 | Add Kitty and Ghostty terminal shortcuts. |
| `d36f9af` | 2026-09-09 | 2924 | +3 | 183 | +70 | Add floating st help viewer and binding; synchronize terminal help. |
| `16b3a48` | 2026-09-09 | 2924 | 0 | 185 | +2 | Document rectangular st copy mode. |
| `8756af6` | 2026-09-10 | 2925 | +1 | 185 | 0 | Recognize st-256color windows for swallowing. |
| `2dedbe3` | 2026-09-11 | 2932 | +7 | 197 | +12 | Harden hardware helpers; add CLI bar-font override and headless helper tests. |
| `e513956` | 2026-09-13 | 2932 | 0 | 197 | 0 | Document dependencies and Mint/Void setup. |
| `12f7473` | 2026-09-13 | 2935 | +3 | 203 | +6 | Align fonts with session/dmenu-font policy; add Super+F1–F4 audio controls and help. |
| `8cad9c0` | 2026-09-13 | 2935 | 0 | 203 | 0 | Correct README font documentation. |
| `13fdf83` | 2026-09-22 | 2935 | 0 | 203 | 0 | Enable -s smart-case matching in the keymap menu. |
| `2c3a4bd` | 2026-09-26 | 2935 | 0 | 231 | +28 | Refresh dwm/st help and bindings; separate Super+B bar toggle; shorten full-width menu; add keymap tests. |
| `8f89445` | 2026-09-27 | 2935 | 0 | 238 | +7 | Use absolute brightness rungs; expand brightness tests and docs. |
| `9aa34ab` | 2026-09-30 | 2935 | 0 | 240 | +2 | Fix smart-case help invocation and bogus menu entries; document copy-mode exit behavior. |
| `22c2661` | 2026-10-02 | 2937 | +2 | 243 | +3 | Add Super+E terminal file manager via dwm-fmgr, packaging and keymap tests. |
| `4443743` | 2026-10-02 | 2937 | 0 | 243 | 0 | Correct Super+E file-manager documentation. |
| `937f79a` | 2026-10-04 | 3022 | +85 | 244 | +1 | Make Super+N tag rename nonblocking with labeled prompt and pipe tests; align brightness tests/docs to current rungs. |
| `WORKTREE` | uncommitted | 3022 | 0 | 244 | 0 | Pending changes vs HEAD: AGENTS.md, README, scripts/cloc-history.json, scripts/test_cloc_history.py, scripts/update_cloc_by_commit.py |

## Supporting code and build files

| Commit | Support C | Δ C | Support scripts | Δ scripts | Build | Δ build | Combined code | Δ combined |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `44dbc68` | 34 | — | 0 | — | 46 | — | 2546 | — |
| `6760c0c` | 34 | 0 | 0 | 0 | 46 | 0 | 2546 | 0 |
| `476bda3` | 34 | 0 | 5 | +5 | 46 | 0 | 2553 | +7 |
| `630a973` | 34 | 0 | 5 | 0 | 46 | 0 | 2571 | +18 |
| `4f0230b` | 34 | 0 | 5 | 0 | 46 | 0 | 2571 | 0 |
| `625ca95` | 34 | 0 | 5 | 0 | 46 | 0 | 2571 | 0 |
| `8bc9886` | 34 | 0 | 5 | 0 | 46 | 0 | 2603 | +32 |
| `fd4af73` | 34 | 0 | 5 | 0 | 46 | 0 | 2671 | +68 |
| `e39092c` | 34 | 0 | 5 | 0 | 46 | 0 | 2671 | 0 |
| `9d2fb98` | 34 | 0 | 5 | 0 | 47 | +1 | 2700 | +29 |
| `c751510` | 34 | 0 | 5 | 0 | 47 | 0 | 2747 | +47 |
| `e27aee9` | 34 | 0 | 5 | 0 | 47 | 0 | 2771 | +24 |
| `409b7b0` | 34 | 0 | 7 | +2 | 47 | 0 | 2805 | +34 |
| `6630daa` | 34 | 0 | 7 | 0 | 47 | 0 | 2813 | +8 |
| `850a415` | 34 | 0 | 7 | 0 | 62 | +15 | 3116 | +303 |
| `6d383a5` | 34 | 0 | 7 | 0 | 62 | 0 | 3120 | +4 |
| `eb26f97` | 34 | 0 | 7 | 0 | 65 | +3 | 3137 | +17 |
| `600ed7c` | 34 | 0 | 7 | 0 | 65 | 0 | 3140 | +3 |
| `d36f9af` | 34 | 0 | 7 | 0 | 68 | +3 | 3216 | +76 |
| `16b3a48` | 34 | 0 | 7 | 0 | 68 | 0 | 3218 | +2 |
| `8756af6` | 34 | 0 | 7 | 0 | 68 | 0 | 3219 | +1 |
| `2dedbe3` | 34 | 0 | 67 | +60 | 71 | +3 | 3301 | +82 |
| `e513956` | 34 | 0 | 67 | 0 | 71 | 0 | 3301 | 0 |
| `12f7473` | 34 | 0 | 67 | 0 | 71 | 0 | 3310 | +9 |
| `8cad9c0` | 34 | 0 | 67 | 0 | 71 | 0 | 3310 | 0 |
| `13fdf83` | 34 | 0 | 67 | 0 | 71 | 0 | 3310 | 0 |
| `2c3a4bd` | 34 | 0 | 125 | +58 | 72 | +1 | 3397 | +87 |
| `8f89445` | 34 | 0 | 146 | +21 | 72 | 0 | 3425 | +28 |
| `9aa34ab` | 34 | 0 | 152 | +6 | 72 | 0 | 3433 | +8 |
| `22c2661` | 34 | 0 | 155 | +3 | 76 | +4 | 3445 | +12 |
| `4443743` | 34 | 0 | 155 | 0 | 76 | 0 | 3445 | 0 |
| `937f79a` | 34 | 0 | 185 | +30 | 77 | +1 | 3562 | +117 |
| `WORKTREE` | 34 | 0 | 185 | 0 | 77 | 0 | 3562 | 0 |

Combined includes all five counted categories; excluded files remain excluded.

## Baseline → committed HEAD totals

| Category | Code baseline → HEAD (net) | Blank baseline → HEAD | Comment baseline → HEAD |
|---|---:|---:|---:|
| C | 2466 → 3022 (+556) | 278 → 313 | 115 → 122 |
| Runtime scripts | 0 → 244 (+244) | 0 → 19 | 0 → 14 |
| Support C | 34 → 34 (0) | 7 → 7 | 1 → 1 |
| Support scripts | 0 → 185 (+185) | 0 → 29 | 0 → 67 |
| Build | 46 → 77 (+31) | 21 → 26 | 17 → 17 |

## Commits integrated by merges

Counts below are each side commit’s snapshot and delta vs its own first parent. These are **not additive** with the main tables.

### Merge `850a415`

| Side commit | C (Δ) | Runtime scripts (Δ) | Support C (Δ) | Support scripts (Δ) | Build (Δ) | Subject |
|---|---:|---:|---:|---:|---:|---|
| `b6df683` | 2912 (+288) | 93 (0) | 34 (0) | 7 (0) | 49 (+2) | add dwm-spawn and swallow |

## Files counted at committed HEAD

- **C:** `config.h`, `drw.c`, `drw.h`, `dwm-spawn.c`, `dwm.c`, `util.c`, `util.h`.
- **Runtime scripts:** `brightness-down`, `brightness-up`, `dwm-fmgr`, `dwm-keymap`, `dwm-screenshot`, `dwm-screenshot-full`, `dwm-st-help`, `dwm-suspend`.
- **Support C:** `transient.c`.
- **Support scripts:** `b`, `tests/helpers.py`, `tests/keymap.py`, `tests/rename.py`.
- **Build:** `Makefile`, `config.mk`.

## Latest change

WORKTREE — Pending changes vs HEAD: AGENTS.md, README, scripts/cloc-history.json, scripts/test_cloc_history.py, scripts/update_cloc_by_commit.py
C: 3022 (0); Runtime scripts: 244 (0); Support C: 34 (0); Support scripts: 185 (0); Build: 77 (0)

Maintenance: regenerate after each modification and again after committing (or switching branches); include the latest code/script totals and net deltas in the change summary. Reporting-only changes legitimately have zero measured delta.
