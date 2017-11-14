:mod:`common.util.usepygram` --- Standard usage of EPYGRAM with VORTEX
======================================================================

.. automodule:: common.util.usepygram
   :synopsis: Common asynchronous tasks

.. moduleauthor:: The Vortex Team
.. sectionauthor:: The Vortex Team
.. versionadded:: 0.9

Package
-------

.. autodata:: __all__

Exceptions
----------

.. autoclass:: EpygramUnavailableError
   :show-inheritance:
   :members:
   :member-order: alphabetical

Functions
---------

.. autofunction:: is_epygram_available

.. autofunction:: disabled_if_no_epygram

.. autofunction:: clone_fields

.. autofunction:: epy_env_prepare

.. autofunction:: addfield

.. autofunction:: copyfield

.. autofunction:: overwritefield

.. autofunction:: mk_pgdfa923_from_pgdlfi

.. autofunction:: empty_fa


Classes
-------

.. autoclass:: EpygramMetadataReader
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: FaMetadataReader
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: GribMetadataReader
   :show-inheritance:
   :members:
   :member-order: alphabetical