:mod:`vortex.data.geometries` --- Data geometry descritpions
============================================================

.. automodule:: vortex.data.geometries
   :synopsis: Description of some basic data geometries

.. moduleauthor:: The Vortex Team
.. sectionauthor:: The Vortex Team
.. versionadded:: 0.2.2

.. seealso:: :ref:`geo_list`


Package
-------

.. autodata:: __all__


Module interface
----------------

.. autofunction:: get

.. autofunction:: keys

.. autofunction:: values

.. autofunction:: items

.. autofunction:: grep


Pre-defined horizontal geometry attribute as an abstract footprints
-------------------------------------------------------------------

.. autodata:: hgeometry

Pre-defined horizontal geometry attribute as an abstract decorative footprints
------------------------------------------------------------------------------

.. autodata:: hgeometry_deco


Concrete geometry classes
-------------------------

.. autoclass:: GaussGeometry
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: ProjectedGeometry
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: LonlatGeometry
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: CurvlinearGeometry
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: MassifGeometry
   :show-inheritance:
   :members:
   :member-order: alphabetical


Abstract geometry classes
-------------------------

.. autoclass:: Geometry
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: HorizontalGeometry
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: VerticalGeometry
   :show-inheritance:
   :members:
   :member-order: alphabetical

.. autoclass:: UnstructuredGeometry
   :show-inheritance:
   :members:
   :member-order: alphabetical


Currently unused geometry classes
---------------------------------

.. autoclass:: CombinedGeometry
   :show-inheritance:
   :members:
   :member-order: alphabetical


Utility function
----------------

.. autofunction:: load
   