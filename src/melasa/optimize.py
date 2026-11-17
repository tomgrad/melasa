"""Shrink bitmap images in a built site: resize and convert PNG/JPEG to WebP.

Only the site directory is touched, never the slide sources.
"""

import re
from pathlib import Path
from urllib.parse import quote, unquote

import click
from PIL import Image, ImageOps

DEFAULT_MAX_SIZE = 1920
DEFAULT_QUALITY = 82

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}
TEXT_SUFFIXES = {".html", ".css", ".md", ".js"}
ASSETS_DIR = "mkslides-assets"
REF_RE = re.compile(r"""[^\s"'()<>=]+?\.(?:png|jpe?g)\b""", re.IGNORECASE)


def convert(path: Path, max_size: int, quality: int) -> Path | None:
    """Convert one image to WebP next to it; return the new path, or None if not worth it."""
    target = path.with_suffix(".webp")
    with Image.open(path) as img:
        if getattr(img, "is_animated", False):
            return None
        img = ImageOps.exif_transpose(img)
        if max(img.size) > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA" if "transparency" in img.info or img.mode in ("LA", "PA") else "RGB")
        img.save(target, "WEBP", quality=quality, method=6)
    if target.stat().st_size >= path.stat().st_size:
        target.unlink()
        return None
    return target


def rewrite_refs(site: Path, converted: dict[Path, Path]) -> int:
    """Point references in text files at the converted images."""
    changed = 0
    for file in site.rglob("*"):
        if not file.is_file() or file.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if ASSETS_DIR in file.relative_to(site).parts:
            continue
        text = file.read_text(encoding="utf-8")

        def sub(m: re.Match) -> str:
            ref = m.group(0)
            candidate = (file.parent / unquote(ref.split("?")[0].split("#")[0])).resolve()
            new = converted.get(candidate)
            if new is None:
                return ref
            stem = ref[: ref.rfind(".")]
            return stem + ".webp"

        new_text = REF_RE.sub(sub, text)
        if new_text != text:
            file.write_text(new_text, encoding="utf-8")
            changed += 1
    return changed


def optimize_site(site: Path, max_size: int = DEFAULT_MAX_SIZE, quality: int = DEFAULT_QUALITY) -> None:
    converted: dict[Path, Path] = {}
    before = after = 0
    for file in sorted(site.rglob("*")):
        if not file.is_file() or file.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        if ASSETS_DIR in file.relative_to(site).parts:
            continue
        size = file.stat().st_size
        try:
            target = convert(file, max_size, quality)
        except OSError as e:
            click.echo(f"skipped {file.relative_to(site)}: {e}", err=True)
            continue
        before += size
        if target is None:
            after += size
            continue
        after += target.stat().st_size
        converted[file.resolve()] = target
    rewrite_refs(site, converted)
    for original in converted:
        original.unlink()
    click.echo(
        f"Optimized {len(converted)} images: {before / 1e6:.1f} MB -> {after / 1e6:.1f} MB"
    )
