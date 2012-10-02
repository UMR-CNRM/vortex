:mod:`vortex.tools.systems` --- Basic system interfaces
=======================================================

.. automodule:: vortex.tools.systems
   :synopsis: Basic system interfaces

.. moduleauthor:: The Vortex Team
.. sectionauthor:: The Vortex Team
.. versionadded:: 0.2.0

.. warning::

   Guess what? The documentation of this module is at a point of complemention
   comparable to its parent package. 
   
Package
-------

.. autodata:: __all__


Interface
---------

As a :mod:`vortex.utilities.catalogs` based module,
:mod:`vortex.tools.systems` automaticaly defined the following functions:

.. autofunction:: catalog
   
.. autofunction:: pickup

.. autofunction:: load


Classes
-------
   
.. autoclass:: SystemsCatalog
   :show-inheritance:
   :members:
   :member-order: bysource

.. autoclass:: System
   :show-inheritance:
   :members:
   :member-order: bysource

.. autoclass:: LinuxBase
   :show-inheritance:
   :members:
   :member-order: bysource

