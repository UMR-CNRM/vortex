=========================================
The `oper` and `dble` special experiments
=========================================

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
modify the base behavior of functions :py:func:`vortex.input` and
:py:func:`vortex.output`.  This behaviour depends on whether or not a
:doc:`remote data tree <remote-data-trees>` is used.

Local data tree
===============

The behaviour associated to ``"oper"`` and ``"dble"`` experiments is
special only in the fact that the corresponding directory name is
capitalised:

.. code:: python

    handler = vortex.input(
        vapp="arome",
        vconf="ifsfr",
        kind='analysis',
        # ...
        cache = True,
        archive = False,
    )
    handler.locate()

    /home/user/vortex.d/arome/ifsfr/DBLE/.../.../analysis.atm-arome.franmg-01km30.grib

Remote data tree
================


