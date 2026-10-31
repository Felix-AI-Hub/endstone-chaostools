"""Build one wheel per plugin into dist/ using only the standard library."""

import base64
import hashlib
import pathlib
import py_compile
import re
import tomllib
import zipfile

ROOT = pathlib.Path(__file__).parent
DIST = ROOT / "dist"


def record_line(name: str, data: bytes) -> str:
    digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
    return f"{name},sha256={digest},{len(data)}\n"


def build(project: pathlib.Path) -> pathlib.Path:
    meta = tomllib.loads((project / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    package = project.name.join(["endstone_", ""])
    info = f"{package}-{meta['version']}.dist-info"
    (slug, entry), = meta["entry-points"]["endstone"].items()

    files: dict[str, bytes] = {}
    for path in sorted((project / package).glob("*.py")):
        py_compile.compile(str(path), cfile=str(DIST / "check.pyc"), doraise=True)
        files[f"{package}/{path.name}"] = path.read_bytes()
    files[f"{info}/METADATA"] = (
        f"Metadata-Version: 2.4\nName: {meta['name']}\nVersion: {meta['version']}\n"
        f"Summary: {meta['description']}\nRequires-Python: {meta['requires-python']}\n"
    ).encode()
    files[f"{info}/WHEEL"] = b"Wheel-Version: 1.0\nGenerator: build.py\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
    files[f"{info}/entry_points.txt"] = f"[endstone]\n{slug} = {entry}\n".encode()
    files[f"{info}/top_level.txt"] = f"{package}\n".encode()

    record = "".join(record_line(name, data) for name, data in files.items()) + f"{info}/RECORD,,\n"
    wheel = DIST / f"{package}-{meta['version']}-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
        archive.writestr(f"{info}/RECORD", record)
    return wheel


def main() -> None:
    DIST.mkdir(exist_ok=True)
    for old in DIST.glob("*"):
        old.unlink()
    for project in sorted((ROOT / "plugins").iterdir()):
        print(build(project).name)
    (DIST / "check.pyc").unlink(missing_ok=True)


if __name__ == "__main__":
    main()
