==========
Vortex CLI
==========

Vortex comes with the ``vtx`` CLI tool to execute a section. The CLI takes a path to a
yaml config file that describes the arguments to pass to a section (``toolbox.input``,
``toolbox.output``, ``toolbox.rload``).

The config can also be passed via stdin if the path is not provided.

Example
^^^^^^^

.. code:: bash

    cat < EOF | vtx
    section: input
    args:
      now: true
      local: file.grib
      model: arpege
      vapp: arpege
      vconf: 4dvarfr
      experiment: OPER
      geometry: glob025
      kind: gridpoint
      nativefmt: grib
      cutoff: prod
      date: 2026-01-01
      term: 0
      namespace: vortex.archive.fr
      block: forecast
      origin: historic
    EOF


Addons
^^^^^^

Addons can be loaded by listing them in the config:

.. code:: bash

    cat < EOF | vtx
    section: input
    addons:
      - kind: grib
      - kind: ectrans
    args:
      now: true
      local: file.grib
      model: arpege
      vapp: arpege
      vconf: 4dvarfr
      experiment: OPER
      geometry: glob025
      kind: gridpoint
      nativefmt: grib
      cutoff: prod
      date: 2026-01-01
      term: 0
      namespace: vortex.archive.fr
      block: forecast
      origin: historic
      storetube: ectrans
    EOF
