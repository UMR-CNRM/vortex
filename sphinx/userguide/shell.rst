.. _shell-interface:

***************
Shell Interface
***************


The VORTEX fonctionnalities are partially accessible from shell interface
as raw command lines.
The present documentation explains the very simple grammar used
and the list of commands in alphabetical and thematic order.

===================
Command line syntax
===================

The vortex command
==================

The VORTEX shell actions are invoqued though a single command named :program:`vortex`, which is
located in the :file:`bin` directory of the current installation.
A specific message warns you that the coprocess has been started:

.. code-block:: console

  % vortex
  New vortex shell facility [21177] for process [26651] and tag [26651]
  Ok

The first invocation will launch in the backgroud a python/vortex interpreter
through the :command:`vortexshcmd.py` application also located in the same :file:`bin` directory.

Note that the first vortex invocation could be a full command as well:

.. code-block:: console

  % vortex user
  New vortex shell facility [21177] for process [26651] and tag [26651]
  droopy

Any subsequent empty call to :command:`vortex` will only prompt an acquiescence message:

.. code-block:: console

  % vortex
  Ok

A session is closed through the :command:`exit` subcommand:

.. code-block:: console

  % vortex exit
  Bye 26651...


FIFO tag session
================

One can specifies a tag to identify the vortex session to talk to.
By default, we have seen that this tag is set to the current process id.
However a specific value could be given through the :envvar:`FIFOTAG` environment variable.

.. code-block:: console

  % export FIFOTAG=foo
  % vortex user
  New vortex shell facility [21177] for process [26651] and tag [foo]
  droopy
  % vortex exit
  Bye foo...

In fact, any command could be reoriented through the :option:`-t` command line argument.

.. code-block:: console

  % vortex -t foo exit
  Bye foo...


The key=value paradigm
======================

Arguments to a subcommand are provided through a sequence of keys/values:

.. code-block:: console

  % vortex subcmd [k1=v1] ... [kn=vn] [set=result]

The :option:`set` key is the standard way to store the result of the current command.
One should distinguish between the result of a command as an object, which could
be stored and the result of a command as a string displayed at the command line interface.

For example, the output of the :command:`session` subcommand
is the tag name of the current session:

.. code-block:: console

  % vortex session
  root

But the result of this command is the session object itself:

.. code-block:: console

  % vortex last
  <vortex.sessions.Ticket object at 0x25da5d0>


Internal variables
==================

We have seen that result of commands could be stored through the :option:`set` key.
By default some pseudo-variables are already defined:

.. code-block:: console

  % vortex vars
  fdir: /home/droopy/.vortexrc
  last: None
  ppid: 17579
  rfifo: /home/droopy/.vortexrc/fifo.r17579
  wfifo: /home/droopy/.vortexrc/fifo.w17579

As soon as command returns a valid value, the ``last`` variables is filled:

.. code-block:: console

  % vortex user
  droopy
  % vortex vars
  fdir: /home/droopy/.vortexrc
  last: droopy
  ppid: 17579
  rfifo: /home/droopy/.vortexrc/fifo.r17579
  wfifo: /home/droopy/.vortexrc/fifo.w17579

The special :command:`last` subcommand could be used to recall the last value:

.. code-block:: console

  % vortex last
  droopy

Which is slightly different from the :command:`echo` subcommand:

.. code-block:: console

  % vortex echo last
  last: droopy

All the non default internal variables
could be remove through the :command:`clear` subcommand:

.. code-block:: console

  % vortex clear
  Internal store is clear


=====================
Review of subcommands
=====================

:command:`apply`

  Get ``attr`` or apply ``method`` on the ``with`` object.
  Return this value.

  .. code-block:: console

    % vortex session set=s
    root
    % vortex apply with=s attr=started
    2012-07-19 17:56:03.142735
    % vortex apply with=s method=duration
    0:11:32.814350


:command:`attributes`

  Print the attributes contents of the specified elements.
        Return ``None``.

  .. code-block:: console

    % vortex container file=foo set=ff
    <vortex.data.containers.File object at 0x1bc64d0>
    % vortex attributes obj=ff
    obj: ['file']


:command:`call`

  Display and return the output of the call on objects provided,
  as long as they are callable.

  .. code-block:: console

    % vortex containers set=c
    <class 'vortex.data.containers.File'>
    <class 'vortex.data.containers.InCore'>
    <class 'vortex.data.containers.MayFly'>
    % vortex call from=c
    [<class 'vortex.data.containers.MayFly'>, <class 'vortex.data.containers.InCore'>, <class 'vortex.data.containers.File'>]


:command:`catalogs`

  Return current entries in catalogs table.
  At the very beginning only already internally used catalogs are available.

  .. code-block:: console

    % vortex catalogs
    ['gloves', 'systems']

  But as soon as you request any other catalog, the list extends:


  .. code-block:: console

    % vortex resources
    <class 'vortex.data.executables.BlackBox'>
    <class 'vortex.data.executables.Script'>
    % vortex catalogs
    ['gloves', 'systems', 'resources']


:command:`component`

  Load an algo component object according to description.
  Return the object itself.
  See also :mod:`vortex.algo.components`.

  .. code-block:: console

    % vortex component engine=parallel kind=forecast
    <common.algo.forecasts.Forecast object at 0x263b350>

:command:`components`

  Display algo components catalog contents.
  Return the catalog itself.

  .. code-block:: console

    % vortex components
    <class 'common.algo.forecasts.DFIForecast'>
    <class 'common.algo.forecasts.Forecast'>
    <class 'common.algo.forecasts.LAMForecast'>
    <class 'vortex.algo.components.BlindRun'>
    <class 'vortex.algo.components.Expresso'>
    <class 'vortex.algo.components.Parallel'>
    % vortex last
    <vortex.algo.components.AlgoComponentsCatalog object at 0x2736f90>


:command:`container`

  Load a container object according to description.
  Return the object itself.
  See also :mod:`vortex.data.containers`.

  .. code-block:: console

    % vortex container file=foo set=ffoo
    <vortex.data.containers.File object at 0x263b5d0>
    % vortex apply with=ffoo method=realkind
    file


:command:`containers`

  Display containers catalog contents.
  Return the catalog itself.

  .. code-block:: console

    % vortex containers
    <class 'vortex.data.containers.File'>
    <class 'vortex.data.containers.InCore'>
    <class 'vortex.data.containers.MayFly'>

:command:`daemons`

  Display the list of current active vortex dispatchers.
  Return this list.

  .. code-block:: console

    % vortex daemons
    USER             FIFOTAG          FIFODIR
    droopy           26651            /home/droopy/.vortexrc
    droopy           foo              /home/droopy/.vortexrc
    % vortex last
    [('droopy', '26651', '/home/droopy/.vortexrc'), ('droopy', 'foo', '/home/droopy/.vortexrc')]


:command:`dblput`

  Perform a "double" put : the first one is a true "physical" put,
  the second one is an hard link to the location given by the ``dblp`` provider.
  Therefore a valid ``dblp`` parameter is mandatory.
  Return the resource handler.

  .. code-block:: console

    % vortex envfp date=2012072018 model=arpege cutoff=production
    {'DATE': '2012072018', 'CUTOFF': 'production', 'MODEL': 'arpege'}
    % vortex spectral set=geo
    <vortex.data.geometries.SpectralGeometry object at 0xc6a490>
    % vortex provider remote=$HOME/tmp/doublon set=dbsto
    <vortex.data.providers.Remote object at 0xc90c10>
    % vortex dblput geometry=geo kind=analysis experiment=A001 block=canari namespace=vortex.cache.fr file=analysis.last dblp=dbsto
    /home/droopy/tmp/vortex/play/sandbox/A001/20120720H1800P/canari/analysis.full-arpege.tl798-c24.fa
      -> /home/droopy/tmp/doublon

:command:`default`

  Print / Return the actual arguments as a python dictionary.

  .. code-block:: console

    % vortex foo=2
    {'foo': '2'}


:command:`echo`

  Print a string version of the specified elements.
  Return ``None``.

  .. code-block:: console

    % vortex echo rfifo wfifo
    rfifo: /home/droopy/.vortexrc/fifo.r17579
    wfifo: /home/droopy/.vortexrc/fifo.w17579
    % vortex echo value=2
    value: 2

:command:`env`

  Print environment associated to current session.
  Return current tied environment.

  .. code-block:: console

    % vortex env
    <vortex.tools.env.Environment object at 0x1a52390>
    % vortex env dump=true
    BROWSER="firefox"
    BUFR_TABLES="/opt/libemos/bufrtables/"
    CANBERRA_DRIVER="pulse"
    CDPATH=".:..:/home/droopy"
    COLORTERM="gnome-terminal"
    ...
    % vortex last
    <vortex.tools.env.Environment object at 0x1a52390>

:command:`envfp`

  Set and print the current default footprint values.
  Result current ``fpenv`` object.

  .. code-block:: console

    % vortex envfp
    {}
    % vortex envfp model=arpege date=2012071900
    {'DATE': '2012071900', 'MODEL': 'arpege'}


:command:`get`

  Perform a :func:`vortex.toolbox.rget` call with current attributes.
  Return the resource handler.

  .. code-block:: console

    % vortex envfp
    {'DATE': '2012072218', 'CUTOFF': 'assim', 'MODEL': 'arpege'}
    % vortex spectral set=geo
    <vortex.data.geometries.SpectralGeometry object at 0x150b390>
    % vortex get geometry=geo kind=analysis suite=oper file=analysis.last set=loc
    get: 1
    % ls -l
    total 1430020
    -rw-r--r-- 1 droopy tex 1464336384 2012-07-23 13:35 analysis.last
    % vortex echo loc
    loc: [<vortex.data.handlers.Handler object at 0x1f480d0>]

:command:`glove`

  Display current glove id.
  Return the glove itself.

  .. code-block:: console

    % vortex
    User     : droopy
    Profile  : research
    Vapp     : play
    Vconf    : sandbox
    Configrc : /home/droopy/.vortexrc
    % vortex last
    <vortex.gloves.ResearchGlove object at 0x1c531d0>


:command:`grid`

  Instanciate a :class:`~vortex.data.geometries.GridGeometry` with specified attributes.
  Return the new object.

  .. code-block:: console

    % vortex grid set=g
    <vortex.data.geometries.GridGeometry object at 0x21b7250>
    % vortex attributes g
    g: ['area', 'id', 'nlat', 'nlon', 'resolution']



:command:`handler`

  Perform a :func:`vortex.toolbox.rh` call with current attributes.
  Return the resource handler.

  .. code-block:: console

    % vortex spectral set=geo
    <vortex.data.geometries.SpectralGeometry object at 0x150b390>
    % vortex handler date=2012072218 cutoff=assim model=arpege geometry=geo kind=analysis file=analysis.last igakey="[model]"
      Handler <vortex.data.handlers.Handler object at 0x1531b90>
    Role      : Anonymous
    Alternate : None
    Complete  : True
    Options   : {}
    Location  : file://oper.inline.fr/arpege/arpege/oper/data/autres/ICMSHARPEINIT.r18

      Resource <common.data.modelstates.Analysis object at 0x1531590>
    Realkind   : analysis
    Attributes : {'cutoff': 'assim', 'kind': 'analysis', 'nativefmt': 'fa', 'geometry': <vortex.data.geometries.SpectralGeometry object at 0x150b310>, 'filling': 'full', 'filtering': None, 'date': Date(2012, 7, 22, 18, 0), 'clscontents': <class 'vortex.data.contents.DataRaw'>, 'model': 'arpege'}

      Provider <iga.data.providers.IgaProvider object at 0x1531850>
    Realkind   : iga
    Attributes : {'tube': 'file', 'namespace': 'oper.inline.fr', 'member': None, 'source': None, 'igakey': 'arpege', 'suite': 'oper', 'config': <iga.data.providers.IgaCfgParser instance at 0x151ec20>, 'vconf': 'sandbox', 'vapp': 'play'}

      Container <vortex.data.containers.File object at 0x1531ad0>
    Realkind   : file
    Attributes : {'file': 'analysis.last'}

:command:`help`

  Print documentation for all or specified methods of the current shell dispatcher.

  .. code-block:: console

    % vortex help mload

      mload:
        Print / Return the results of the import on the specified modules.


:command:`id`

  Print current session identification card.
  Return the id number of the session.

  .. code-block:: console

    % vortex id
    Name     : root
    Started  : 2012-07-19 18:26:02.054235
    Active   : True
    Duration : 0:07:26.410897
    Loglevel : WARNING
    % vortex last
    35956304


:command:`item`

  Extract from an object either a key or an idx entry.
  Return this entry.

  .. code-block:: console

    % vortex catalogs set=cats
    ['gloves', 'systems']
    % vortex item from=cats idx=1
    systemsls -

:command:`locate`

  Load a resource handler and apply the ``locate`` method.
  Return this information.

  .. code-block:: console

    % vortex vapp value=arpege
    arpege
    % vortex vconf value=france
    france
    % vortex envfp date=2012072218 cutoff=assim model=arpege
    {'DATE': '2012072218', 'CUTOFF': 'assim', 'MODEL': 'arpege'}
    % vortex locate geometry=geo kind=analysis suite=oper virtual=true
    mrpm631@cougar.meteo.fr:/home/m/mxpt/mxpt001/arpege/oper/assim/2012/07/22/r18/analyse

:command:`mload`

  Print / Return the results of the import on the specified modules.

  .. code-block:: console

    % vortex mload common.data
    [<module 'common' from '/home/droopy/dev/eclipse/vortex/src/common/__init__.py'>]


:command:`mpitool`

  Load a mpitool object according to description.
  Return the object itself.
  See also :mod:`vortex.algo.mpitools`.

  .. code-block:: console

    % vortex vortex mpitool mpiname=mpirun sysname=Linux set=mpi
    <vortex.algo.mpitools.MpiRun object at 0x1d5ee90>
    % vortex attributes mpi
    mpi: ['mpiname', 'mpiopts', 'sysname']


:command:`mpitools`

  Display mpitools catalog contents.
  Return the catalog itself.

  .. code-block:: console

    % vortex mpitools
    <class 'common.algo.mpitools.NecMpiRun'>
    <class 'vortex.algo.mpitools.MpiRun'>


:command:`namespaces`

  Display the range of names defined as values for ``namespace`` or ``netloc`` attributes.
  Optional arguments are ``only`` and ``match``.
  Return the associated dictionary.

  .. code-block:: console

    % vortex namespaces
    multi.open.fr	 ['vortex.data.stores.VortexStore']
    multi.vortex.fr	 ['vortex.data.providers.Vortex']
    open.archive.fr      ['vortex.data.stores.VortexArchiveStore', 'vortex.data.providers.Vortex']
    open.cache.fr        ['vortex.data.stores.VortexCacheStore', 'vortex.data.providers.Vortex']
    open.meteo.fr        ['vortex.data.stores.VortexStore']
    open.vortex.fr       ['vortex.data.providers.Vortex']
    vortex.archive.fr    ['vortex.data.stores.VortexArchiveStore', 'vortex.data.providers.Vortex']
    vortex.cache.fr      ['vortex.data.stores.VortexCacheStore', 'vortex.data.providers.Vortex']

  As both some :mod:`~vortex.data.providers` and :mod:`~vortex.data.stores`
  define namespaces (more precisely ``netloc`` for stores), one can select to display
  only one kind of these objects:

  .. code-block:: console

    % vortex namespaces only=stores
    multi.open.fr        ['vortex.data.stores.VortexStore']
    open.archive.fr      ['vortex.data.stores.VortexArchiveStore']
    open.cache.fr        ['vortex.data.stores.VortexCacheStore']
    open.meteo.fr        ['vortex.data.stores.VortexStore']
    vortex.archive.fr    ['vortex.data.stores.VortexArchiveStore']
    vortex.cache.fr      ['vortex.data.stores.VortexCacheStore']

  It is also possible to give a regular expression to match the namespaces themselves,
  for example:

  .. code-block:: console

    % vortex namespaces match=cache
    open.cache.fr        ['vortex.data.stores.VortexCacheStore', 'vortex.data.providers.Vortex']
    vortex.cache.fr      ['vortex.data.stores.VortexCacheStore', 'vortex.data.providers.Vortex']

  Both options could be combined.


:command:`nice`

  Data dumper on any key/value.
  Nothing to return.

  .. code-block:: console

    % vortex nice foo=2 default='direct'
      default:
        'direct'
      foo:
        '2'


:command:`provider`

  Load a provider object according to description.
  Return the object itself.
  See also :mod:`vortex.data.providers`.

  .. code-block:: console

    % vortex provider remote=/tmp/foo set=p
    <vortex.data.providers.Remote object at 0x2519510>
    % vortex attributes p
    p: ['hostname', 'remote', 'tube', 'username', 'vapp', 'vconf']
    % vortex apply with=p attr=tube
    file

:command:`providers`

  Display providers catalog contents.
  Return the catalog itself.

  .. code-block:: console

    % vortex  providers
    <class 'vortex.data.providers.Remote'>
    <class 'vortex.data.providers.Vortex'>


:command:`put`

  Perform a :func:`vortex.toolbox.rput` call with current attributes.
  Return the resource handler.

  .. code-block:: console

    % vortex put geometry=geo kind=analysis experiment=A001 block=canari namespace=olive.cache.fr file=analysis.last
    put: 1
    % vortex echo last
    last: [<vortex.data.handlers.Handler object at 0x1a8c0d0>]

  (Assuming the same defaults as the :command:`get` command).

:command:`refill`

  Refill the specified catalogs already in the calatogs table.
  Return the actual number of items.

  .. code-block:: console

    % vortex refill
    stores: 4
    providers: 2
    containers: 3
    gloves: 2
    systems: 1
    components: 3
    resources: 2
    mpitools: 1
    % vortex mload common.data
    [<module 'common' from '/home/droopy/dev/eclipse/vortex/src/common/__init__.py'>]
    % vortex refill resources
    resources: 20
    % vortex resources
    <class 'common.data.binaries.IFSModel'>
    <class 'common.data.boundaries.Elscf'>
    <class 'common.data.climfiles.ClimBDAP'>
    <class 'common.data.climfiles.ClimGlobal'>
    <class 'common.data.climfiles.ClimLAM'>
    <class 'common.data.consts.MatFilter'>
    <class 'common.data.consts.RtCoef'>
    <class 'common.data.gridfiles.Gridpoint'>
    <class 'common.data.logs.Listing'>
    <class 'common.data.modelstates.Analysis'>
    <class 'common.data.modelstates.Historic'>
    <class 'common.data.modelstates.Histsurf'>
    <class 'common.data.namelists.NamSelect'>
    <class 'common.data.namelists.NamTerm'>
    <class 'common.data.namelists.NamUtil'>
    <class 'common.data.namelists.Namelist'>
    <class 'common.data.namelists.Namelistfp'>
    <class 'common.data.namelists.Namselectdef'>
    <class 'vortex.data.executables.BlackBox'>
    <class 'vortex.data.executables.Script'>



:command:`resource`

  Load a resource object according to description.
  Return the object itself.
  See also :mod:`vortex.data.resources`.

  .. code-block:: console

    % vortex envfp date=2012072018 model=arpege cutoff=production
    {'DATE': '2012072018', 'CUTOFF': 'production', 'MODEL': 'arpege'}
    % vortex spectral set=geo
    <vortex.data.geometries.SpectralGeometry object at 0xb7de10>
    % vortex resource kind=analysis geometry=geo set=a
    <common.data.modelstates.Analysis object at 0xb9d8d0>
    % vortex attributes a
    a: ['clscontents', 'cutoff', 'date', 'filling', 'filtering', 'geometry', 'kind', 'model', 'nativefmt']


:command:`resources`

  Display resources catalog contents.
  Return the catalog itself.

  .. code-block:: console

    % vortex resources
    <class 'vortex.data.executables.BlackBox'>
    <class 'vortex.data.executables.Script'>


:command:`rmfp`

  Remove from current default footprint the specified keys.
  Return the list of removed keys.

  .. code-block:: console

    % vortex envfp date=2012072018 model=arpege cutoff=production
    {'DATE': '2012072018', 'CUTOFF': 'production', 'MODEL': 'arpege'}
    % vortex rmfp  date
    ['date']
    % vortex envfp
    {'CUTOFF': 'production', 'MODEL': 'arpege'}


:command:`session`

  Print current session tag.
  Return current session.

  .. code-block:: console

    % vortex session
    root
    % vortex last
    <vortex.sessions.Ticket object at 0x29e5710>


:command:`spectral`

  Instanciate a :class:`~vortex.data.geometries.SpectralGeometry` with specified attributes.
  Return the new object.

  .. code-block:: console

    % vortex spectral truncation=1199 set=geo
    <vortex.data.geometries.SpectralGeometry object at 0x2a60590>
    % vortex attributes geo
    geo: ['area', 'id', 'resolution', 'stretching', 'truncation']
    % vortex apply with=geo attr=truncation
    1199


:command:`store`

  Load a store object according to description.
  Return the object itself.
  See also :mod:`vortex.data.stores`.

  .. code-block:: console

    % vortex store netloc=open.meteo.fr scheme=vortex set=st
    <vortex.data.stores.VortexStore object at 0x2a50710>
    % vortex attributes st
    st: ['netloc', 'scheme']


:command:`stores`

  Display stores catalog contents.
  Return the catalog itself.

  .. code-block:: console

    % vortex stores
    <class 'vortex.data.stores.Finder'>
    <class 'vortex.data.stores.VortexArchiveStore'>
    <class 'vortex.data.stores.VortexCacheStore'>
    <class 'vortex.data.stores.VortexStore'>
    % vortex last
    <vortex.data.stores.StoresCatalog object at 0x2880290>


:command:`system`

  Load a system object according to description.
  Return the object itself.
  See also :mod:`vortex.tools.systems`.

  .. code-block:: console

    % vortex system sysname=Linux
    <vortex.tools.systems.LinuxBase object at 0x2880150>

:command:`systems`

  Display systems catalog contents.
  Return the catalog itself.

  .. code-block:: console

    % vortex systems
    [<class 'vortex.tools.systems.LinuxBase'>]
    % vortex last
    <vortex.tools.systems.SystemsCatalog object at 0x297ae50>


:command:`trackers`

  Display the tagged references to internal footprint resolution trackers.
  Return the table itself.

  .. code-block:: console

    % vortex trackers
    {'fpresolve': <vortex.utilities.trackers.Tracker instance at 0x17443f8>}


:command:`trackfp`

  Display a complete dump of the footprint resolution tracker.
  Return nothing.

  .. code-block:: console

    % vortex trackfp
    <?xml version="1.0" ?>
    <tracker tag="fpresolve">
        <catalog name="vortex.gloves.GlovesCatalog" stamp="2012-07-20 13:36:54.815228">
            <class name="vortex.gloves.OperGlove">
                <key name="profile" text="missing"/>
            </class>
            <class name="vortex.gloves.ResearchGlove"/>
        </catalog>
        <catalog name="vortex.tools.systems.SystemsCatalog" stamp="2012-07-20 13:36:54.817239">
            <class name="vortex.tools.systems.LinuxBase"/>
        </catalog>
        <catalog name="vortex.algo.mpitools.MpiToolsCatalog" stamp="2012-07-20 13:37:16.818858">
            <class name="vortex.algo.mpitools.MpiRun">
                <key name="mpiname" text="missing"/>
            </class>
        </catalog>
    </tracker>


:command:`user`

  Shortcut to glove's username.

  .. code-block:: console

    % vortex user
    droopy

:command:`vapp`

  Print or set current ``vapp`` value.
  Return actual vapp.

  .. code-block:: console

    % vortex vapp
    play
    % vortex vapp value=arome
    arome

:command:`vconf`

  Print or set current ``vconf`` value according to ``value`` argument.
  Return actual vconf.

  .. code-block:: console

    % vortex vconf
    sandbox
    % vortex vconf value=ensemble
    ensemble


================
Beyond the scene
================

The specific coprocess launched is tagged with the process-id of the calling shell session.
Therefore, different shell sessions of the same user will have a diffrent namespace
for their relative commands.

The current communication with the coprocess is achieved through standard named pipes
wich are created by default in the :file:`$HOME/.vortexrc` user's directory:

.. code-block:: console

  % cd $HOME/.vortexrc
  % ls -l
  -rw-r--r-- 1 droopy tex    6 2012-07-19 12:20 fifo.p17579
  prw-r--r-- 1 droopy tex    0 2012-07-19 12:20 fifo.r17579|
  prw-r--r-- 1 droopy tex    0 2012-07-19 12:20 fifo.w17579|
  -rw-r--r-- 1 droopy tex  714 2012-07-19 11:49 vortexsh.log.17579

An alternate location could be provided through the environment variable :envvar:`FIFODIR`.

