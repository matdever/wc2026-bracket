# 2026 FIFA World Cup — Bracket Predictor & Pool

An interactive, single-file predictor for the 2026 FIFA World Cup (48 teams, 104 matches,
all kick-off times in **Halifax time / ADT**). Enter scores, the group standings re-sort with
FIFA tiebreakers, the "best third-placed teams" are worked out automatically, and the knockout
bracket fills itself all the way to the Final. Includes per-player **profiles**, a per-match 🎲,
and a configurable **scoring leaderboard** for running a pool.

**Live site:** https://matdever.github.io/wc2026-bracket/

---

## How the pool works

Everything runs in the browser — there is no server. The shared pool is just a file,
**`pool.json`**, that lives next to `index.html` in this repo. When the page loads it reads
`pool.json` and shows everyone's predictions on the 🏆 **Leaderboard** tab.

### If you're a participant (a friend)
1. Open the live site.
2. In the **👤 Profiles** bar, make a profile (or rename "Player 1" to your name).
3. Fill in your predictions — group scores, knockout bracket. (In a hurry? Use the per-match 🎲
   or **🎲 Random all**.)
4. Click **⬇ Export** to download your `.json` file.
5. **Send that file to the host.**

### If you're the host (the commissioner)
You keep the master copy in *your* browser and publish snapshots to this repo.

1. For each friend's file: click **⬆ Import** — they appear as a profile. (Do this once per
   person; they're saved in your browser.)
2. Make one profile called **Actual results** and click the **☆** star on its chip to mark it
   **⭐ official results**. Fill it in as real matches are played.
3. Open the **🏆 Leaderboard** tab → click **📤 Publish pool** → it downloads `pool.json`.
4. Replace `pool.json` in this repo with that file and commit/push (see below). The live site
   updates in ~1 minute, and everyone sees the new standings.

Repeat steps 2–4 whenever new real results come in.

### Updating `pool.json` on GitHub
- Easiest: on github.com open `pool.json` → ✏️ edit (or **Add file → Upload files**) → paste/drop
  the freshly published file → **Commit changes**.
- Or from your machine:
  ```bash
  # put the downloaded pool.json into your local clone, then:
  git add pool.json
  git commit -m "Update pool results"
  git push
  ```

---

## Scoring (all values editable in the ⚙ panel on the Leaderboard tab)

| Category | Rule | Default |
|---|---|---|
| Group standings | correct qualifier / exact position / advancing 3rd-place | 1 / 1 / 2 |
| Group scorelines | exact score / correct result (W-D-L) | 3 / 1 |
| Knockout (per team reaching the round) | R16 / QF / SF / Final / Champion | 2 / 4 / 8 / 16 / 32 |
| Bonus | both finalists / 3rd-place game | 5 / 3 |

The point values you set travel inside `pool.json`, so everyone sees the same scoring.

---

## Good to know
- **It's public.** Anyone with the link can see all predictions and names. Commit everyone's
  picks **after the deadline** so no one peeks early.
- **Predictions auto-lock at kick-off.** When the first match starts (Thu Jun 11, 2026,
  4:00 PM ADT), the app turns every bracket read-only and makes all picks public to view
  (open a name under **🔓 Everyone's picks**). Your **⭐ official-results** profile stays
  editable so you can keep scoring. It's a client-side lock — the picks that truly count are
  whatever you've committed to `pool.json`, so still commit everyone's entries before kick-off.
- **Saving:** each browser keeps its own profiles in local storage. The shared standings come
  from `pool.json`.
- The page reads `pool.json` only when **hosted** (opening the raw file from disk can't fetch it).

---

*Schedule, groups, and the official 495-row "best third-placed teams" Round-of-32 allocation
table are from the public FIFA / Wikipedia data. Kick-off times are accurate as published and
may be adjusted by FIFA.*
