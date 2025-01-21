========================================
Extending *vortex* using plugin packages
========================================

The *vortex* plugin system makes it easy for users to define and
redistribute their own resources and task classes.

The ``vortex`` and ``vortex.nwp`` packages ship with a number of
classes that model data, programs and computational tasks that
typically make up most Numerical Weather Prediction pipelines.  We
expect use-cases, however, for which none of the provided classes
apply.  These could arise from novel research or using vortex within a
domain for which it was not originally designed for.

You can implement the appropriate classes fitting your use case by
extending one or several classes present in the ``vortex`` or
``vortex.nwp`` packages.  In order to make these classes available to
functions like :py:func:`vortex.input`, :py:func:`vortex.executable`
or :py:func:`vortex.task`, the corresponding Python modules must be
installed as part of a package that declares the ``vtx`` entry point
in its metadata.

Example
-------

Let's say we wish to define the following ressource class and make it
available alongside any other *vortex* ressources. By *make it
available*, we mean that, given the appropriate collection of
arguments, functions of the top-level :py:mod:`vortex` module such as
``input`` or ``output`` will be able to instantiate the class.

.. code:: python

    # new.py

    from vortex.data.flow import FlowResource
    
    class NewResource(FlowResource):
        _footprint = [
            {
                "kind": {
                    "values": ["observations"]
                },
                "nativefmt": {
                    "values": ["json"]
                },
                "model": {
                    "values": ["arpege"]
                },
            }
        ]
    
        @property
        def realkind(self):
            return "my-new-ressource"

Assuming the `new.py` module is installed, importing it will make the
`NewResource` class available:

.. code:: python

    >>> from new import NewResource
    >>> rh = vortex.input(
    ...    kind="newressource", model="arpege", cutoff="assim"
    ...    nativefmt="json", experiment="dummy-xp", local="local-filename"
    ... )[0]
    >>> type(rh.resource)
    <class 'new.NewResource'>

Having to manually import modules so that they are available through
the top level :py:mod:`vortex` module functions is error-prone.
It can also be awkward to import one or more modules for the sole
purpose of making a few classes available, with the modules object
themselves not being used in the script. For these reasons, we
recommend that you group your modules into an plugin package that will
be automatically discovered when importing *vortex*.

Creating a *vortex* plugin package
----------------------------------

If you group your module(s) into a Python package that declare the
``vtx`` entry point as part of its metadata, a ``import vortex``
statement will discover and load the modules it ships.

.. seealso::

   This guide assumes that you are familiar with writing Python
   package metadata.  If this is not the case, see the `Configuring
   metadata
   <https://packaging.python.org/en/latest/tutorials/packaging-projects/#configuring-metadata>`_
   section in the Python Packaging User Guide chapter on `Packaging
   Python Projects
   <https://packaging.python.org/en/latest/tutorials/packaging-projects/#packaging-python-projects>`_.

Continuing on the previous example, here is how it works. We now
assume that the ``new.py`` module is part of a package with the
following directory structure:

.. code::

    new-resource-package/
        pyproject.toml
        src/
            vortex_newresource/
                 new.py
                 __init__.py

The package's ``__init__.py`` module is responsible for making
``new`` available under the ``vortex_newresource`` namespace:

.. code:: python

    # src/newresource/__init__.py

    # Use a redundant import alias to instruct linters (e.g. Ruff) that this
    # is just a re-export of "new" as part of the package's public interface.
    from . import new as new


In other words, importing the ``vortex_newresource`` package (``import
vortex_newresource``) will make available the ``new`` module as
``newresource.new``.

Next, the package metadata must declare the ``vtx`` entry point:

.. code:: toml

    # pyproject.toml
	  
    [project.entry-points.vtx]
    newresource = "vortex_newresource"

.. seealso::

   See `Entry points specification <https://packaging.python.org/en/latest/specifications/entry-points/#entry-points>`_ in the Python Packaging User Guide for more information about declaring entry points.

After installing the plugin package, the ``vortex_newresource.new``
module will be automatically discovered and loaded when importing
*vortex*:

.. code:: python

   >>> import vortex
   Loaded plugin newresource
   Vortex 2.0.0b1 loaded
   >>> rh = vortex.input(
   ...    kind="newressource", model="arpege", cutoff="assim"
   ...    nativefmt="json", experiment="dummy-xp", local="local-filename"
   ... )[0]
   >>> type(rh.resource)
   <class 'vortex_newresource.new.NewResource'>

Note that importing the ``vortex_newresource.new`` explicitly was never
required.
