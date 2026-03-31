.. _vtx-command:

===================
The ``vtx`` command
===================

Vortex comes with a command line program ``vtx`` that fetches or
stores files from/into the local and/or remote data tree.

.. note::

   The `vtx` program is in fact a thin wrapper around the
   :py:func:`vortex.input` and :py:func:`vortex.output` functions.

Usage
-----

.. code:: bash

   vtx [-h] [--addon [ADDON ...]] [--log-level LOG_LEVEL] {get,put} [path]

The ``vtx`` command accepts two subcommands:

- ``get``: fetch a resource (runs :py:func:`vortex.input`).
- ``put``: store a resource (runs :py:func:`vortex.output`).

The subcommand takes an optional path to a YAML config file.
If the path is not provided, the config is read from stdin.

Options
-------

``-h``, ``--help``
^^^^^^^^^^^^^^^^^^

Show help message and exit

``-a``, ``--addon``
^^^^^^^^^^^^^^^^^^^

Addon to load. Multiple addons can be provided

``--log-level``
^^^^^^^^^^^^^^^

Logging level

Example
-------

From a YAML file:

.. code:: bash

    vtx get config.yaml

Or from standard input directly:

.. code:: bash

    cat < EOF | vtx get
    args:
      local: "file.grib"
      model: "arpege"
      vapp: "arpege"
      vconf: "4dvarfr"
      experiment: "OPER"
      geometry: "glob025"
      kind: "gridpoint"
      nativefmt: "grib"
      cutoff: "prod"
      date: "202601010600"
      term: 0
      namespace: "vortex.archive.fr"
      block: "forecast"
      origin: "historic"
    EOF


Addons
^^^^^^

Addons can be loaded by listing them in the configuration:

.. code:: bash

    cat < EOF | vtx get
    addons:
      - kind: grib
      - kind: ectrans
    args:
      local: "file.grib"
      model: "arpege"
      vapp: "arpege"
      vconf: "4dvarfr"
      experiment: "OPER"
      geometry: "glob025"
      kind: "gridpoint"
      nativefmt: "grib"
      cutoff: "prod"
      date: "202601010600"
      term: 0
      namespace: "vortex.archive.fr"
      block: "forecast"
      origin: "historic"
      storetube: "ectrans"
    EOF
