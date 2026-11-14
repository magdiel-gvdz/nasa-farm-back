import json
import sys
import textwrap
import zipfile
from pathlib import Path

from scripts import package_lambda


def test_package_uses_trusted_interpreter_and_handles_paths_with_shell_characters(
    tmp_path, monkeypatch
):
    root = tmp_path / "project with spaces & semicolon;"
    root.mkdir()
    (root / "app").mkdir()
    (root / "app" / "main.py").write_text("APP_MARKER = True\n", encoding="utf-8")
    (root / "requirements.txt").write_text("", encoding="utf-8")
    # A local pip fixture exercises the real child process without network access.
    (root / "pip.py").write_text(
        textwrap.dedent("""\
            import json
            import sys
            from pathlib import Path

            Path("pip-invocation.json").write_text(json.dumps({
                "executable": sys.executable,
                "arguments": sys.argv[1:],
            }), encoding="utf-8")
            target = Path(sys.argv[sys.argv.index("--target") + 1])
            (target / "dependency.py").write_text("DEPENDENCY_MARKER = True\\n")
        """),
        encoding="utf-8",
    )
    output = root / "artifact with spaces & semicolon;.zip"
    monkeypatch.setattr(package_lambda, "ROOT", root)
    monkeypatch.setattr(sys, "argv", ["package_lambda.py", "--output", str(output)])
    monkeypatch.chdir(tmp_path)

    package_lambda.main()

    invocation = json.loads((root / "pip-invocation.json").read_text(encoding="utf-8"))
    assert Path(invocation["executable"]).resolve() == Path(sys.executable).resolve()
    assert invocation["arguments"][:5] == [
        "install",
        "--requirement",
        "requirements.txt",
        "--target",
        "build/package",
    ]
    assert str(root) not in invocation["arguments"]
    assert str(output) not in invocation["arguments"]
    with zipfile.ZipFile(output) as archive:
        assert set(archive.namelist()) == {"dependency.py", "app/main.py"}
        assert archive.read("app/main.py") == (root / "app" / "main.py").read_bytes()
