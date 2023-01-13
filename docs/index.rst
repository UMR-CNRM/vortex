.. bronx documentation master file, created by
   sphinx-quickstart on Wed Nov  2 14:34:54 2022.

Welcome to arpifs_listings documentation!
=========================================

The :mod:`arpifs_listings` package provides a toolbox to process and compare
various data from Arpege/IFS listings.

A command line toos is provided with this package. It is called
``compare_listings.py``. This command line utility is provided with an embedded
documentation accessible with the `-h` option (e.g. ``compare_listings.py -h``).

Within a Python script, the :func:`arpifs_listings.compare_files` and
:func:`arpifs_listings.show_TL_test`  function provides a high-level interface
to the :mod:`arpifs_listings` package.

A lower-level interface is accessible in the :mod:`arpifs_listings.listings`
module.

Developers' corner
------------------

Browse the package content:

.. autosummary::
   :toctree: _autosummary
   :template: autosummary/custom-module.tpl
   :recursive:

   arpifs_listings

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
