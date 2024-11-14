==============
Explicit paths
==============


Vortex makes it possible to fetch (write) data files from (to)
locations outside of the vortex data tree, whether it is local or
remote.

Fetching (writing) from (to) an explicit path
---------------------------------------------

This is achieved by specifying an optional extra argument ``remote``,
``to calls to ~vortex.input`` or ``vortex.output``.  The value must be a
string containing the path to the target or source data file.  The
path must either be absolute or relative to the user's home directory.

Passing the ``remote`` argument replaces passing arguments specifying
the location of the source (target) data file within the vortex data
tree, such as ``block``, ``experiment``, ``vapp`` or ``vconf``.

.. code:: python

    import vortex as vtx

    handler = vtx.input(
        kind="analysis",
        date="2024082600",
        model="arpege",
        cutoff="production",
        filling="atm",
        remote="/home/user/data/analysis.fa"
        local="ICMSHFCSTINIT",
    )

Fetching (writing) from (to) an explicit path on a remote machine
-----------------------------------------------------------------

The two optional arguments ``hostname`` and ``tube`` can be used to
specify the address and protocol of a remote machine:

``address``
