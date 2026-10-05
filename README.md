# 🛠️ Sims 4 Save Fixer

> A set of small Python scripts for diagnosing and repairing corrupt **The Sims 4** save files, built while using [Claude Code](https://claude.com/claude-code) to rescue a heavily modded save.

If your save shows a warning like **"a career is missing or broken"** on load, the game suddenly runs very slowly, or `lastException.txt` keeps filling with errors from `careers/career_base.py`, this repo (and the approach below) is for you.

---

## 📖 Table of Contents

- [What this does](#-what-this-does)
- [The story: what was actually wrong](#-the-story-what-was-actually-wrong)
- [Fixing your save with Claude Code (recommended)](#-fixing-your-save-with-claude-code-recommended)
- [Running the scripts yourself](#-running-the-scripts-yourself)
- [Script reference](#-script-reference)
- [Troubleshooting](#-troubleshooting)
- [Safety notes](#%EF%B8%8F-safety-notes)

---

## ✨ What this does

A Sims 4 `.save` file is a **DBPF package** (the same container format as mods) holding a compressed **protobuf** blob called `SaveGameData`. That blob holds every sim, household, lot and career. These scripts can:

| | |
|---|---|
| 🔍 **Inspect** | Check the save container is intact, decompress it, and cross-reference sims, households and lots |
| 🧑‍💼 **Audit careers** | List every career and career track each sim holds or has held |
| 📦 **Scan mods & game files** | Index every career/track tuning ID in your `Mods` folder and the game's install, so you can see which careers really exist |
| 🎓 **Find university problems** | Report sims holding Discover University course careers without a valid enrollment |
| ✂️ **Repair** | Remove careers that no longer exist, remove broken university course careers, or remove sim records entirely — always writing a **new** file |

No third-party packages are needed: everything runs on plain Python 3.

---

## 🕵️ The story: what was actually wrong

This is worth reading, because the obvious fix was the wrong one.

**Symptom:** on load the game warned that a career was missing/broken, and afterwards ran very slowly.

**First attempt (wrong):** the save contained four careers with large "custom content" IDs, so the assumption was that a mod had been removed. All four were stripped from every sim. The warning **didn't go away**, and worse, two of those careers came from a mod that **was still installed**, so several sims lost their jobs for nothing.

**What Claude Code found:**

1. **Every career ID in the save was checked against what was actually installed**: all ~4,700 mod packages *and* the game's own packed tuning across every expansion. Only **2** of the 4 "custom" careers were truly missing.
2. **The real crash wasn't a missing career at all.** By decompiling the game's own `career_base.py` and decoding the game's save schema, the errors were traced to **one sim** who held the four *Discover University* course-slot careers (plus the base university career) but had **no university, no major, no courses**, and an enrollment status stuck on *Probation*. When the game loaded that sim it went looking for course data that didn't exist and threw 4 exceptions: exactly matching the log.
3. **The fix** started from the earlier save (before the over-eager career removal) and:
   - removed only the broken university careers from that one sim and reset their enrollment to *None*;
   - removed only the 2 careers that genuinely no longer existed;
   - left every other sim and career untouched.

**Result:** the career error disappeared. One unrelated, harmless error remained (`Attempt to transfer into inventory type with multiple nonshared inventories: InventoryType.MAILBOX`), caused by **two mailboxes on the same lot**. That one is fixed in-game by deleting the extra mailbox in Build mode.

> 💡 **Lesson:** don't trust the warning text on its own. Read `lastException.txt`, find the exact line that crashes, and check every career against what's *actually installed* before deleting anything.

---

## 🤖 Fixing your save with Claude Code (recommended)

Every corrupt save is different. The scripts here contain IDs specific to the save they were written for, so the best way to use this repo is to let **Claude Code** investigate *your* save, using these scripts as a starting point.

### 1. Install Claude Code

You'll need a Claude Pro/Max subscription (or an Anthropic API account).

**Windows** (Command Prompt):

```cmd
curl -fsSL https://claude.ai/install.cmd -o install.cmd && install.cmd && del install.cmd
```

**macOS / Linux:**

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

> ⚠️ **Windows "not in your PATH" note:** if the installer says `C:\Users\<you>\.local\bin is not in your PATH`, either add it via *System Properties → Environment Variables → Edit User PATH → New*, then restart your terminal, **or** just run it directly:
>
> ```cmd
> cd %USERPROFILE%\.local\bin
> claude
> ```
>
> (Note: `cd` into the **folder**, not into `claude.exe` itself.)

You **don't** need Python installed beforehand. If it's missing, Claude can download a portable copy into its own scratch folder without changing your system.

### 2. Close The Sims 4

Make sure the game is fully closed so the save file isn't locked or overwritten.

### 3. Start Claude Code and paste this prompt

Run `claude`, log in when asked, then paste the prompt below. Fill in the parts in `<angle brackets>`:

```text
We are trying to fix a corrupt Sims 4 save. Whenever it loads it says that a career
is missing/broken, and now the game runs very slowly. <Describe anything else you've
noticed or already tried.>

The save is <Slot_xxxxxxxx.save> in:
  <C:\Users\YOU\Documents\Electronic Arts\The Sims 4\saves>

Exception logs (lastException*.txt, Better Exceptions reports) are in:
  <C:\Users\YOU\Documents\Electronic Arts\The Sims 4>

The game is installed at:
  <C:\Program Files\EA Games\The Sims 4>

Some helper scripts and earlier fix attempts are in:
  <path to this repo / your working folder>

Please:
1. BACK UP the save before touching anything.
2. Read the exception logs to find the exact error and code path.
3. Check every career/track in the save against what is actually installed: the base
   game and packs AND my Mods folder. Don't assume a mod career is missing.
4. Look at the game's own code/tuning if needed to understand why it crashes.
5. Make the smallest targeted fix possible, write it to a NEW file, verify it, and
   only then install it in place of the old save.
6. Explain what was wrong, what you changed, and where the backup is.
```

Claude will explore the folders, back up the save, read the logs and work through it. It will ask before doing anything risky. A full investigation took about 10 minutes for us.

### 4. Test it in-game

1. Load the save.
2. If there's no warning and it runs at normal speed, it's fixed. 🎉 Use **Save As** to save into a new slot.
3. If you get a **different** error, go back to Claude with a follow-up like:

```text
Now I'm getting a different error. Can you read the newest lastException file in
<C:\Users\YOU\Documents\Electronic Arts\The Sims 4> and tell me what it means and
how to fix it?
```

### Tips for a good session

- ✅ **Give it every path up front**: the save, the logs, the game install, the Mods folder, and any earlier fix attempts.
- ✅ **Mention what you already tried.** In our case Claude found that an earlier attempt had removed careers that still existed.
- ✅ **Ask it to verify before installing.** It can run an integrity check (`dbpf_check.py`) on the new file.
- ❌ Claude **can't click through the game's menus** to load a save, so the final in-game test is up to you.

---

## 🐍 Running the scripts yourself

Requires **Python 3.8+** (no extra packages). Run everything from this repo's folder, since the scripts import each other.

```bash
# 1. Sanity-check the save container (and optionally extract its resources)
python dbpf_check.py Slot_xxxxxxxx.save

# 2. Cross-reference sims / households / lots for dangling references
python save_xref.py Slot_xxxxxxxx.save

# 3. List every career in the save (high IDs = mod careers)
python careers.py Slot_xxxxxxxx.save

# 4. Build an index of every career/track that actually exists
#    (edit the two paths at the top of scan_tuning.py first)
python scan_tuning.py            # writes tuning_index.json

# 5. Show which careers in the save are NOT FOUND anywhere
python check_careers.py Slot_xxxxxxxx.save

# 6. Look for broken university enrollment
python uni_report.py Slot_xxxxxxxx.save
```

Then repair, always into a **new** file:

```bash
# Remove specific careers (decimal IDs from careers.py / check_careers.py)
python remove_careers.py IN.save OUT.save 1234567890123456789

# Remove specific sims (hex sim IDs); refuses if the sim is still referenced
python remove_sim.py IN.save OUT.save 0123456789abcdef

# Or the combined targeted fix (edit MISSING_CAREERS at the top first!)
python fix_save.py IN.save OUT.save

# Verify the result
python dbpf_check.py OUT.save
```

Copy `OUT.save` over your original save **only** after backing it up and closing the game.

---

## 📚 Script reference

| Script | Purpose |
|---|---|
| `dbpf_check.py` | Integrity checker for DBPF `.save`/`.package` files: header, index, decompression (zlib and RefPack), protobuf sanity. `--extract DIR` dumps resources. |
| `pb_explore.py` | Schema-less protobuf parser plus `load_savegame()`. The shared foundation for the other scripts. |
| `save_xref.py` | Cross-references sims ↔ households ↔ lots ↔ neighborhoods and reports dangling IDs. |
| `careers.py` | Lists every career (current and history) referenced by sims, flagging custom/mod careers. |
| `scan_mods.py` | Searches a `Mods` folder for specific career/track tuning IDs. |
| `scan_tuning.py` | Indexes career, track and level tuning in the game's `Simulation*.package` files and your Mods into `tuning_index.json`. |
| `check_careers.py` | Labels each career in the save as `EA`, `MOD/pkg:<file>` or `*** NOT FOUND ***`. Uses `tuning_index.json` and, optionally, `ea_ids.json`. |
| `uni_report.py` | Reports sims with Discover University careers versus their actual degree-tracker enrollment. |
| `remove_careers.py` | Strips given career IDs (current and history) from every sim. |
| `remove_sim.py` | Removes sim records safely, refusing if they're still referenced elsewhere. |
| `fix_save.py` | The targeted fix: removes missing careers and broken university course careers, and resets enrollment. |

> ⚠️ `fix_save.py`, `scan_mods.py` and `scan_tuning.py` contain **IDs and paths specific to the save they were written for**. Update the constants at the top of each file for your own save, or let Claude do it.

> ℹ️ EA's own careers live in packed "combined tuning" blobs rather than individual resources, so `scan_tuning.py` alone won't find most base-game careers. Treat small numeric IDs reported as `NOT FOUND` with suspicion until they're checked against the combined tuning (Claude Code can do this).

---

## 🧯 Troubleshooting

| Error / symptom | Likely cause | Fix |
|---|---|---|
| "Career missing/broken" warning; `career_base.py` errors mentioning `degree_tracker`, `get_course_data` or `get_university` | A sim holds university course careers without a valid enrollment | `uni_report.py` → `fix_save.py` |
| Career warning; careers show `*** NOT FOUND ***` | A career mod was removed or updated | Reinstall the mod, or `remove_careers.py` for only the truly missing IDs |
| `Attempt to transfer into inventory type with multiple nonshared inventories: InventoryType.MAILBOX` | Two or more mailboxes on one lot (custom-content postboxes count) | In Build/Buy mode, search "mail" and delete all but one |
| Game still slow after errors are gone | Large Mods folder or heavy script mods | Try loading with mods disabled, or use the 50/50 method |
| `Python was not found` (Windows) | Only the Microsoft Store alias exists | Install Python, or let Claude use a portable copy |

---

## ⚠️ Safety notes

- 🔒 **Always back up** your `saves` folder before making changes.
- 🎮 **Close the game** before replacing a save file.
- 📝 Every script writes a **new** file. Your original is never modified in place.
- 🧪 Test the repaired save in-game, then use **Save As** to a new slot once it loads cleanly.
- This is an unofficial community tool and isn't affiliated with Electronic Arts or Maxis.
