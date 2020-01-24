:mod:`vortex.tools.systems` --- Basic system interfaces
=======================================================

.. automodule:: vortex.tools.systems
   :synopsis: Basic system interfaces

.. moduleauthor:: The Vortex Team
.. sectionauthor:: The Vortex Team
.. versionadded:: 0.2.0


Package
-------

.. autodata:: __all__


Exceptions
----------

.. autoclass:: ExecutionError
   :show-inheritance:

.. autoclass:: CopyTreeError
   :show-inheritance:


Classes
-------

Misc
****

.. autoclass:: FtpFlavourTuple
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autofunction:: setlocale

.. autofunction:: LocaleContext

Generic system objects
**********************

.. autoclass:: System
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: OSExtended
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: Garbage
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: Garbage27
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: Garbage34p
   :show-inheritance:
   :members:
   :member-order: alphabetical

OS specific system objects: Linux
*********************************

.. autoclass:: Linux
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: Linux27
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: Linux34p
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: LinuxDebug
   :show-inheritance:
   :members:
   :member-order: alphabetical

OS specific system objects: Darwin (MacOS)
******************************************

.. autoclass:: Macosx
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: Macosx27
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: Macosx34p
   :show-inheritance:
   :members:
   :member-order: alphabetical

Some Python's version specific extra features
*********************************************

.. autoclass:: Python27
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: Python34
   :show-inheritance:
   :members:
   :member-order: alphabetical

Utility Classes
---------------

.. autoclass:: CdContext
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: PythonSimplifiedVersion
   :show-inheritance:
   :members:
   :member-order: alphabetical
