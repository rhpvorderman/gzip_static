# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

from distutils.dist import DistributionMetadata
from pathlib import Path

import pkg_resources

# -- Project information -----------------------------------------------------

# Get package information from the installed package.
package = pkg_resources.get_distribution("gzip_static")
metadata_file = Path(package.egg_info) / Path(package.PKG_INFO)
metadata = DistributionMetadata(path=str(metadata_file))

project = 'gzip_static'
copyright = '2021, Ruben Vorderman'
author = 'Ruben Vorderman'

# The short X.Y version
version = package.parsed_version.base_version
# The full version, including alpha/beta/rc tags
release = package.version


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ["sphinx.ext.autodoc", "sphinxarg.ext"]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'
html_theme_options = dict(
    display_version=True,
)

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']