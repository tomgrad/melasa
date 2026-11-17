# Style library Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Separate melasa's structural CSS from personal looks, and let `melasa init --style NAME` spin up a deck from a packaged style library.

**Architecture:** `stage()` layers reveal theme (from deck/base `mkslides.yml`), packaged `melasa.css` (structural), deck `style.css` (overrides only). Styles live in `src/melasa/data/styles/<name>/{style.css,mkslides.yml}` and are copied by `init`. Deck-local `custom.css` and `preprocessor.py` support is removed.

**Tech Stack:** Python 3.12, click, omegaconf, mkslides, hatchling, pytest.

**Spec:** `docs/superpowers/specs/2026-11-17-style-library-design.md`

## Global Constraints

- Theme named only in `mkslides.yml` (`slides.theme`); never `@import`ed inside a style's `style.css`.
- `melasa.css`: structural rules only (`.cols*`, `.cols-top-align`, `.cols-bottom-align`, `.box`, `.footnote`, `.tight`); no fonts, no heading/code/table styling.
- Layer order: reveal theme, `melasa.css`, deck `style.css` (last).
- Shared `preprocessor.py` always used; no deck-local lookup.
- Initial styles: `default` (comment-only `style.css`, theme `beige`) and `garamond` (current look, theme `beige`).
- `init` refuses to overwrite existing files; default style `default`.
- Run tests with `uv run --with pytest python -m pytest -q` (`uv run pytest` fails in this repo).
- `slides/` and `site/` are gitignored test material: do not touch.

## Review Focus

- `init --style nope` exits non-zero, lists valid style names, writes nothing.
- `init --list` output is sorted and writes nothing.
- A deck still containing a legacy `custom.css` / `preprocessor.py` builds using the shared ones (files ignored, no error).
- Deck `mkslides.yml` `theme:` overrides the base theme; a URL theme still produces an `@import`.
- Built wheel contains `melasa/data/styles/*/style.css` and `melasa/data/melasa.css`.

---

### Task 1: Structural theme and layering

**Files:**
- Create: `src/melasa/data/melasa.css`
- Modify: `src/melasa/cli.py` (`BASE_THEME_NAME`, `stage`, `base_theme_import`)
- Delete: `src/melasa/data/custom.css` (its look moves to Task 2)
- Modify: `tests/test_cli.py`

**Interfaces:**
- Produces: `BASE_THEME_NAME = "melasa.css"`; `stage(deck: Path, stage_dir: Path) -> Staged` unchanged signature, `Staged.base_theme` is the staged copy of `melasa.css`.

- [ ] **Step 1: Update tests.** In `tests/test_cli.py`: replace every `'@import url("melasa-base.css");'` with `'@import url("melasa.css");'`; delete `test_stage_deck_custom_css_replaces_global_theme`; add `test_stage_ignores_legacy_local_overrides` (deck with `custom.css` = `.x{}` and `preprocessor.py` = `raise SystemExit`; assert `staged.base_theme.read_text()` equals the packaged `melasa.css` text and `OmegaConf.load(staged.config).slides.preprocess_script` ends with `preprocessor.py` and does not start with `str(deck)`); add `test_melasa_css_is_structural_only` asserting the packaged text contains `.cols21` and `.box` and does not contain `font-family` or `darkorange`.
- [ ] **Step 2: Run tests, expect FAIL** (`melasa.css` missing, import name mismatch).
- [ ] **Step 3: Create `data/melasa.css`** by moving the `.box`, `.tight`, `.cols*`, `.cols-top-align`, `.cols-bottom-align`, `.footnote` rules from `data/custom.css` verbatim (drop the `.footnote` colour/size only if you judge them visual; default: keep, per spec). Delete `data/custom.css`.
- [ ] **Step 4: Edit `cli.py`.** Set `BASE_THEME_NAME = "melasa.css"`. In `stage`, drop the `local_theme` and `local_pre` branches: always write `DATA/"melasa.css"` to `stage_dir/BASE_THEME_NAME` and `DATA/"preprocessor.py"` to `stage_dir/"preprocessor.py"`. In `base_theme_import`, drop the `"custom.css"` special case (keep `THEME_NAME`). Update the `stage` docstring.
- [ ] **Step 5: Run tests, expect PASS** (the `test_build_*` test exercises a real build).
- [ ] **Step 6: Commit** `refactor: split structural css, drop deck-local theme/preprocessor overrides`.

### Task 2: Style library and `init`

**Files:**
- Create: `src/melasa/data/styles/default/{style.css,mkslides.yml}`, `src/melasa/data/styles/garamond/{style.css,mkslides.yml}`, `src/melasa/data/starter_index.md`
- Modify: `src/melasa/cli.py` (`init`, remove `STARTER_STYLE`/`STARTER_CONFIG`/`STARTER_FILES`)
- Modify: `tests/test_cli.py`

**Interfaces:**
- Produces: `list_styles() -> list[str]` (sorted directory names under `DATA/"styles"`); `init` options `--style TEXT` (default `"default"`) and `--list` (flag, prints one name per line, exits 0).

- [ ] **Step 1: Write failing tests.**
  - `test_init_default_style` (adapt existing `test_init_creates_starter_files`: still asserts the same three files, `style.css` starts with `/*` and contains "override", config contains `theme: beige` and `league`).
  - `test_init_garamond_copies_style`: `init --style garamond` → `style.css` contains `EB Garamond` and does not contain `reveal-js/dist/theme`; `mkslides.yml` contains `theme: beige`.
  - `test_init_unknown_style`: exit code != 0, output contains `default` and `garamond`, no files written.
  - `test_init_list`: output lines `== ["default", "garamond"]`, no files written.
  - `test_starter_index_demos_tags`: `index.md` contains `<!-- c21 -->`, `<!-- box -->`, `<!-- footnote -->`.
  - Keep the two "refuses to overwrite" tests unchanged.
- [ ] **Step 2: Run tests, expect FAIL.**
- [ ] **Step 3: Create style files.** `default/style.css`: a single `/* Per-deck overrides, loaded after the reveal.js theme and melasa.css. */` comment. `default/mkslides.yml` and `garamond/mkslides.yml`: the current `STARTER_CONFIG` text (comment listing themes + `slides:\n    theme: beige`). `garamond/style.css`: everything remaining in the old `custom.css` (font `@import`, `.reveal` font/size, headings, `h1`–`h4` sizes, `table`, `code`, `span.katex`) with the old `.footnote` colour left in `melasa.css`. Recover the old content from `git show HEAD:src/melasa/data/custom.css` (the file is tracked at HEAD).
- [ ] **Step 4: Create `data/starter_index.md`**: title slide plus one slide per tag family (columns incl. ratios/alignment, box, footnote), each showing the real syntax; read `data/preprocessor.py` for the exact tag set.
- [ ] **Step 5: Implement in `cli.py`:** `list_styles()`; `init(style: str, list_styles_flag: bool)` — `--list` prints and returns; unknown style raises `click.ClickException` naming valid styles; copies `index.md` from `starter_index.md`, `style.css` and `mkslides.yml` from the style dir; overwrite check covers the same three target names, before writing anything. Update the `init` docstring/echo.
- [ ] **Step 6: Run tests, expect PASS.**
- [ ] **Step 7: Commit** `feat: style library and init --style/--list`.

### Task 3: Packaging, docs, cleanup

**Files:**
- Modify: `README.md`, `pyproject.toml` (only if the wheel check fails)

- [ ] **Step 1: Verify wheel contents.** Run `uv build --wheel -o /tmp/claude-1000/melasa-wheel` then `unzip -l` on it. Expected: lists `melasa/data/melasa.css`, `melasa/data/starter_index.md`, `melasa/data/styles/default/style.css`, `melasa/data/styles/garamond/style.css`, both style `mkslides.yml`, `melasa/data/preprocessor.py`. If any is missing, add the hatch include needed and rebuild.
- [ ] **Step 2: Update `README.md`.** Replace the paragraph about overriding `custom.css`/`preprocessor.py` and the CSS-layer list (lines ~29–42) with: theme via `mkslides.yml`; layers (reveal theme, `melasa.css`, `style.css`); `init [--style NAME] [--list]`; library location and how to add a style (a dir with `style.css` + `mkslides.yml`). Rename the title/intro from "mkslides-theme" to melasa.
- [ ] **Step 2b: Check `omegaconf`.** Add `"omegaconf"` to `dependencies` in `pyproject.toml` (it is imported directly in `cli.py`); run `uv lock`.
- [ ] **Step 3: Full test run** `uv run --with pytest python -m pytest -q`; expect all pass. Then `uv run melasa build slides/test -d /tmp/claude-1000/melasa-site` exits 0.
- [ ] **Step 4: Commit** `docs: document style library; declare omegaconf dependency`.
