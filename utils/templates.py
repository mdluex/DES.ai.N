"""
Template file helpers.

Centralises every place in the codebase that needs to recognise Photoshop
template files. Both `.psd` (standard Photoshop document) and `.psb`
("Photoshop Big" — used for documents larger than 30,000 px or 2 GB) are
treated as first-class templates.
"""

import os
from typing import Iterable, List, Optional


# All extensions we consider valid Photoshop templates. Order matters when
# resolving a bare filename (we try PSD first, then PSB).
SUPPORTED_EXTENSIONS: tuple = (".psd", ".psb")


def is_photoshop_template(filename: str) -> bool:
    """Return True if `filename` looks like a Photoshop template (psd or psb)."""
    if not filename:
        return False
    return filename.lower().endswith(SUPPORTED_EXTENSIONS)


def list_templates(folder: str) -> List[str]:
    """List Photoshop templates inside `folder`.

    Returns only files that end with .psd / .psb (case-insensitive), sorted
    alphabetically. Returns an empty list if the folder does not exist.
    Hidden files (starting with `.`) are skipped.
    """
    if not folder or not os.path.isdir(folder):
        return []
    try:
        names = os.listdir(folder)
    except OSError:
        return []
    return sorted(
        n for n in names
        if not n.startswith(".") and is_photoshop_template(n)
    )


def resolve_template_path(folder: str, name: str) -> Optional[str]:
    """Resolve a (possibly bare) template name to an absolute path.

    Resolution order, all case-insensitive:
      1. Exact filename match (with .psd or .psb extension).
      2. Bare name → try `<name>.psd` then `<name>.psb`.
      3. Substring match against the templates listing (e.g. "figo" matches
         "FIGO Ride hailing app - Social media post.psd").

    Returns the absolute path to the file, or None if nothing matched.
    """
    if not folder or not name:
        return None

    name = name.strip()
    if not name:
        return None

    candidates = list_templates(folder)
    if not candidates:
        return None

    lname = name.lower()

    # 1. Exact match (with extension)
    if is_photoshop_template(name):
        for c in candidates:
            if c.lower() == lname:
                return os.path.join(folder, c)
        return None  # Caller gave a specific extension that doesn't exist.

    # 2. Bare name → try PSD then PSB
    for ext in SUPPORTED_EXTENSIONS:
        target = (name + ext).lower()
        for c in candidates:
            if c.lower() == target:
                return os.path.join(folder, c)

    # 3. Substring match against base names (without extension)
    for c in candidates:
        base = os.path.splitext(c)[0].lower()
        if lname in base:
            return os.path.join(folder, c)

    # 4. Substring against the full filename (last resort)
    for c in candidates:
        if lname in c.lower():
            return os.path.join(folder, c)

    return None


def format_template_listing(folder: str) -> str:
    """Human-readable listing of templates in a folder, useful for prompts."""
    items = list_templates(folder)
    if not items:
        return "(no PSD/PSB templates found)"
    return ", ".join(items)
