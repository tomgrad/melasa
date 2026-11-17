from pathlib import Path

import click
import pytest

from click.testing import CliRunner
from omegaconf import OmegaConf

from melasa.cli import DATA, main, stage


def test_init_creates_starter_files(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(main, ["init"])

    index = tmp_path / "index.md"
    style = tmp_path / "style.css"
    config = tmp_path / "mkslides.yml"
    assert result.exit_code == 0
    assert index.is_file()
    assert index.read_text().startswith("# ")
    assert "---" in index.read_text()
    assert style.is_file()
    assert style.read_text().startswith("/*")
    assert "override" in style.read_text().lower()
    assert config.is_file()
    assert "theme: beige" in config.read_text()
    assert "league" in config.read_text()


def test_init_garamond_copies_style(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(main, ["init", "--style", "garamond"])

    assert result.exit_code == 0, result.output
    style = (tmp_path / "style.css").read_text()
    assert "EB Garamond" in style
    assert "reveal-js/dist/theme" not in style
    assert "theme: beige" in (tmp_path / "mkslides.yml").read_text()


def test_init_unknown_style(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(main, ["init", "--style", "nope"])

    assert result.exit_code != 0
    assert "default" in result.output and "garamond" in result.output
    assert list(tmp_path.iterdir()) == []


def test_init_list(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(main, ["init", "--list"])

    assert result.exit_code == 0
    assert result.output.split() == ["default", "garamond"]
    assert list(tmp_path.iterdir()) == []


def test_starter_index_demos_tags(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    CliRunner().invoke(main, ["init"])

    index = (tmp_path / "index.md").read_text()
    for tag in ("<!-- c21 -->", "<!-- box -->", "<!-- footnote -->"):
        assert tag in index


def test_init_refuses_to_overwrite_existing_index(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "index.md").write_text("# My deck\n")

    result = CliRunner().invoke(main, ["init"])

    assert result.exit_code != 0
    assert (tmp_path / "index.md").read_text() == "# My deck\n"
    assert not (tmp_path / "style.css").exists()
    assert not (tmp_path / "mkslides.yml").exists()
    assert "already exists" in result.output


def test_init_refuses_to_overwrite_existing_style(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "style.css").write_text("/* my styles */\n")

    result = CliRunner().invoke(main, ["init"])

    assert result.exit_code != 0
    assert (tmp_path / "style.css").read_text() == "/* my styles */\n"
    assert not (tmp_path / "index.md").exists()
    assert not (tmp_path / "mkslides.yml").exists()
    assert "style.css already exists" in result.output


def test_stage_uses_theme_from_deck_config(tmp_path: Path) -> None:
    deck = tmp_path / "deck"
    deck.mkdir()
    (deck / "mkslides.yml").write_text("slides:\n  theme: league\n")
    stage_dir = tmp_path / "stage"
    stage_dir.mkdir()

    staged = stage(deck, stage_dir)

    assert staged.theme.read_text().splitlines()[0] == (
        '@import url("mkslides-assets/reveal-js/dist/theme/league.css");'
    )
    assert OmegaConf.load(staged.config).slides.theme == "melasa-theme.css"


def test_stage_uses_beige_as_default_theme(tmp_path: Path) -> None:
    deck = tmp_path / "deck"
    deck.mkdir()
    stage_dir = tmp_path / "stage"
    stage_dir.mkdir()

    staged = stage(deck, stage_dir)

    assert staged.theme.read_text().splitlines()[0] == (
        '@import url("mkslides-assets/reveal-js/dist/theme/beige.css");'
    )


def test_stage_layers_deck_style_after_the_global_theme(tmp_path: Path) -> None:
    deck = tmp_path / "deck"
    deck.mkdir()
    (deck / "mkslides.yml").write_text("slides:\n  theme: league\n")
    (deck / "style.css").write_text(".reveal h1 { color: navy; }\n")
    stage_dir = tmp_path / "stage"
    stage_dir.mkdir()

    staged = stage(deck, stage_dir)

    assert staged.theme.read_text().splitlines() == [
        '@import url("mkslides-assets/reveal-js/dist/theme/league.css");',
        '@import url("melasa.css");',
        '@import url("style.css");',
    ]
    assert staged.style == deck / "style.css"


def test_stage_omits_style_import_without_deck_style(tmp_path: Path) -> None:
    deck = tmp_path / "deck"
    deck.mkdir()
    stage_dir = tmp_path / "stage"
    stage_dir.mkdir()

    staged = stage(deck, stage_dir)

    assert "style.css" not in staged.theme.read_text()
    assert staged.style is None


def test_stage_ignores_legacy_local_overrides(tmp_path: Path) -> None:
    deck = tmp_path / "deck"
    deck.mkdir()
    (deck / "custom.css").write_text(".x{}\n")
    (deck / "preprocessor.py").write_text("raise SystemExit\n")
    stage_dir = tmp_path / "stage"
    stage_dir.mkdir()

    staged = stage(deck, stage_dir)

    assert staged.base_theme.read_text() == DATA.joinpath("melasa.css").read_text()
    pre = OmegaConf.load(staged.config).slides.preprocess_script
    assert pre.endswith("preprocessor.py")
    assert not pre.startswith(str(deck))


def test_melasa_css_is_structural_only() -> None:
    css = DATA.joinpath("melasa.css").read_text()

    assert ".cols21" in css and ".box" in css
    assert "font-family" not in css
    assert "darkorange" not in css


def test_build_layers_deck_style_over_selected_theme(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    deck = tmp_path / "deck"
    deck.mkdir()
    (deck / "index.md").write_text("# Title\n")
    (deck / "mkslides.yml").write_text("slides:\n  theme: league\n")
    (deck / "style.css").write_text(".reveal h1 { color: navy; }\n")
    site = tmp_path / "site"

    result = CliRunner().invoke(main, ["build", str(deck), "-d", str(site)])

    assert result.exit_code == 0, result.output
    assert "melasa-theme.css" in (site / "index.html").read_text()
    assert (site / "melasa-theme.css").read_text().splitlines() == [
        '@import url("mkslides-assets/reveal-js/dist/theme/league.css");',
        '@import url("melasa.css");',
        '@import url("style.css");',
    ]
    assert (site / "melasa.css").is_file()
    assert (site / "style.css").read_text() == ".reveal h1 { color: navy; }\n"
    assert Path.cwd() == tmp_path


def test_stage_accepts_url_theme(tmp_path: Path) -> None:
    deck = tmp_path / "deck"
    deck.mkdir()
    (deck / "mkslides.yml").write_text("slides:\n  theme: https://example.com/t.css\n")
    stage_dir = tmp_path / "stage"
    stage_dir.mkdir()

    staged = stage(deck, stage_dir)

    assert staged.theme.read_text().splitlines()[0] == '@import url("https://example.com/t.css");'


def test_stage_rejects_unknown_local_theme(tmp_path: Path) -> None:
    deck = tmp_path / "deck"
    deck.mkdir()
    (deck / "mkslides.yml").write_text("slides:\n  theme: custom.css\n")
    stage_dir = tmp_path / "stage"
    stage_dir.mkdir()

    with pytest.raises(click.ClickException, match="custom.css"):
        stage(deck, stage_dir)
