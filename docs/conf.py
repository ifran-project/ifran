import sys
from pathlib import Path
import re
from datetime import date
import tomllib


DOCS = Path(__file__).resolve().parent
ROOT = DOCS.parent
PROJECT_DIRS = ["."]

def parse_authors(meta: dict) -> list[str]:
    """Return author names from PEP 621 or Poetry metadata."""
    names = []
    for entry in meta.get("authors", []):
        if isinstance(entry, dict):          # PEP 621: {name = "...", email = "..."}
            name = entry.get("name") or entry.get("email", "")
        else:                                # Poetry: "Name <email@example.com>"
            name = re.sub(r"\s*<[^>]*>\s*$", "", str(entry))
        if name:
            names.append(name.strip())
    return names

def read_project(directory: Path) -> dict:
    data = tomllib.loads((directory / "pyproject.toml").read_text(encoding="utf-8"))
    meta = data.get("project") or data.get("tool", {}).get("poetry", {})
    src = directory / "src"
    packages = sorted(
        p for p in src.iterdir()
        if p.is_dir()
        and not p.name.startswith((".", "_"))
        and not p.name.endswith(".egg-info")
        and any(p.rglob("*.py"))
    )
    print(f'[docs] {meta["name"]}: packages={[p.name for p in packages]}, '
          f'authors={parse_authors(meta)}')
    return {
        "name": meta["name"],
        "version": meta.get("version", "unknown"),
        "authors": parse_authors(meta),
        "src": src,
        "packages": packages,
    }

PROJECTS = [read_project(ROOT / d) for d in PROJECT_DIRS]

# Make the packages importable for autodoc
for info in PROJECTS:
    sys.path.insert(0, str(info["src"]))

# -- Project information -----------------------------------------------------
project = "IFRAN: Interoperable Framework for Reproducible Automation of Networks"
release = " / ".join(f'{p["name"]} {p["version"]}' for p in PROJECTS)
version = release

# all authors from both pyproject.toml files, without duplicates, order preserved
ALL_AUTHORS = list(dict.fromkeys(a for p in PROJECTS for a in p["authors"]))
author = ", ".join(ALL_AUTHORS)
copyright = f"{date.today().year}, {author}" if author else str(date.today().year)


# General configuration
root_doc = "index"
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",   # Google / NumPy style docstrings
    "sphinx.ext.viewcode",
    "myst_parser",
    "sphinxcontrib.mermaid",
]
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
    "no-index": True,
}
autodoc_member_order = "bysource"
# autodoc_mock_imports = ["some_heavy_dependency"]  # if deps aren't installed

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

myst_fence_as_directive = ["mermaid"]
suppress_warnings = ["myst.xref_missing"]

exclude_patterns = ["_build"]

# HTML output
html_title = "IFRAN: Interoperable Framework for Reproducible Automation of Networks"
html_short_title = "IFRAN"
html_theme = "furo"
html_theme_options = {}


def generate_reference(app):
    from sphinx.ext.apidoc import main as apidoc
    import shutil

    reference_dir = DOCS / "reference"
    reference_dir.mkdir(parents=True, exist_ok=True)

    # Remove the old intermediate Python reference directory
    python_dir = reference_dir / "python"
    if python_dir.exists():
        shutil.rmtree(python_dir)

    # Build the API Reference index directly
    packages_index = [
        "API Reference",
        "===============",
        "",
        "Automatically generated documentation of Python models "
        "and supporting modules.",
        "",
        ".. toctree::",
        "   :maxdepth: 3",
        "",
    ]

    for info in PROJECTS:
        for pkg in info["packages"]:
            apidoc([
                "--force",
                "--separate",
                "--module-first",
                "--implicit-namespaces",
                "--tocfile", "index",
                "-o", str(reference_dir / pkg.name),
                str(pkg),
            ])

            packages_index.append(f"   {pkg.name}/index")

    (reference_dir / "index.rst").write_text(
        "\n".join(packages_index) + "\n",
        encoding="utf-8",
    )


def setup(app):
    app.connect("builder-inited", generate_reference)

