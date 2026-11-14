"""Build a deterministic Lambda archive from Linux wheels for Python 3.13."""

import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build" / "api.zip")
    args = parser.parse_args()
    target = ROOT / "build" / "package"
    if not target.resolve().is_relative_to(ROOT) or target.is_symlink():
        raise ValueError("Package directory must resolve inside the repository")
    if target.exists():
        shutil.rmtree(target)  # Fixed build directory, never a caller-supplied path.
    target.mkdir(parents=True)
    # Keep pip's command and arguments fixed. Select the trusted interpreter
    # explicitly and resolve relative paths from the repository, without a shell.
    subprocess.run(
        [
            "python",
            "-m",
            "pip",
            "install",
            "--requirement",
            "requirements.txt",
            "--target",
            "build/package",
            "--platform",
            "manylinux2014_x86_64",
            "--python-version",
            "3.13",
            "--implementation",
            "cp",
            "--abi",
            "cp313",
            "--only-binary=:all:",
            "--no-compile",
        ],
        executable=sys.executable,
        cwd=ROOT,
        shell=False,
        check=True,
    )
    shutil.copytree(ROOT / "app", target / "app", ignore=shutil.ignore_patterns("__pycache__"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for source in sorted(target.rglob("*")):
            if source.is_file() and "__pycache__" not in source.parts:
                entry = zipfile.ZipInfo(
                    source.relative_to(target).as_posix(), (2020, 1, 1, 0, 0, 0)
                )
                entry.compress_type = zipfile.ZIP_DEFLATED
                entry.external_attr = 0o644 << 16
                archive.writestr(entry, source.read_bytes())
    print(f"Lambda package: {args.output}")


if __name__ == "__main__":
    main()
