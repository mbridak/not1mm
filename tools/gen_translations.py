"""Regenerate Qt translation files for not1mm.

Run from the repository root:

    python tools/gen_translations.py

Merges new source strings into each existing not1mm_<lang>.ts (preserving
already-translated strings), and compiles every not1mm_<lang>.ts to
not1mm_<lang>.qm with lrelease. Requires pylupdate6 on PATH; lrelease is
looked up on PATH or inside installed Qt packages.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRANS_DIR = ROOT / "not1mm" / "data" / "translations"


NOISE_DIRS = {
    ".Trash", "Trash", ".cache", ".git", "__pycache__", "node_modules",
    ".npm", ".cargo", ".lmstudio", ".local/lib/python3", ".rustup",
}


def find_lrelease() -> str:
    found = shutil.which("lrelease")
    if found:
        return found
    for root, max_depth in ((Path.home(), 12), (Path("/usr"), 6)):
        if not root.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            if "lrelease" in filenames:
                return str(Path(dirpath) / "lrelease")
            depth = len(Path(dirpath).relative_to(root).parts)
            if depth >= max_depth:
                dirnames[:] = []
            else:
                dirnames[:] = [d for d in dirnames if d not in NOISE_DIRS]
    return "lrelease"


def source_files() -> list:
    return [
        str(path)
        for path in sorted((ROOT / "not1mm").rglob("*"))
        if path.suffix in {".py", ".ui"}
        and ".venv" not in path.parts
        and "build" not in path.parts
    ]


def pylupdate(ts_path: Path) -> None:
    subprocess.run(
        ["pylupdate6", *source_files(), "-ts", str(ts_path)],
        check=True,
        cwd=ROOT,
    )


def lrelease(ts_path: Path, lrelease_bin: str) -> None:
    subprocess.run([lrelease_bin, str(ts_path)], check=True, cwd=ROOT)


def main() -> int:
    if shutil.which("pylupdate6") is None:
        print("pylupdate6 not found on PATH", file=sys.stderr)
        return 1
    lrelease_bin = find_lrelease()

    TRANS_DIR.mkdir(parents=True, exist_ok=True)

    template = TRANS_DIR / "not1mm.ts"
    print(f"Updating {template.name}")
    pylupdate(template)

    languages = sorted(
        path.stem[len("not1mm_"):]
        for path in TRANS_DIR.glob("not1mm_*.ts")
    )
    if not languages:
        print("No not1mm_<lang>.ts files found.", file=sys.stderr)
        return 1

    for code in languages:
        ts = TRANS_DIR / f"not1mm_{code}.ts"
        print(f"Updating {ts.name}")
        pylupdate(ts)
        lrelease(ts, lrelease_bin)

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
