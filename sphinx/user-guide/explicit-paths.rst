=====================
Using arbitrary paths
=====================


Vortex makes it possible to fetch (write) data files from (to)
locations outside of the vortex data tree, whether it is local or
remote.

Local paths
-----------

You can specify an arbitrary path to write (read) a resource from (to)
by passing an optional extra argument ``remote`` to calls to
:py:func:`vortex.input` or :py:func:`vortex.output`.  The value must
be a string containing the path to the target or source data file.
The path must either be absolute or relative to the user's home
directory.

Passing the ``remote`` argument replaces passing arguments specifying
the location of the source (target) data file within the vortex data
tree, such as ``block``, ``experiment``, ``vapp`` or ``vconf``.

The following snippet would cause the creation of a file named
``ICMSHFCSTINIT`` linking to file ``/home/user/data/analysis.fa``:

.. code:: python

    import vortex as vtx

    vtx.input(
        kind="analysis",
        date="2024082600",
        model="arpege",
        cutoff="production",
        filling="atm",
        remote="/home/user/data/analysis.fa"
        local="ICMSHFCSTINIT",
    ).get()

Remote paths
------------

The two optional arguments ``hostname`` and ``tube`` can be used to
specify the address and protocol of a remote machine:

``hostname``
    A string containing the address of the remote machine

``tube``
    Specifies the protocol used to access the remote
    machine. Allowed values are ``"scp"`` for the SSH protocol and
    ``"ftp"`` for FTP.

For instance:

.. code:: python

    handler = vtx.input(
        kind="analysis",
        date="2024082600",
        # ...
        remote="/home/user/data/analysis.fa"
        hostname="hendrix.meteo.fr",
        tube="ftp",
    )

.. important::

   The requests are made with the current user's account.
