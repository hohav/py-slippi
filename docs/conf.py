# -*- coding: utf-8 -*-
#
# Configuration file for the Sphinx documentation builder.
# http://www.sphinx-doc.org/en/master/config

# -- Path setup --------------------------------------------------------------

import os
import sys
from typing import Any

sys.path.insert(0, os.path.abspath('..'))


# -- Project information -----------------------------------------------------

project = 'py-slippi'
author = 'melkor'

version = '1.6.1'
release = '1.6.1'


# -- General configuration ---------------------------------------------------

extensions = ['sphinx.ext.autodoc', 'sphinx_autodoc_typehints']
templates_path = ['_templates']
source_suffix = ['.rst']
master_doc = 'index'
exclude_patterns = ['_build']
pygments_style = 'sphinx'


# -- Options for HTML output -------------------------------------------------

html_theme = 'alabaster'

html_theme_options = {
    'description': 'Python parser for SSBM replay files',
    'fixed_sidebar': True,
    'github_button': True,
    'github_repo': "py-slippi",
    'github_user': "hohav",
}

html_static_path = ['_static']

html_sidebars = {
    "**": [
        "about.html",
        "localtoc.html",
        "relations.html",
        "searchbox.html",
    ]
}


# -- Extension configuration -------------------------------------------------

from sphinx.ext.autodoc import ClassLevelDocumenter
from sphinx.ext.autodoc.deprecated import InstanceAttributeDocumenter

autodoc_member_order = 'bysource'

def skip(app: Any, what: Any, name: Any, obj: Any, skip: Any, options: Any) -> Any:
    if name == '__init__' and obj.__doc__:
        return False
    return skip

def setup(app: Any) -> None:
    app.connect("autodoc-skip-member", skip)
    app.add_stylesheet('custom.css')
    app.add_javascript('custom.js')

# remove the useless " = None" after every ivar
def iad_add_directive_header(self: Any, sig: str) -> None:
    ClassLevelDocumenter.add_directive_header(self, sig)

InstanceAttributeDocumenter.add_directive_header = iad_add_directive_header  # type: ignore[assignment]
