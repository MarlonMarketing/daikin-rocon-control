"""Create a public source archive from an explicit allowlist; never include _private."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import tomllib

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_ROOTS = ("rocon_local", "custom_components", "tests", "tools", "docs")
PUBLIC_FILES = ("README.md", "LICENSE", "SECURITY.md", "pyproject.toml", ".gitignore", "Diagnostica-cloud.cmd", "hacs.json")
# Explicitly reviewed images only. Do not glob all JPGs: originals must stay out.
PUBLIC_IMAGES = (
    "docs/images/hardware/g1_etichetta_tecnica.jpg",
    "docs/images/hardware/g1_modello_identificativi_oscurati.jpg",
    "docs/images/hardware/g1_connettore_cavo_dettaglio.jpg",
    "docs/images/hardware/g1_porte_e_connettore.jpg",
    "docs/images/hardware/g1_cablaggio_esterno.jpg",
)
ALLOWED_SUFFIXES = {".py", ".ps1", ".sh", ".md", ".json", ".toml", ".txt"}
PUBLIC_ASSETS = (
    "docs/images/climate-studio-demo.png",
    "custom_components/rocon_g1_local/frontend/rocon-climate-card.js",
    "docs/interface-preview.html",
    ".github/workflows/validate.yml",
)


def public_paths():
    paths = [ROOT / name for name in PUBLIC_FILES]
    paths.extend(ROOT / name for name in PUBLIC_IMAGES)
    paths.extend(ROOT / name for name in PUBLIC_ASSETS)
    for name in PUBLIC_ROOTS:
        paths.extend(path for path in (ROOT / name).rglob("*")
                     if path.is_file() and path.suffix in ALLOWED_SUFFIXES
                     and "__pycache__" not in path.parts)
    for path in sorted(set(paths)):
        if path.is_symlink() or not path.resolve().is_relative_to(ROOT):
            raise RuntimeError("Symlink or external file refused")
        if "_private" in path.relative_to(ROOT).parts or "_private" in path.resolve().relative_to(ROOT).parts:
            raise RuntimeError("Private file refused")
        yield path


def main():
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    destination = ROOT / "dist" / f"daikin-rocon-local-{version}.zip"
    destination.parent.mkdir(exist_ok=True)
    with ZipFile(destination, "x", compression=ZIP_DEFLATED) as archive:
        for path in public_paths():
            archive.write(path, "daikin-rocon-local/" + path.relative_to(ROOT).as_posix())
    print(destination)


if __name__ == "__main__":
    main()
