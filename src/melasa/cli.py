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
BASE_THEME_NAME = "melasa.css"
STYLE_NAME = "style.css"
DATA = resources.files("melasa") / "data"

STARTER_FILES = ("index.md", "style.css", "mkslides.yml")
DEFAULT_STYLE = "default"


def list_styles() -> list[str]:
    """Names of the styles shipped in data/styles, sorted."""
    return sorted(p.name for p in (DATA / "styles").iterdir() if p.is_dir())


def deck_dir(path: Path) -> Path:
    return path if path.is_dir() else path.parent


class Staged(NamedTuple):
    config: Path
    theme: Path
    base_theme: Path
    style: Path | None


def base_theme_import(theme: str | None) -> str | None:
    """Turn the reveal.js theme selected in the config into a CSS import."""
    if not theme or theme == THEME_NAME:
        return None

    from mkslides.constants import OUTPUT_ASSETS_DIRNAME, REVEALJS_THEMES_LIST

    if theme in REVEALJS_THEMES_LIST:
        theme = f"{OUTPUT_ASSETS_DIRNAME}/reveal-js/dist/theme/{theme}.css"
    elif not theme.startswith(("http://", "https://")):
        raise click.ClickException(
            f"unknown reveal.js theme {theme!r}; use a built-in name or an http(s) URL "
            "(put local overrides in style.css)"
        )
    return f'@import url("{theme}");'


def stage(deck: Path, stage_dir: Path) -> Staged:
    """Create the config and CSS layers in stage_dir.

    Layers, later wins: reveal.js theme, melasa.css (structural), deck style.css.
    """
    config = OmegaConf.create(DATA.joinpath("mkslides.yml").read_text())
    local_config = deck / "mkslides.yml"
    if local_config.is_file():
        config = OmegaConf.merge(config, OmegaConf.load(local_config))

    base_theme = stage_dir / BASE_THEME_NAME
    base_theme.write_text(DATA.joinpath("melasa.css").read_text())

    style = deck / STYLE_NAME
    if not style.is_file():
        style = None

    imports = [base_theme_import(config.slides.theme), f'@import url("{BASE_THEME_NAME}");']
    if style:
        imports.append(f'@import url("{STYLE_NAME}");')

    theme = stage_dir / THEME_NAME
    theme.write_text("\n".join(line for line in imports if line) + "\n")

    pre = stage_dir / "preprocessor.py"
    pre.write_text(DATA.joinpath("preprocessor.py").read_text())

    config.slides.theme = THEME_NAME
    config.slides.preprocess_script = str(pre)

    config_file = stage_dir / "mkslides.yml"
    OmegaConf.save(config, config_file)
    return Staged(config_file, theme, base_theme, style)


class _SyncTimer:
    """Stand-in for threading.Timer that runs the callback immediately.

    mkslides debounces rebuilds on a timer thread, but livereload tells the
    browser to reload as soon as the watcher callback returns, i.e. before the
    rebuild is done (you see the previous save). Running the rebuild inline
    makes the reload happen after it.
    """

    daemon = True

    def __init__(self, interval, function) -> None:
        self.function = function

    def start(self) -> None:
        self.function()

    def cancel(self) -> None:
        pass


def patch_build(staged: Staged, deck: Path, stage_dir: Path) -> None:
    """Hook mkslides' build/serve: copy our CSS into the output and keep serve live.

    mkslides expects the CSS inside the output dir, so copy it after every build.
    On every serve reload the deck is staged again, so edits to the deck's
    mkslides.yml or style.css apply, and the rebuild finishes before the
    browser reloads.
    """
    import types

    import mkslides.__main__ as main
    import mkslides.serve as serve

    current = [staged]
    original_build = main.build
    original_get_config = serve.get_config

    def build(config, input_path, output_path, strict):
        original_build(config, input_path, output_path, strict)
        output = Path(output_path)
        latest = current[0]
        for asset in (latest.theme, latest.base_theme):
            shutil.copy(asset, output / asset.name)
        if latest.style:
            shutil.copy(latest.style, output / latest.style.name)

    def get_config(config_path):
        try:
            current[0] = stage(deck, stage_dir)
        except click.ClickException as error:
            click.echo(f"melasa: {error.message}; keeping the previous config", err=True)
        return original_get_config(config_path)

    main.build = build
    serve.build = build
    serve.get_config = get_config
    serve.threading = types.SimpleNamespace(Timer=_SyncTimer)


path_arg = click.argument(
    "path",
    type=click.Path(exists=True, resolve_path=True, path_type=Path),
    default=".",
)


@click.group()
def main() -> None:
    """Build and serve slides with the shared melasa theme.

    Start a deck with `init [--style NAME]`; `init --list` shows the available
    styles.

    Image optimization (resize, PNG/JPEG to WebP) is off by default: use
    `build --optimize`, or `optimize SITE_DIR` on an existing site.
    Sources are never modified, only the built site.
    """


@main.command()
@click.option("--style", metavar="NAME", default=DEFAULT_STYLE, show_default=True, help="Style from the library: copies its style.css and mkslides.yml (reveal.js theme).")
@click.option("--list", "list_only", is_flag=True, help="List available styles and exit.")
def init(style: str, list_only: bool) -> None:
    """Create a starter presentation (index.md, style.css, mkslides.yml).

    style.css holds only your overrides; the reveal.js theme is named in
    mkslides.yml. Use --list to see the available styles.
    """
    styles = list_styles()
    if list_only:
        click.echo("\n".join(styles))
        return
    if style not in styles:
        raise click.ClickException(f"unknown style {style!r}; available: {', '.join(styles)}")

    existing = [name for name in STARTER_FILES if (Path.cwd() / name).exists()]
    if existing:
        verb = "exists" if len(existing) == 1 else "exist"
        raise click.ClickException(
            f"{', '.join(existing)} already {verb}; refusing to overwrite"
        )

    source = DATA / "styles" / style
    contents = {
        "index.md": DATA.joinpath("starter_index.md").read_text(),
        "style.css": source.joinpath("style.css").read_text(),
        "mkslides.yml": source.joinpath("mkslides.yml").read_text(),
    }
    for name, content in contents.items():
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
        patch_build(staged, deck, Path(tmp))
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
