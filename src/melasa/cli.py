"""melasa: run mkslides on a slides directory using a shared theme and preprocessor."""

import os
import shutil
import tempfile
from importlib import resources
from pathlib import Path
from typing import NamedTuple

import click
from omegaconf import OmegaConf

from melasa.optimize import DEFAULT_MAX_SIZE, DEFAULT_QUALITY, optimize_site

THEME_NAME = "melasa-theme.css"
BASE_THEME_NAME = "melasa-base.css"
STYLE_NAME = "style.css"
DATA = resources.files("melasa") / "data"

STARTER_INDEX = """# Title

---

## Slide
"""

STARTER_STYLE = """/* Per-deck overrides, loaded after the selected reveal.js theme and melasa's shared theme. */
"""

STARTER_CONFIG = """slides:
    # Pick any reveal.js theme: beige, black, league, sky, night, serif,
    # simple, solarized, moon, dracula, ...
    theme: beige
"""

STARTER_FILES = {
    "index.md": STARTER_INDEX,
    "style.css": STARTER_STYLE,
    "mkslides.yml": STARTER_CONFIG,
}


def deck_dir(path: Path) -> Path:
    return path if path.is_dir() else path.parent


class Staged(NamedTuple):
    config: Path
    theme: Path
    base_theme: Path
    style: Path | None


def base_theme_import(theme: str | None) -> str | None:
    """Turn the reveal.js theme selected in the config into a CSS import."""
    if not theme or theme in (THEME_NAME, "custom.css"):
        return None

    from mkslides.constants import OUTPUT_ASSETS_DIRNAME, REVEALJS_THEMES_LIST

    if theme in REVEALJS_THEMES_LIST:
        theme = f"{OUTPUT_ASSETS_DIRNAME}/reveal-js/dist/theme/{theme}.css"
    return f'@import url("{theme}");'


def stage(deck: Path, stage_dir: Path) -> Staged:
    """Create the config and CSS layers in stage_dir.

    A deck-local custom.css replaces the shared theme, while style.css is layered
    on top of the active theme and only overrides what it declares.
    """
    config = OmegaConf.create(DATA.joinpath("mkslides.yml").read_text())
    local_config = deck / "mkslides.yml"
    if local_config.is_file():
        config = OmegaConf.merge(config, OmegaConf.load(local_config))

    local_theme = deck / "custom.css"
    base_theme = stage_dir / BASE_THEME_NAME
    if local_theme.is_file():
        shutil.copy(local_theme, base_theme)
    else:
        base_theme.write_text(DATA.joinpath("custom.css").read_text())

    style = deck / STYLE_NAME
    if not style.is_file():
        style = None

    imports = [base_theme_import(config.slides.theme), f'@import url("{BASE_THEME_NAME}");']
    if style:
        imports.append(f'@import url("{STYLE_NAME}");')

    theme = stage_dir / THEME_NAME
    theme.write_text("\n".join(line for line in imports if line) + "\n")

    local_pre = deck / "preprocessor.py"
    if local_pre.is_file():
        pre = local_pre.resolve()
    else:
        pre = stage_dir / "preprocessor.py"
        pre.write_text(DATA.joinpath("preprocessor.py").read_text())

    config.slides.theme = THEME_NAME
    config.slides.preprocess_script = str(pre)

    config_file = stage_dir / "mkslides.yml"
    OmegaConf.save(config, config_file)
    return Staged(config_file, theme, base_theme, style)


def patch_build(staged: Staged) -> None:
    """mkslides expects the CSS inside the output dir; copy it after every build."""
    import mkslides.__main__ as main
    import mkslides.serve as serve

    original = main.build

    def build(config, input_path, output_path, strict):
        original(config, input_path, output_path, strict)
        output = Path(output_path)
        for asset in (staged.theme, staged.base_theme):
            shutil.copy(asset, output / asset.name)
        if staged.style:
            shutil.copy(staged.style, output / staged.style.name)

    main.build = build
    serve.build = build


path_arg = click.argument(
    "path",
    type=click.Path(exists=True, resolve_path=True, path_type=Path),
    default=".",
)


@click.group()
def main() -> None:
    """Build and serve slides with the shared melasa theme.

    Image optimization (resize, PNG/JPEG to WebP) is off by default: use
    `build --optimize`, or `optimize SITE_DIR` on an existing site.
    Sources are never modified, only the built site.
    """


@main.command()
def init() -> None:
    """Create a starter presentation (index.md, style.css, mkslides.yml)."""
    existing = [name for name in STARTER_FILES if (Path.cwd() / name).exists()]
    if existing:
        verb = "exists" if len(existing) == 1 else "exist"
        raise click.ClickException(
            f"{', '.join(existing)} already {verb}; refusing to overwrite"
        )

    for name, content in STARTER_FILES.items():
        path = Path.cwd() / name
        path.write_text(content)
        click.echo(f"Created {path}")
    click.echo("Run `melasa serve` to preview.")


@main.command()
@path_arg
@click.option("-d", "--site-dir", type=click.Path(path_type=Path), help="Output directory (default: site-<dirname> in the current directory).")
@click.option("--optimize", is_flag=True, help="Optimize images in the built site (off by default).")
@click.option("--max-size", type=click.IntRange(min=1), default=DEFAULT_MAX_SIZE, show_default=True, help="Max image dimension in pixels (with --optimize).")
@click.option("--quality", type=click.IntRange(1, 100), default=DEFAULT_QUALITY, show_default=True, help="WebP quality 1-100 (with --optimize).")
@click.option("-s", "--strict", is_flag=True, help="Fail on unresolved relative links.")
def build(path: Path, site_dir: Path | None, optimize: bool, max_size: int, quality: int, strict: bool) -> None:
    """Build the slides in PATH (default: .) into a static site.

    With --optimize, images in the built site are scaled down to --max-size
    and converted to WebP at --quality (kept only if smaller).
    """
    deck = deck_dir(path)
    site = (site_dir or Path.cwd() / f"site-{deck.name}").resolve()
    args = ["build", "-d", str(site), *(["-s"] if strict else []), str(path)]
    run_mkslides(args, deck)
    click.echo(f"Built {site}")
    if optimize:
        optimize_site(site, max_size, quality)


@main.command()
@path_arg
@click.option("-a", "--dev-addr", default="localhost:8000", show_default=True)
@click.option("-o", "--open", "open_browser", is_flag=True)
@click.option("-s", "--strict", is_flag=True, help="Fail on unresolved relative links.")
def serve(path: Path, dev_addr: str, open_browser: bool, strict: bool) -> None:
    """Serve the slides in PATH (default: .) with live reload."""
    deck = deck_dir(path)
    args = ["serve", "-a", dev_addr, *(["-o"] if open_browser else []), *(["-s"] if strict else []), str(path)]
    run_mkslides(args, deck)


def run_mkslides(args: list[str], deck: Path) -> None:
    from mkslides.__main__ import cli

    previous_dir = Path.cwd()
    with tempfile.TemporaryDirectory(prefix="melasa_") as tmp:
        staged = stage(deck, Path(tmp))
        patch_build(staged)
        os.chdir(tmp)
        try:
            cli([args[0], "-f", str(staged.config), *args[1:]], standalone_mode=False)
        finally:
            os.chdir(previous_dir)


@main.command()
@click.argument("site", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--max-size", type=click.IntRange(min=1), default=DEFAULT_MAX_SIZE, show_default=True, help="Max image dimension in pixels.")
@click.option("--quality", type=click.IntRange(1, 100), default=DEFAULT_QUALITY, show_default=True, help="WebP quality 1-100.")
def optimize(site: Path, max_size: int, quality: int) -> None:
    """Optimize images of an already built SITE directory.

    Scales images down to --max-size and converts PNG/JPEG to WebP at
    --quality (kept only if smaller); references are updated.
    """
    optimize_site(site.resolve(), max_size, quality)
