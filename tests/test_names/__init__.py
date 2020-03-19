# -*- coding: utf-8 -*-

r"""
:mod:`test_names` is a Unit-Test facility that creates a large number of
resource's :class:`~vortex.data.handlers.Handler`\s and checks that the
generated URIs (obtained by a call to the :meth:`vortex.data.handlers.Handler.location`
method) are unchanged compared to a reference run. Such
:class:`~vortex.data.handlers.Handler`\s are created based on a footprint
description of the :class:`~vortex.data.resources.Resource` and
:class:`~vortex.data.providers.Provider` objects that one intends to test.

Since Vortex version are supposed to be backward compatible, this unit-test
ensures that there are no changes in time for the various resources and
providers combination. Therefore, it is in the best interest of developers
to add realistic tests for newly created resources.

To get meaningful unit-tests, the idea is to mimic the Olive/DSI
behaviour. Therefore:

  * The usual footprints' defaults are used (date, cutoff, ...);
  * The :func:`footprints.util.expand` function is used when generating the
    :class:`~vortex.data.handlers.Handler` objects (the same way
    :func:`vortex.toolbox.input` uses it);
  * Some pre-defined Genv can be stored in order to tests all the diversity
    of GCO's stores.

This package can be run as a Python's unit-test using nose
(``cd tests; nosetests test_names``). Otherwise, a dedicated command-line
tool is provided (``project/bin/test_names_cli.py``). When new Resource/Provider
pairs are meant to be tested, the ``test_names_cli.py`` command-line utility
allows to generate the reference data that will be used for subsequent checks.

Starting from the Vortex's installation root directory, the configuration files
related to :mod:`test_names` are stored under ``tests/data``:

  * ``tests/data/namestest``: The configuration files were the various
    Resource/Provider pairs to be tested are described. These files are in
    YAML format;
  * ``tests/data/namestest_results``: The YAML files (generated by the
    ``test_names_cli.py`` command-line utility) were the reference results
    are stored for each and every Resource/Provider pair;
  * ``tests/data/namestest_register/genv``: a place where dummy Genv can be
    stored in order to conduct some tests. It is advised not to have a too
    large number of dummy Genv files (it is often enough to use old ones or
    to add entries to existing ones).


Basic Usage
-----------

The ``test_names_cli.py`` utility
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``project/bin/test_names_cli.py`` command-line utility can be used with
both Python2.7 en Python3. Calling ``project/bin/test_names_cli.py -h`` gives
you an help message that summarises all available options.

By default, ``test_names_cli.py`` works on the Vortex code contained in the
same directory path than the ``test_names_cli.py`` utility.

A first step might be to list all of the available configuration files::

    $ python3 project/bin/test_names_cli.py list
    Vortex 1.6.4 loaded ( Monday 16. March 2020, at 16:50:03 )
    # [2020/03/16-16:50:03][bronx.syntax.externalcode][__exit__:0116][WARNING]: The snowtools package is unavailable.
    [...]

    Test files located in "[...]/tests/data/namestest". Here are the available test files:

      * cen/flow.yaml
      [...]
      * nwp/boundaries.yaml
      * nwp/clim.yaml
      * nwp/consts/clim_constants.yaml
      [...]

    Vortex 1.6.4 completed ( Monday 16. March 2020, at 16:50:04 )

(Some harmless warning may appear because of the lack of some external
packages, this is fine.)

The ``test_names_cli.py`` standard behaviour is to work on all available
configuration files. For example, this will check that the current Vortex
code gives appropriate results (compared to the references stored in
``tests/data/namestest_results``)::

    $ python3 project/bin/test_names_cli.py check
    Vortex 1.6.4 loaded ( Monday 16. March 2020, at 16:56:37 )
    # [2020/03/16-16:56:37][bronx.syntax.externalcode][__exit__:0116][WARNING]: The snowtools package is unavailable.
    [...]

    [SUCCESS] ( 247 RH tested) cen/flow.yaml
    [...]
    [SUCCESS] (  16 RH tested) nwp/boundaries.yaml
    [SUCCESS] (  60 RH tested) nwp/clim.yaml
    [SUCCESS] (  34 RH tested) nwp/consts/clim_constants.yaml
    [...]
    Everything went fine (a total of 5851 resource Handlers were tested).

    Vortex 1.6.4 completed ( Monday 16. March 2020, at 16:57:04 )

This behaviour can be changed using the ``--only`` or ``--regex``
command line options::

    $ python3 project/bin/test_names_cli.py --only=nwp/boundaries.yaml check
    Vortex 1.6.4 loaded ( Monday 16. March 2020, at 17:00:47 )
    # [2020/03/16-17:00:47][bronx.syntax.externalcode][__exit__:0116][WARNING]: The snowtools package is unavailable.
    [...]
    [SUCCESS] nwp/boundaries.yaml
    Vortex 1.6.4 completed ( Monday 16. March 2020, at 17:00:48 )
    $ python3 project/bin/test_names_cli.py --regex='nwp/(eps|eda)' check
    Vortex 1.6.4 loaded ( Monday 16. March 2020, at 17:03:09 )
    # [2020/03/16-17:03:09][bronx.syntax.externalcode][__exit__:0116][WARNING]: The snowtools package is unavailable.
    [...]

    [SUCCESS] (  36 RH tested) nwp/eda.yaml
    [SUCCESS] (   2 RH tested) nwp/eps_aromepe.yaml
    [SUCCESS] (  26 RH tested) nwp/eps_pearp.yaml

    Everything went fine (a total of 64 resource Handlers were tested).

    Vortex 1.6.4 completed ( Monday 16. March 2020, at 17:03:10 )

If some test_names' configuration files were modified (for example to add a new
test on a few Resource/Provider pairs), the reference files can be generated
as follows::

    $ python3 project/bin/test_names_cli.py dump
    Vortex 1.6.4 loaded ( Monday 16. March 2020, at 17:10:10 )
    # [2020/03/16-17:10:11][bronx.syntax.externalcode][__exit__:0116][WARNING]: The snowtools package is unavailable.
    [...]

    [SUCCESS] ( 247 RH tested) cen/flow.yaml
    [...]
    [SUCCESS] (  16 RH tested) nwp/boundaries.yaml
    [SUCCESS] (  60 RH tested) nwp/clim.yaml
    [SUCCESS] (  34 RH tested) nwp/consts/clim_constants.yaml
    [...]
    Everything went fine (a total of 5851 resource Handlers were tested).

    Vortex 1.6.4 completed ( Monday 16. March 2020, at 17:10:36 )

This will re-generate all of the reference files: this is costly but harmless
since, if no change are made in the configuration files, the reference files
should remain identical (this can be verified using Git). Consequently,
only modified or created reference files should be affected by changes made in
the configuration files by the developers.

However, it is also possible to re-generate the reference file for only one
configuration file::

    $ python3 project/bin/test_names_cli.py --only=nwp/eda.yaml dump
    Vortex 1.6.4 loaded ( Monday 16. March 2020, at 17:15:34 )
    # [2020/03/16-17:15:34][bronx.syntax.externalcode][__exit__:0116][WARNING]: The snowtools package is unavailable.
    [...]

    [SUCCESS] (  36 RH tested) nwp/eda.yaml

    Everything went fine (a total of 36 resource Handlers were tested).

    Vortex 1.6.4 completed ( Monday 16. March 2020, at 17:15:35 )

Some other "actions" are also available with the ``test_names_cli.py`` utility:

    * ``project/bin/test_names_cli.py load`` will only read the configuration
      files and create resource's :class:`~vortex.data.handlers.Handler`\ s.
      This is a way to check that the syntax of the YAML configuration file
      is fine and that it is possible to build the
      :class:`~vortex.data.resources.Resource` and
      :class:`~vortex.data.providers.Provider` based on this configuration files.
    * ``project/bin/test_names_cli.py compute`` will load the configuration
      files (see above) and create the URIs (by a call to the
      :meth:`vortex.data.handlers.Handler.location` method). This is a way to
      check that the Vortex code technically works but it does not guaranty
      that the result is fine.

Via the nosetests command
^^^^^^^^^^^^^^^^^^^^^^^^^

Simply call ``nosetests`` with the :mod:`test_names` package path on the
command-line::

    $ cd tests
    $ nosetests3 ./test_names
    .
    ----------------------------------------------------------------------
    Ran 1 test in 9.175s

    OK

Performances
^^^^^^^^^^^^

Since the number of tested resource's :class:`~vortex.data.handlers.Handler`\s
is quite high, the ``test_name_cli.py`` utility and the unit-tests package can
be quite slow.

With Python3 (only), a good level of parallelism was introduced using the
:mod:`concurrent.futures` standard package:

  * By default, the number of parallel tasks to be used is equal to the number
    of CPUs available on the system;
  * Otherwise, the ``VORTEX_TEST_NAMES_NTASKS`` can be exported in order to
    set this number of parallel tasks;
  * With the ``test_names_cli.py`` utility, the ``--ntasks`` command line
    option can also be used.


Description of the YAML configuration files
-------------------------------------------

Just keep in mind that the idea of the :mod:`test_names` unit-tests package is
to test a large number of resource's :class:`~vortex.data.handlers.Handler`\s.
Such resource's :class:`~vortex.data.handlers.Handler`\s need to be defined
by developers in configuration files.

A configuration file for the :mod:`test_names` unit-tests package must be
placed in ``tests/data/namestest`` (the subdirectory structure below
``namestest`` directory is arbitrary and should be used by the developers
to properly organise tests).

A configuration file, that must be a valid YAML file, looks like:

.. code:: yaml

    default:
        style: olive
        sets:
            # A first defaults description:
            -   date: 2018010100
                geometry: antigsp16km
                cutoff: production
                model: aladin
                namespace: vortex.multi.fr
                vapp: arome
                vconf: antilles
            # A second defaults description:
            -   date: 2018010100
                geometry:
                    - macc01
                    - glob22
                cutoff:
                    - assim
                    - production
                model: mocage
                namespace: vortex.multi.fr
                vapp: mocage
                vconf: camsfcst

    todo:
        # Description of a first ensemble of tests
        -   commons:
                kind: boundary
                nativefmt: fa
                block: coupling
                experiment: abcd
                source_app: ifs
                source_conf: determ
                namespace:
                    - olive.multi.fr
                    - vortex.multi.fr
            tests:
                # A first test
                - source_conf: eps
                  term: 0
                # A second test
                - term:
                    - 0
                    - 24
        # Description of a second ensemble of tests
        -   commons:
                kind: fake
            tests:
                - term: 1

For each of the test files, at least one set of footprints' default values
needs to be provided (in the ``default`` section):

    * The type of the defaults can be provided using the ``style`` entry.
      It describes how default values are dealt with. For example, in
      ``olive`` style, ``date`` and ``geometry`` entries are transformed
      in valid :class:`~bronx.stdtypes.date.Date` and
      :class:`~vortex.data.geometries.Geometry` objects prior to being used as
      footprints' default. Currently ``olive`` is the only available style
      (NB: it is also relevant for jobs launched with ``mkjob``).
    * Sets of defaults are provided as a list using the ``sets`` entry. All
      of the resource's :class:`~vortex.data.handlers.Handler`\s defined
      in the ``todo`` section (see explanations below) will be tested with
      each of the defaults sets.
    * During defaults definition, footprints' expansion mechanism can be
      used (see :meth:`footprints.util.expand`). In the example above, for
      the second defaults description, the expansion mechanism is used for the
      ``geometry`` and ``cutoff`` defaults. Instead of using the expansion
      mechanism, 4 defaults sets might have been created (e.g. for ``macc01``
      + ``assim``, ``macc01`` + ``production``, ``glob22`` + ``assim`` and
      ``glob22`` + ``production``): This would be equivalent but a lot more
      painful.

The second part of the configuration file is dedicated to the description of
tested resource's :class:`~vortex.data.handlers.Handler`\s (via the ``todo``
section):

    * The ``todo`` section is a list of one or several ensemble of tests.
      Optionally, a given ensemble of tests share some common resource's
      Handlers attributes (defined in the ``commons`` section). The various
      resource's Handlers to be tested are described as a list in the
      ``tests`` section.
    * Please note that the attributes listed in the ``commons`` section are not
      footprints' default values. They are simply merged with the
      one listed in the ``tests`` section. If an attribute is defined
      twice, the one from the ``tests`` section takes precedence.
    * Both in the ``commons`` and ``tests`` sections, the footprints'
      expansion mechanism can be used (see :meth:`footprints.util.expand`).

:note: The footprints' expansion mechanism makes it very easy to generate a
       large number of resource's :class:`~vortex.data.handlers.Handler`\s:
       use this mechanism with care since the test duration directly depends
       on the number of tested resource's
       :class:`~vortex.data.handlers.Handler`\s.


Some technical details on the :mod:`test_names` package implementation
----------------------------------------------------------------------

The various configuration files can be accessed using the
:mod:`test_names.discover` module and his :data:`test_names.discover.all_tests`
object.

The content of a single configuration file is hold in a
:class:`test_names.core.TestDriver` object. The reference data associated with
a given configuration file are also managed by the
:class:`~test_names.core.TestDriver` object.

The set of defaults (defined in the ``default`` section of the configuration
file) are stored directly in the :class:`~test_names.core.TestDriver` object.
However, ensembles of tests (defined in the the ``todo`` section of the
configuration files) are stored as a list of
:class:`test_names.core.TestsStack` objects.

The :class:`~test_names.core.TestsStack` objects can be seen as sets of
:class:`test_names.core.SingleTest` objects that represents each of the
tests defined in the ``tests`` sections of the configuration file.

Test results (the URIs generated based on the resource's
:class:`~vortex.data.handlers.Handler`\s defined in the configuration file)
are stored within the :class:`~test_names.core.SingleTest` objects in a
:class:`test_names.core.TestResults` object.

Reference data files are generated using a dedicated YAML dumper object that is
fit to serialise all of the previously mentioned classes. Therefore, a
reference data file is a YAML dump of a :class:`~test_names.core.TestDriver`
object.
"""

from __future__ import print_function, division, absolute_import, unicode_literals
