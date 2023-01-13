"""
Configuration file for the Sphinx documentation builder.
"""

#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import sys
import os
# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# This will make sphinx crash if something goes wrong with bronx import !
import footprints

assert footprints

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'footprints'
copyright = '2022, The Vortex Team'
author = 'The Vortex Team'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',       # Core library for html generation from docstrings
    'sphinx.ext.autosummary',   # Create neat summary tables
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx'
]
autosummary_generate = True  # Turn on sphinx.ext.autosummary

intersphinx_mapping = {
    "bronx": ("https://bronx.readthedocs.io/en/latest", None),
}

# Concatenate the class docstring and the __init__ docstring
autoclass_content = 'both'

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinxdoc'
