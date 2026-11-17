# melasa: structural theme and style library

## Intent

melasa extends mkslides with preprocessor tags for columns and blocks
(`<!-- c21 -->`, `<!-- box -->`, ...) plus the CSS those tags need. Today the
structural CSS and the author's personal look are mixed in one file
(`data/custom.css`), and a deck-local `custom.css` or `preprocessor.py`
replaces the shared one wholesale, so decks fork and drift.

Goal: separate the three concerns and make personal looks reusable through
`melasa init`.

## Goals

- reveal.js theme is named only in the deck's `mkslides.yml` (`slides.theme`).
- Structural CSS for the tags ships with melasa and is the same for every deck.
- A deck's `style.css` holds overrides only and is the single place to customize.
- A library of named styles ships in the package; `melasa init` spins one up.

## Non-goals

- No style inheritance or composition.
- No updating a deck from the library after `init` (the copy is the deck's own).
- No deck-local `preprocessor.py` and no deck-local replacement of the
  structural CSS. Those in `slides/` are leftovers of the previous tool version
  and are ignored after this change.

## Anti-goals

- A deck whose look can only be changed by forking shared files.
- A theme name that appears in two places (yml and CSS).

## Design

### Layers (CSS load order)

1. reveal.js theme from `slides.theme` in `mkslides.yml`, imported by melasa
   (existing `base_theme_import` behaviour).
2. `melasa.css`: structural CSS only (`.cols*`, `.cols-top-align`,
   `.cols-bottom-align`, `.box`, `.footnote`, `.tight`). No fonts, colours or
   font sizes beyond what layout requires. Shipped at `src/melasa/data/melasa.css`.
3. Deck `style.css`, if present, loaded last so it wins.

The shared `preprocessor.py` is always used; the deck-local lookup is removed.
The deck-local `custom.css` lookup and `BASE_THEME_NAME` replacement logic are
removed; `custom.css` as a theme name is no longer special-cased.

### Library

`src/melasa/data/styles/<name>/` with two files:

- `style.css`: overrides only. Font `@import`s belong here. No reveal theme import.
- `mkslides.yml`: fragment, e.g. `slides:\n    theme: beige`.

Initial styles:

- `default`: empty `style.css` (comment only), theme `beige`.
- `garamond`: the current look from `data/custom.css` minus the structural
  rules (EB Garamond / Raleway / Source Code Pro, orange headings with
  text-shadow, `.reveal` 3em, table/code sizes, katex), theme `beige`.

### `melasa init [--style NAME] [--list]`

- Writes `index.md`, `style.css`, `mkslides.yml` into the current directory.
  `style.css` and `mkslides.yml` come from the chosen style; default style is
  `default`.
- `index.md` is a starter deck that demonstrates each tag.
- `--list` prints available style names and exits.
- Unknown style: error listing valid names.
- Still refuses to overwrite existing files.

### Build / serve

`stage()` merges the packaged base `mkslides.yml` with the deck's, writes the
theme CSS as imports of (reveal theme, `melasa.css`, `style.css` if present),
and copies the staged CSS into the output dir after each build (existing
`patch_build` mechanism). Base `mkslides.yml` in `data/` keeps the shared
separators, revealjs options and `preprocess_script`; it no longer needs a
default theme beyond a fallback.

## Approaches considered

- A. Self-contained single-CSS style that `@import`s its own reveal theme.
  Rejected: theme named in CSS, not yml.
- B. CSS plus yml fragment per style, theme in yml (chosen). Matches "theme
  referenced by name in yml, only overrides in style.css".
- C. Reference style by name at build time, no copy. Rejected: look lives
  outside the project and changes under the deck.

## Left to the builder

- Exact split of rules between `melasa.css` and `garamond/style.css`
  (guideline: layout needed by a tag is structural; anything visual is style).
- Tag demo content of the starter `index.md`.
- Updating `README.md`, tests in `tests/test_cli.py` (init styles, `--list`,
  layering, removal of local-override behaviour), and removing now-dead code.
- Packaging: confirm `data/styles/**` is included in the wheel.
