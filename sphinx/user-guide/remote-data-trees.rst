=================
Remote data trees
=================


By default, vortex fetches and write data from and from a *local* data
tree, see :doc:`data-layout`.  It is however possible to configure access to a
remote data tree usinf the FTP protocol, for instance acting as a data archive.

Remote data tree configuration
------------------------------

In the vortex configuration file (:doc:`configuration`), specify a section
``storage`` defining the following key/value pairs:


.. code:: toml

    [storage]
    address = "example.meteo.fr"
    protocol = "ftp"
    rootdir = "/path/to/data/tree/root"
    op_rootdir = "/path/to/oper/data/tree/root"

``address``
    the network address of the server hosting the remote data tree.

``protocol``
   the protocol with which to communicate with the server hosting the remote data tree.

``rootdir``
    Path to the root of the vortex data tree on the remote
    server's filesystem.

``op_rootdir``
    Path to the root of the operational vortex data tree
    on the remote server's filesystem. See <todolink>.

``export_mapping``
    <TODO>

Using remote data trees
-----------------------

If a remote data tree is configured, a call to ``handlers.Handler.get``
will first try to fetch the file from the local data tree.  If the
file cannot be found locally, an attempt will be made to fetch the
file from the remote data tree instead.

If the file is successfully fetched from the remot data tree, then the
file is *also* written in the local data tree, so that a later
retrieval will not have to access the remote server.

In this mode of operation, the *local* data tree behaves like a cache
space with respect to the *remote* data tree.

If a remote data tree is configured, a call to ``handlers.Handler.put``
will both write to the local data tree and the remote data tree.

Modifying local and remote data trees access patterns
-----------------------------------------------------

The above section describes the default access pattern whenever a
remote data tree is configured.  However, the access pattern can be
alterned by specifying optional arguments ``cache`` and/or
``archive`` to functions ``vortex.input`` and ``vortex.output``.

``cache``
    A boolean indicating whether or not a ``get`` (``put``) call on
    the resulting handler(s) should fetch (write) from (to) the local
    data tree.

``archive``
    A boolean indicating whether or not a ``get`` (``put``) call on
    the resulting handler(s) should fetch (write) from (to) the remote
    data tree.

Examples
~~~~~~~~

The following snippet illustrates only writing to the remote data
tree:

.. code:: python

    import vortex as vtx

    handlers = vtx.output(
        kind="historic",
        block="forecast",
        # ...
        term = [0, 1, 2, 3],
        local="ICMSHFCST+[term::fmthm]",
        cache=False,  # Disable local data tree
    )

    for hander in handlers:
        # Do not write to local data tree, only
        # to remote data tree
        handler.put()

The following snippet illustrates only fetching from the local data
tree:

.. code:: python

    import vortex as vtx

    handler = vtx.input(
        kind="analysis"
        block="4dupd2",
        # ...
        local="ICMSHFCSTINIT",
        archive=False,  # Disable remote data tree
    )

    # Do not write to remote data tree, only
    # to local data tree
    handler.get()
