"""Sphinx configuration for cs310-code documentation."""

import os
import sys

sys.path.insert(0, os.path.abspath(".."))

project = "cs310-code"
author = "Alex"
release = "0.1.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autodoc.typehints",
    "sphinx.ext.mathjax",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
]

napoleon_google_docstring = True
napoleon_numpy_docstring = True

autodoc_member_order = "bysource"
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}

autodoc_mock_imports = [
    "numpy",
    "qiskit",
    "qiskit_aer",
    "qiskit_ibm_runtime",
    "matplotlib",
    "polars",
    "pylatexenc",
    "IPython",
    "ipykernel",
]

html_theme = "furo"
html_title = "cs310-code"

templates_path = ["_templates"]
exclude_patterns = ["_build"]
