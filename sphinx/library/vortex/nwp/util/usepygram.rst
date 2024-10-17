:mod:`vortex.nwp.util.usepygram` --- Standard usage of EPYGRAM with VORTEX
==========================================================================

.. automodule:: vortex.nwp.util.usepygram
   :synopsis: Common asynchronous tasks

.. moduleauthor:: The Vortex Team
.. sectionauthor:: The Vortex Team
.. versionadded:: 0.9

Package
-------

.. autodata:: __all__

Public Data
-----------

.. autodata:: epygram_checker


Functions
---------

.. autofunction:: clone_fields

.. autofunction:: epy_env_prepare

.. autofunction:: addfield

.. autofunction:: copyfield

.. autofunction:: overwritefield

.. autofunction:: updatefield

.. autofunction:: mk_pgdfa923_from_pgdlfi

.. autofunction:: empty_fa

.. autofunction:: geopotentiel2zs

.. autofunction:: add_poles_to_GLOB_file

.. autofunction:: add_poles_to_reglonlat_file

.. autofunction:: split_errgrib_on_shortname

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
