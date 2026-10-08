import ast
import pathlib

PKG = pathlib.Path(__file__).resolve().parents[1] / "sciqlop_tracers_mp"
QT_FREE_ALLOWED = {"numpy", "scipy", "geopack", "speasy", "__future__", "dataclasses", "typing", "threading",
                   "collections", "datetime", "math", "logging"}


def _imports(path):
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            yield node.module


def test_core_model_format_are_qt_free():
    files = [PKG / "model.py", PKG / "ui" / "format.py", *(PKG / "core").rglob("*.py")]
    for py in files:
        for mod in _imports(py):
            assert mod.split(".")[0] in QT_FREE_ALLOWED, f"{py.name} imports {mod}"


def test_private_multiplots_line_only_in_bar():
    for py in PKG.rglob("*.py"):
        if "MultiPlotsVerticalLine" in py.read_text():
            assert py.name == "bar.py", py


def test_dock_manager_only_in_dock():
    for py in PKG.rglob("*.py"):
        if "dock_manager" in py.read_text() or "PySide6QtAds" in py.read_text():
            assert py.name == "dock.py", py
