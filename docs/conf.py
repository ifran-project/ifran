import sys
from pathlib import Path
import re
from datetime import date

try:
    import tomllib            # Python 3.11+
except ModuleNotFoundError:
    import tomli as tomllib   # pip install tomli

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
project = "Post5G Blueprint API Reference"
release = " / ".join(f'{p["name"]} {p["version"]}' for p in PROJECTS)
version = release

# all authors from both pyproject.toml files, without duplicates, order preserved
ALL_AUTHORS = list(dict.fromkeys(a for p in PROJECTS for a in p["authors"]))
author = ", ".join(ALL_AUTHORS)
copyright = f"{date.today().year}, {author}" if author else str(date.today().year)


# -- General configuration ---------------------------------------------------
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
}
autodoc_member_order = "bysource"
# autodoc_mock_imports = ["some_heavy_dependency"]  # if deps aren't installed

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

myst_fence_as_directive = ["mermaid"]

exclude_patterns = ["_build"]

# -- HTML output -------------------------------------------------------------
html_theme = "sphinx_rtd_theme"
html_theme_options = {
    "collapse_navigation": False,   # keep sub-trees expanded
    "navigation_depth": 4,
    "titles_only": False,
}

# -- Generate the API pages before each build --------------------------------
def _generate_api(app):
    from sphinx.ext.apidoc import main as apidoc

    api_dir = DOCS / "api"
    api_dir.mkdir(parents=True, exist_ok=True)
    toc = []

    for info in PROJECTS:
        title = f'{info["name"]} {info["version"]}'
        toc += [title, "-" * len(title), "",
                ".. toctree::",
                "   :maxdepth: 3",
                "   :titlesonly:",
                ""]
        for pkg in info["packages"]:
            apidoc([
                "--force", "--separate", "--module-first", "--no-toc",
                "--implicit-namespaces",
                "-o", str(api_dir / pkg.name), str(pkg),
            ])
            toc.append(f"   api/{pkg.name}/{pkg.name}")
        toc.append("")

    # .inc is not a Sphinx source suffix, so it is not built as a page itself
    (api_dir / "toc.inc").write_text("\n".join(toc), encoding="utf-8")
def generate_api(app):
    from sphinx.ext.apidoc import main as apidoc

    api_dir = DOCS / "api"
    index_lines = ["API", "===", ""]

    for info in PROJECTS:
        for pkg in info["packages"]:
            # one .rst per package/submodule, with automodule for each
            apidoc([
                "--force", "--separate", "--module-first", "--no-toc",
                "-o", str(api_dir / pkg.name),
                str(pkg),
            ])
            title = f'{info["name"]} {info["version"]}'
            index_lines += [
                title, "-" * len(title), "",
                ".. toctree::",
                "   :maxdepth: 2",
                "",
                f"   {pkg.name}/{pkg.name}",
                "",
            ]

    (api_dir / "index.rst").write_text("\n".join(index_lines), encoding="utf-8")


def setup(app):
    app.connect("builder-inited", generate_api)
