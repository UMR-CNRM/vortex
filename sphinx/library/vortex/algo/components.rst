:mod:`vortex.algo.components` --- Base class for executables modes
==================================================================

.. automodule:: vortex.algo.components
   :synopsis: Local receptacle for vortex resources

.. moduleauthor:: The Vortex Team
.. sectionauthor:: The Vortex Team
.. versionadded:: 0.2.1


Package
-------

.. autodata:: __all__

Exceptions
----------

.. autoclass:: AlgoComponentError
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: AlgoComponentAssertionError
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: DelayedAlgoComponentError
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: ParallelInconsistencyAlgoComponentError
   :show-inheritance:
   :members:
   :member-order: alphabetical

Base classes
------------

Base class and its metaclass
****************************

.. autoclass:: AlgoComponent
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: AlgoComponentMeta
   :show-inheritance:
   :members:
   :member-order: alphabetical

Base Mixin class
****************

.. autoclass:: AlgoComponentDecoMixin
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: AlgoComponentMpiDecoMixin
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autofunction:: algo_component_deco_mixin_autodoc

Abstract classes with some refinements on binaries verification
***************************************************************

.. autoclass:: ExecutableAlgoComponent
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: xExecutableAlgoComponent
   :show-inheritance:
   :members:
   :member-order: alphabetical

Ready to use AlgoComponents (for basic needs)
---------------------------------------------

.. autoclass:: BlindRun
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: Expresso
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: Parallel
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: PythonFunction
   :show-inheritance:
   :members:
   :member-order: alphabetical

Base classes for AlgoComponents implementing task parallelism (using taylorism)
-------------------------------------------------------------------------------

.. autoclass:: TaylorRun
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: ParaBlindRun
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: ParaExpresso
   :show-inheritance:
   :members:
   :member-order: alphabetical

Usefull generic mixins
----------------------

.. autoclass:: ParallelIoServerMixin
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: ParallelOpenPalmMixin
   :show-inheritance:
   :members:
   :member-order: alphabetical
