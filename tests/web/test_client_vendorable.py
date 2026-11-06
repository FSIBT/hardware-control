"""``hc_web/client.py`` is meant to be copied into other projects: stdlib only."""

import ast
import os
import shutil
import subprocess
import sys
from pathlib import Path

CLIENT = Path(__file__).parents[2] / "src" / "hc_web" / "client.py"


def test_client_file_is_vendorable(tmp_path):
    vendored = tmp_path / "vendored"
    vendored.mkdir()
    shutil.copy(CLIENT, vendored / "client.py")

    code = (
        "import importlib.util, sys\n"
        "spec = importlib.util.spec_from_file_location('client', "
        f"{str(vendored / 'client.py')!r})\n"
        "mod = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(mod)\n"
        "assert mod.WebClient('http://localhost', '1.x').url == 'http://localhost'\n"
        "bad = sorted(m for m in sys.modules "
        "if m.split('.')[0] in ('hc_web', 'hardware_control', 'flask', 'PyQt6'))\n"
        "assert not bad, bad\n"
        "print('ok')\n"
    )
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-c", code],
        cwd=vendored,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"

    # `import client` itself, with the directory on sys.path
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-S",
            "-c",
            f"import sys; sys.path.insert(0, {str(vendored)!r}); import client",
        ],
        cwd=vendored,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr


def test_client_imports_only_the_standard_library():
    tree = ast.parse(CLIENT.read_text())
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "relative import"
            found.add(node.module.split(".")[0])
    assert found, "no imports found"
    found.discard("certifi")  # optional, imported lazily as a CA bundle fallback
    assert found <= set(sys.stdlib_module_names), found - set(sys.stdlib_module_names)


def test_client_module_docstring_shows_usage():
    doc = ast.get_docstring(ast.parse(CLIENT.read_text()))
    assert "curl" in doc
    assert "WebClient(" in doc
    assert ".send(" in doc
