=============================================
The ``oper`` and ``dble`` special experiments
=============================================

The description of the vortex data tree provided in :doc:`data-layout`
mentions that nodes at the experiment identifier level can have
arbitrary names.  In practice, it means you are free to pass any
string value to the ``experiment`` argument of functions
:py:func:`vortex.input` and :py:func:`vortex.output`:

.. code:: python

    vortex.input(
        # ...
        experiment="my-experiment",
        # ...
    )

The values ``"oper"`` and ``"dble"``, however, are special cases that
enable fetching data files from an additional **local** data tree in
case they are not found in the default local data tree.

.. note::

   The additional data tree associated with special experiments
   identifiers ``"oper"`` and ``"dble"`` can only be *fetched* from.  In
   other words, a call to ``put`` on a ``Handler`` object returned by
   :py:func:`vortex.output` will *not* write the file in the
   additional directory.

   This is mostly because the use of an additional data tree was
   designed as a cache space for fetching data files produced by NWP
   operational runs.

This behavior is enabled whenever a configuration entry ``op_rootdir``
is set within the ``data-tree`` section of the configuration.  Note
that, similarly to the defaut data tree, this extra data tree is *not*
accessed whenever ``cache=False`` is passed to :py:func:`vortex.input`
or :py:func:`vortex.output`.

Example
========

Assume the following directory trees::

    /home/user/vortex.d/arome/ifsfr/DBLE/.../
         file1
         file2

    /vortex/cache/arome/ifsfr/DBLE/.../
         file1
         file2
         file3

As well as the following configuration:

.. code:: toml

   [data-tree]
   op_rootdir = "/vortex/cache"

Suppose that a call to :py:func:`vortex.input`:

.. code:: python

   handler = vortex.input(
       # ...
       experiment="dble",
       # ...
   )

results to a handler on node ``arome/ifsfr/DBLE/.../file1`` of the
data tree.  Then a call to ``handler.get`` will fetch the file
``file1`` from the default local data tree ``/home/user/vortex.d``.
However, all call to ``get`` on a handler on node
``arome/ifsfr/DBLE/.../file3`` would fetch the file ``file3`` from the
additional local data tree ``/vortex/cache``.
