.. _uget-en:

***********************************************
User Documentation Uenv/Uget
***********************************************

:Release: |version|
:Author: Alexandre Mary et al.
:Date: |today|

The *uenv/uget* tool developped in Vortex is the counterpart of
*genv/gget* (MF/GCO op team), but user-oriented (hence the **u** instead of **g**)
and shareable with other users.
It enables, in Vortex experiments, to get resources the same way as within an official
*genv* but from your own catalogs or your colleagues'.

This tool hence enables to work in research mode the same way as with official op resources,
changing just the *uenv* in the Vortex experiment.

How does it work ?
Quite simple, but a few explanations are necessary to use it properly...


Tutorial
========

The following example shows how to modify components of an Arome-France *genv* catalog and modify its components piece
by piece.

.. highlight:: none


Before first use
----------------

.. highlight:: bash

* load Genv/Gget (in your *profile*, if not already done)::

    export PATH=/home/mf/dp/marp/gco/public/bin:$PATH

* load Vortex (in your *profile*, if not already done)::

      module load python
      VORTEX_INSTALL_DIR=/home/mf/dp/marp/verolive/vortex/vortex
      PYTHONPATH=$VORTEX_INSTALL_DIR/src:$PYTHONPATH
      PYTHONPATH=$VORTEX_INSTALL_DIR/site:$PYTHONPATH
      PYTHONPATH=$VORTEX_INSTALL_DIR/project:$PYTHONPATH
      export PYTHONPATH
      export PATH=$VORTEX_INSTALL_DIR/bin:$PATH

* initialisation of directories::

      uget.py bootstrap_hack [user]

  Ex::

      uget.py bootstrap_hack mary

.. highlight:: none

.. _uget-clone-existant-en:

Clone an existing env (catalog)
-------------------------------

Syntax::

    uget.py hack genv [cycle_source] into [cycle_cible]@[user]

Ex::

    uget.py hack genv al42_arome-op2.30 into al42_arome-dble.02@mary

This "hack" command creates a copy of the genv catalog (``genv al42_arome-op2.30``),
under: ``$HOME/.vortexrc/hack/uget/mary/env/al42_arome-dble.02``.

The initial env can be a GCO official one (genv), or a user one (uenv);
in which case the syntax is slightly different, in order to precise who we want to get the env from::

    uget.py hack env al42_arome-dble.01@faure into al42_arome-dble.02@mary

It is a sort of convention within *uget* : ``genv blabla``
stands for a GCO env named ``blabla`` whereas ``env blabla@someone``
points to a user-owned env named ``blabla`` hosted at ``someone``.


Modification of the cloned env
------------------------------

For each element in the cloned catalog (obtained at step
:ref:`uget-clone-existant-en`), we can modify the the resource (i.e. to the right of the ``=``),
by pointing at an element in the "GCO official store",
or at a colleague's or one of your own's (under ``$HOME/.vortexrc/hack/uget/$USER/data/``).

We can mix such elements of a *uenv*...

Ex:
    | I am user ``mary``, the element:
    |    ``CLIM_FRANMG_01KM30=clim_franmg.01km30.03`` (at GCO)
    | can be replaced by :
    |    ``CLIM_FRANMG_01KM30=uget:mes_clims@mary`` (``uget:`` to identify it is an element managed by *uget* and ``@mary`` because the element is in my store)
    | or:
    |    ``CLIM_FRANMG_01KM30=uget:mes_clims.04@faure`` (``@faure`` because it is an element stored at user ``faure``)

Beware a little difference with ``genv`` for namelists packages:
these packages being stored as tar/tgz, you need to specify explicitly in the uenv.

Ex (note the extension ``.tgz``)::

    NAMELIST_AROME=uget:my_namelist_package.tgz@mary

However, *uget* will be able to get either the directory
``$HOME/.vortexrc/hack/uget/mary/data/my_namelist_package`` soit le tgz
``$HOME/.vortexrc/hack/uget/mary/data/my_namelist_package.tgz`` (actually, the most recently modified of both).

We can also add new resources in a  *uenv*.
The keys (left of the ``=`` just need to follow a precise Vortex syntax;
for instance for a clim file: ``CLIM_[AREA]_[RESOLUTION]``.

To modify an existing element (e.g. a namelist package), we get it via uget::

    uget.py hack gdata [element] into [clone_element]@[user]

Ex::

    uget.py hack gdata al42_arome-op2.15.nam into al42_arome-op2.16.nam.tgz@mary

or::

    uget.py hack data al42_arome-dble.01.nam.tgz@faure into al42_arome-op2.16.nam.tgz@mary

The convention used here by *uget* is consistent with the one used before:
``gdata blabla`` stands for a GCO element named ``blabla``
when ``data blabla@someone`` points to a data stored
via *uget/uenv*, named ``blabla`` and stored at ``someone``.

Historisation
-------------

It is a good practice to first check there are no inconsistency within your *uenv*,
i.e. check that all elements listed there actually exist, either locally or on archive,
and at your user, someone else or GCO::

    uget.py check env al42_arome-dble.02@mary

Then, to freeze a version and share it with other users, you need to push the *uenv* to archive::

    uget.py push env al42_arome-dble.02@mary

The command (can take a little while) archives the uenv AND the elements locally present onto archive.
It is then strongly recommended to clean them locally, to avoid to modify something that has been archived and
end up with inconsistencies between local and archived versions::

    uget.py clean_hack

Caution: all *uenv* and elements having been pushed are then deleted locally from
directories ``env`` et ``data`` !

We may also want to push just one element to make it available before a whole uenv is ready.

In this case::

    uget.py push data [element]@[user]}

Ex::

    uget.py push data al42_arome-op2.16.nam.tgz@mary


Explore
-------

*(new in Vortex-1.2.3)*

It is possible to list all uenv existing from a user::

    uget.py list env from faure

or the elements, potentially with a filter (based on a regular expression)::

    uget.py list data from faure matching .nam


From one uenv to another
------------------------

*(new in Vortex-1.2.3)*

It is also possible to compare 2 *uenv*::

    uget.py diff env [cycle_to_compare] wrt env [cycle_reference]

Ex::

    uget.py diff env al42_arome-dble.02@mary wrt genv al42_arome-op2.30

or::

    uget.py diff env al42_arome-dble.02@mary wrt env al42_arome-dble.01@faure

If your uenv has been generated using ``uget.py hack``, a comment has been left in the head of the file to trace its
history, and enables you to use the alias ``parent`` as::

    uget.py diff env [my_uenv] wrt parent


Export catalog
--------------

*(new in Vortex-1.2.3)*

The command ``uget.py export`` enables to list the elements updated with regards to a reference,
giving their path on the archive.

Ex::

    uget.py export env al42_arome-dble.02@mary [wrt genv al42_arome-op2.30]


Remarks and good habits
=======================

* clim files (and other monthly resources) are expanded:
  the key ``CLIM_BLABLA=uget:my_clims@mary`` aim at all files syntaxed
  ``my_clims.m??`` located in the directory ``data`` ;
* even if it is technically feasable, it is strongly advised to forbid yourself
  to modify an element once pushed. With the cache system, you may face weird fetches
  in experiments...
* as a corollary, it is a good habit to number each uenv and each resource, and increment them push after push
* on hendrix, the *uenv* and resources are archived under an archived and spread tree of directories.
  This is both for performance matters and an incitation to use ``uget.py`` to get these resources systematically
* before an element is pushed (uenv and resources), it is not accessible via ``uget.py`` nor a vortex experiment
  for other users, only for the owner.
* if large resources are to be pushed, one can advantageously log on a transfer node before the push
* comments are accepted in a *uenv*, starting with ``#``.


More advanced functionalities
=============================


Default user
------------

It can become cumbersome to repeat the user (e.g. ``@mary``) in command lines.
Hence a default user can be defined::

   uget.py set location mary

The default user can be retrieved with ``uget.py info``.
Once set, one can only type::

   uget.py check env al42_arome-dble.02

or::

   uget.py diff env al42_arome-dble.02 wrt env al42_arome-dble.01@faure

(instead of ``uget.py check env al42_arome-dble.02@mary`` and
``uget.py diff env al42_arome-dble.02@mary wrt env al42_arome-dble.01@faure``)

However, the user is required inside the uenv file catalog, and in the experiments.

Using *uget.py* in console mode
-------------------------------

In previous examples, we used ``uget.py`` via independent successive shell commands.
Another mode exists, using the console mode.
To do so, just type ``uget.py`` (without arguments) to open the interactive mode
(to quit, use ``Ctrl-D``);
you can then type commands as following::

      $ uget.py
      Vortex 1.2.2 loaded ( Monday 05. March 2018, at 14:07:13 )
      (Cmd) list env from mary

      al42_test.02
      [...]
      cy43t2_clim-op1.05
      cy43t2_climARP.01

      (Cmd) pull env cy43t2_clim-op1.05@mary

      ARPREANALYSIS_SURFGEOPOTENTIAL=uget:Arp-reanalysis.surfgeopotential.bin@mary
      [...]
      UGAMP_OZONE=uget:UGAMP.ozone.ascii@mary
      USNAVY_SOIL_CLIM=uget:US-Navy.soil_clim.bin@mary

      (Cmd) check env cy43t2_clim-op1.05@mary

      Hack   : MISSING (/home/meunierlf/.vortexrc/hack/uget/mary/env/cy43t2_clim-op1.05)
      Archive: Ok      (meunierlf@hendrix.meteo.fr:~mary/uget/env/f/cy43t2_clim-op1.05)

      Digging into this particular Uenv:
        [...]
        ARPREANALYSIS_SURFGEOPOTENTIAL: Archive  (uget:Arp-reanalysis.surfgeopotential.bin@mary)
        [...]
        UGAMP_OZONE                   : Archive  (uget:UGAMP.ozone.ascii.m01@mary for month: 01)
        UGAMP_OZONE                   : Archive  (uget:UGAMP.ozone.ascii.m02@mary for month: 02)
        UGAMP_OZONE                   : Archive  (uget:UGAMP.ozone.ascii.m03@mary for month: 03)
        UGAMP_OZONE                   : Archive  (uget:UGAMP.ozone.ascii.m04@mary for month: 04)
        UGAMP_OZONE                   : Archive  (uget:UGAMP.ozone.ascii.m05@mary for month: 05)
        UGAMP_OZONE                   : Archive  (uget:UGAMP.ozone.ascii.m06@mary for month: 06)
        UGAMP_OZONE                   : Archive  (uget:UGAMP.ozone.ascii.m07@mary for month: 07)
        UGAMP_OZONE                   : Archive  (uget:UGAMP.ozone.ascii.m08@mary for month: 08)
        UGAMP_OZONE                   : Archive  (uget:UGAMP.ozone.ascii.m09@mary for month: 09)
        UGAMP_OZONE                   : Archive  (uget:UGAMP.ozone.ascii.m10@mary for month: 10)
        UGAMP_OZONE                   : Archive  (uget:UGAMP.ozone.ascii.m11@mary for month: 11)
        UGAMP_OZONE                   : Archive  (uget:UGAMP.ozone.ascii.m12@mary for month: 12)
        USNAVY_SOIL_CLIM              : Archive  (uget:US-Navy.soil_clim.bin@mary)

      (Cmd) [Ctrl-D]
      Vortex 1.2.2 completed ( Monday 05. March 2018, at 14:09:06 )
      $

This mode can be interesting:

   * For systems on which loading Vortex is slow, you will load it once only in the beginning instead of at each
     command.
   * There is auto-completion (``Tab``).
   * Within one session, you can navigate through commands history.


Cheatsheet
==========

Environnement
-------------

* Recommended version of Vortex on belenos/taranis is : ``/home/mf/dp/marp/verolive/vortex/vortex-olive``
* ``uget.py`` is: ``/home/mf/dp/marp/verolive/vortex/vortex-olive/bin/uget.py``
* Genv/Gget are to be found in: ``/home/mf/dp/marp/gco/public/bin``
* The workdir of uget is: ``$HOME/.vortexrc/hack/uget/$USER/``

    * ``env/`` : *uenv* catalogs
    * ``data/`` : resources


Commands
--------

* clone a GCO env::

    uget.py hack genv al42_arome-op2.30 into al42_arome-dble.02@mary

* clone a uenv::

    uget.py hack env al42_arome-dble.01@faure into al42_arome-dble.02@mary

* display a uenv (equiv. command ``genv``)::

    uget.py pull env cy43t2_clim-op1.05@mary

* download a uget resource in CWD (equiv. command ``gget``)::

    uget.py pull data al42_arome-op2.15.nam.tgz@mary

* clone a GCO resource::

    uget.py hack gdata al42_arome-op2.15.nam into al42_arome-op2.16.nam.tgz@mary

* clone a uget resource::

    uget.py hack data al42_arome-dble.01.nam.tgz@faure into al42_arome-op2.16.nam.tgz@mary

* check that all elements exist, either locally or on archive::

    uget.py check env al42_arome-dble.02@mary

* archive a uenv (incl. resources implied)::

    uget.py push env al42_arome-dble.02@mary

* archive a resource::

    uget.py push data al42_arome-op2.16.nam.tgz@mary

* clean the workdir (hack) wrt what has been archived::

    uget.py clean_hack

* list uenv and resources from a user::

    uget.py list env from faure
    uget.py list data from faure

* compare 2 uenv::

    uget.py diff env al42_arome-dble.02@mary wrt genv al42_arome-op2.30

* list the resources modified and their path::

    uget.py export env al42_arome-dble.02@mary wrt genv al42_arome-op2.30

* I am lost::

    uget.py help

  and::

    uget.py help [hack|pull|check|push|diff|list|...]

