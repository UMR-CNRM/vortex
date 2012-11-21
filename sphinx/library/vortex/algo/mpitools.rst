:mod:`vortex.algo.mpitools` --- MPI launcher interface
======================================================

.. automodule:: vortex.algo.mpitools
   :synopsis: MPI launcher interface

.. moduleauthor:: The Vortex Team
.. sectionauthor:: The Vortex Team
.. versionadded:: 0.2

Package
-------

.. autodata:: __all__


Interface
---------

As a :mod:`vortex.utilities.catalogs` based module,
:mod:`vortex.tools.targets` automaticaly defined the following functions:

.. autofunction:: catalog
   
.. autofunction:: pickup

.. autofunction:: load

Classes
-------
   
.. autoclass:: MpiToolsCatalog
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: MpiTool
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: MpiRun
   :show-inheritance:
   :members:
   :member-order: alphabetical
