import pytest


@pytest.fixture(autouse=True)
def restore_mkslides_patches(monkeypatch):
    """patch_build monkeypatches mkslides module globals; undo after each test."""
    import mkslides.__main__ as mk_main
    import mkslides.serve as mk_serve

    for module, name in (
        (mk_main, "build"),
        (mk_serve, "build"),
        (mk_serve, "get_config"),
        (mk_serve, "threading"),
    ):
        monkeypatch.setattr(module, name, getattr(module, name))
