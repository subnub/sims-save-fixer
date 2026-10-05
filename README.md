# 🛠️ Sims 4 Save Fixer

> Fix a corrupt **The Sims 4** save with [Claude Code](https://claude.com/claude-code). Download this folder, point Claude at it, paste one prompt, and let it do the investigating.

Use this if your save:

- shows an error or warning when it loads (for example **"a career is missing or broken"**)
- won't load, or loads into a broken household or lot
- suddenly runs **very slowly**
- keeps filling `lastException.txt` with errors

It was first built to fix a broken-career save, but the approach works for any save problem: Claude reads *your* error logs, works out what's actually wrong, and makes a targeted fix.

---

## 🚀 Quick Start

### 1. Download this repo

Click **Code → Download ZIP** on GitHub and unzip it somewhere easy to find, for example `C:\Users\YOU\Downloads\sims-save-fixer`.

### 2. Install Claude Code

You'll need a Claude Pro/Max subscription (or an Anthropic API account).

**Windows** (Command Prompt):

```cmd
curl -fsSL https://claude.ai/install.cmd -o install.cmd && install.cmd && del install.cmd
```

**macOS / Linux:**

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

> ⚠️ **Windows "not in your PATH" note:** if the installer says `C:\Users\<you>\.local\bin is not in your PATH`, either add it via *System Properties → Environment Variables → Edit User PATH → New*, then restart your terminal, **or** run it directly:
>
> ```cmd
> cd %USERPROFILE%\.local\bin
> claude
> ```

You **don't** need Python installed. If it's missing, Claude can download a portable copy without changing your system.

### 3. Close The Sims 4

Make sure the game is fully closed so the save file isn't locked or overwritten.

### 4. Start Claude and paste the prompt

Run `claude`, log in when asked, then copy the prompt below. Replace the parts in `<angle brackets>` with your own paths and slot name:

```text
I have a corrupt Sims 4 save. <Describe what happens, e.g. "when it loads it says
a career is missing/broken and the game runs very slowly".>

- Save file:      <C:\Users\YOU\Documents\Electronic Arts\The Sims 4\saves\Slot_xxxxxxxx.save>
- Error logs:     <C:\Users\YOU\Documents\Electronic Arts\The Sims 4>  (lastException*.txt)
- Mods folder:    <C:\Users\YOU\Documents\Electronic Arts\The Sims 4\Mods>
- Game install:   <C:\Program Files\EA Games\The Sims 4>
- Helper scripts: <C:\Users\YOU\Downloads\sims-save-fixer>  (read the README there)

Please:
1. BACK UP the save before touching anything.
2. Read the newest exception logs to find the exact error and code path.
3. Use the helper scripts (and write new ones if needed) to check whatever the
   error points at (sims, households, lots, careers, objects, etc.) against what
   is actually installed: the base game, packs AND my Mods folder. Don't assume
   something is missing without checking.
4. Look at the game's own code/tuning if needed to understand why it crashes.
5. Make the smallest targeted fix possible, write it to a NEW file, verify it with
   dbpf_check.py, and only then install it in place of the old save.
6. Tell me what was wrong, what you changed, and where the backup is.
```

Claude will explore the folders, back up your save, read the logs and work through the problem. It asks before doing anything risky, and a full run usually takes around 10 minutes.

### 5. Test it in-game

1. Load the save.
2. If there's no warning and it runs at normal speed, you're done. 🎉 Use **Save As** to save into a new slot.
3. If you get a **different** error, send Claude this follow-up:

```text
Now I'm getting a different error. Can you read the newest lastException file in
<C:\Users\YOU\Documents\Electronic Arts\The Sims 4> and tell me what it means and
how to fix it?
```

> ℹ️ Claude can't click through the game's menus, so the final in-game test is up to you.

---

## 📚 What's in this repo

All scripts are plain Python 3 with no extra packages. Claude uses them as a starting point, adapts them to your save, and writes new ones when your problem needs something different. The container, cross-reference and sim-removal scripts work on any save; the career scripts cover the most common kind of breakage. Every repair script writes a **new** file and never changes your original.

| Script | Purpose |
|---|---|
| `dbpf_check.py` | Checks that a `.save` file is intact and can be decompressed |
| `pb_explore.py` | Reads the save's internal data (used by the other scripts) |
| `save_xref.py` | Finds sims, households or lots that point at things that don't exist |
| `careers.py` | Lists every career each sim holds or has held |
| `scan_tuning.py` / `scan_mods.py` | Index the careers that actually exist in your game and Mods folder |
| `check_careers.py` | Labels each career in the save as `EA`, `MOD` or `NOT FOUND` |
| `uni_report.py` | Finds sims with university courses but no valid enrollment |
| `remove_careers.py` | Removes specific careers from every sim |
| `remove_sim.py` | Removes specific sims, refusing if they're still referenced elsewhere |
| `fix_save.py` | Targeted repair for missing careers and broken university enrollment |

> ⚠️ Some scripts have IDs and paths hard-coded at the top. Claude will update these for your save.

---

## 🧯 Common errors

| Error / symptom | Likely cause | Fix |
|---|---|---|
| Any other error in `lastException.txt` | Varies | Paste the prompt above with your symptoms; Claude will trace it from the log |
| Career warning; `career_base.py` errors mentioning `degree_tracker`, `get_course_data` or `get_university` | A sim holds university course careers without a valid enrollment | Paste the prompt above; Claude will use `uni_report.py` and `fix_save.py` |
| Career warning; careers show as `NOT FOUND` | A career mod was removed or updated | Reinstall the mod, or let Claude remove only the truly missing careers |
| `Attempt to transfer into inventory type with multiple nonshared inventories: InventoryType.MAILBOX` | Two or more mailboxes on one lot (custom-content postboxes count) | In Build/Buy mode, search "mail" and delete all but one |
| Game still slow after errors are gone | Large Mods folder or heavy script mods | Try loading with mods disabled, or use the 50/50 method |

---

## ⚠️ Safety notes

- 🔒 **Back up** your `saves` folder before making changes. The prompt tells Claude to do this too.
- 🎮 **Close the game** before replacing a save file.
- 🧪 Test the repaired save in-game, then use **Save As** to a new slot once it loads cleanly.
- This is an unofficial community tool and isn't affiliated with Electronic Arts or Maxis.
