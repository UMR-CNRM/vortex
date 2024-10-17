:mod:`vortex.tools.storage` --- Storage place management
========================================================

.. automodule:: vortex.tools.storage
   :synopsis: Storage place management

.. moduleauthor:: The Vortex Team
.. sectionauthor:: The Vortex Team
.. versionadded:: 0.7


Package
-------

.. autodata:: __all__


Classes
-------

Storage abstract class
**********************

.. autoclass:: Storage
   :show-inheritance:
   :members:
   :member-order: alphabetical

Generic Cache and Archive management classes
********************************************

.. autoclass:: Cache
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: AbstractArchive
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: Archive
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: AbstractLocalArchive
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: LocalArchive
   :show-inheritance:
   :members:
   :member-order: alphabetical

Specialised Cache management classes
************************************

.. autoclass:: FixedEntryCache
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: MtoolCache
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: MtoolBuddiesCache
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: FtStashCache
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: Op2ResearchCache
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: HackerCache
   :show-inheritance:
   :members:
   :member-order: alphabetical


Decorators (Module's internal use only)
---------------------------------------

.. autofunction:: do_recording

.. autofunction:: enforce_readonly
