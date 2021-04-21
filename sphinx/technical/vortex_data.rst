.. _vortex_data:

*****************************************
Management of data by the Vortex provider
*****************************************

:Release: |version|
:Author: Louis-François Meunier
:Date: |today|

Vortex provider's attributes influence how the data are stored. On
file based systems, the **vapp**, **vconf** and **experiment** mandatory
attributes determine the first bits of the data hierarchy:
``vapp/vconf/experiment/...``.

Attributes like **namespace** and **experiment** enable the Vortex
provider to decide:

* on which host the data should be located (e.g. in a local cache, on the mass
  archive system, ...);
* where it should reside on this host (e.g. on a file based mass archived
  system, in which sub-directory will the Vortex data hierarchy start). From
  now and one, we will call this location the "*root of the data hierarchy*".

The **namespace** attribute accepts four values:

* ``vortex.cache.fr``: Data are solely stored and retrieved from the local
  machine. This *Cache* space should give a very fast access to data
  especially if the data is requested in read-only mode (i.e by specifying
  the **intent** = ``"in"`` when calling :func:`vortex.toolbox.input`.
* ``vortex.archive.fr``: Data are solely stored and retrieved from a mass
  archive system. Such *Archive* systems have a very large capacity but
  provide only a slow access to data (moreover, the access time might
  fluctuate).
* ``vortex.multi.fr``: In that case, Vortex tries to optimally exploit the
  two worlds. When retrieving a data, the *Cache* space is looked at first. If
  the data is missing in *Cache*, it is fetched from the *Archive* and put back
  in *Cache* (for a later use). When storing a data, both the *Cache* and
  *Archive* spaces are fed.
* ``vortex.hack.fr``: This very special case won't be discussed here. The
  reader may refer to :ref:`nbook-VortexStacksDoc`

Description of the Vortex *Cache* space
=======================================

The *Cache* space may be hosted on a large variety of technologies. That being
said, the only available option in Vortex right now is to rely on a POSIX like
file-system (on clusters, a shared file-system is used).

If the *MTOOL* software is used to launch your job, the *Cache* location is
pre-configured. Otherwise the ``$MTOOLDIR`` environment variable should be
defined in order to tell Vortex where to create the *Cache* space.

The *Cache* space is created in: ``$MTOOLDIR/cache``.

The Vortex Provider's *Cache* is made of several "layers":

* Your own writable *Cache* space is located below ``$MTOOLDIR/cache/vortex``
  (the root of the data hierarchy). This is the go-to place to retrieve and
  store data locally (*NB*: When used through ``vortex.multi.fr``, data
  fetched from the *Archive* will be stored here even (if they have been
  produced by others). This mechanism is called "*refill*").
* When getting data, if the lookup in ``$MTOOLDIR/cache/vortex`` fails, the
  ``$MTOOLDIR/cache/vortexbuddies`` location will also be searched. This
  read-only location can be used to retrieve data freshly produced by others
  (your "buddies"). Let's say you want to retrieve data from your friend
  Charles' *Cache* for experiment ABCD (vapp "arpege" and vconf
  "4dvarfr"), you will create a symbolic link from
  ``Charles_mtooldir/cache/vortex/arpege/4dvarfr/ABCD`` to
  ``$MTOOLDIR/cache/vortexbuddies/arpege/4dvarfr/ABCD``.
* Finally, when getting data, a "*MarketPlace*" location can also be looked
  at (if all of the two previous lookups failed). Such locations need to be
  configured well in advance in Vortex. This is not very flexible but allows
  a privileged user/administrator to prefetch and permanently store data that
  are frequently accessed. The :class:`~vortex.tools.storage.MarketPlaceCache`
  documentation briefly describes how to configure such a cache. In any case,
  before changing the configuration of the "*MarketPlace*" location, please
  contact the Vortex support team.

When accessing data produced by the operational team, this works slightly
differently:

* Your own *Cache* (located below ``$MTOOLDIR/cache/vortex``) will still be
  used (e.g. to *refill* data fetched from the *Archive*);
* The *vortexbuddies* and *MarketPlace* locations are ineffective;
* If permitted in Vortex configuration, the operational team's cache directories
  will be looked up.

Description of the Vortex *Archive*
===================================

The Vortex *Archive* may be managed using a large variety of technologies.
However, Vortex currently uses file-based archiving systems. Such systems can be
accessed using various protocols: Vortex should be preconfigured in order to
determine which host and protocol needs to be used.

If a user wants to override these preconfigured values, the **storage**
(host name) and **storetube** attributes may added during the
:func:`vortex.toolbox.input` or :func:`vortex.toolbox.output` calls.
Alternatively, for a more permanent change regarding the target host, the
``VORTEX_DEFAULT_STORAGE`` environment variable can be set. Be aware that
it is not guarantee to work since Vortex may lack configuration data for
some hosts.

The Vortex Provider determines the root of the data hierarchy depending on the
**experiment** attribute:

* For anything related to the operational team (**experiment** attributes like
  *oper*, *dble*, *test* or *mirr*), Vortex will automatically find the
  appropriate root of the data hierarchy;
* For any data produced by the *Olive* system (**experiment** attributes like
  *XXXX* where the "Xs" are letters or digits), Vortex will find the appropriate
  root of the data hierarchy. To do so, it heavily relies on symbolic links
  that should be managed by the *Olive* system itself (for any reason, *Olive*
  may fail to create these links: in such case contact the SWAPP support);
* Otherwise, **experiment** should look like that:
  ``any_xp_identifier@location`` where ``location`` usually identifies a
  user-name on the *Archive*. In such a case, Vortex will consider that the
  root of the data hierarchy, is the 'vortex' directory in the home-directory
  of the user identified by ``location``. This is the default behaviour that
  will be used most of the time. However, in Vortex's configuration it is
  possible to define "virtual" ``location`` attributes. This configuration-based
  mechanism might be interesting to designate some general-interest data
  (as opposed to personal or user specific data). A more detailed explanation
  is given in the following section.

Configuration of "virtual" locations in the Vortex *Archive*
------------------------------------------------------------

The global configuration for Vortex' *Archive* is located in the Vortex source
distribution: ``conf/store-vortex-free.ini``. This configuration file
contains default settings (that may not be very useful) and, more
interestingly, configuration data related to many specific *Archive* hosts.

Let's consider an *Archive* host whose network name is ``mass-archive.domain.fr``.
This could result in the following configuration file:

.. code-block:: ini

   [DEFAULT]
   localconf=@store-vortex-free-default.ini

   [mass-archive.domain.fr]
   localconf=@store-vortex-free-mass-archive.ini
   generic_remoteconf1_uri=ftp://mass-archive.domain.fr/home/privileged_user/vortex/store-vortex-free.ini
   generic_remoteconf1_restrict=^teamA_
   generic_remoteconf2_uri=ftp://mass-archive.domain.fr/home/other_privileged_user/vortex/store-vortex-free-bis.ini
   generic_remoteconf2_restrict=^teamB_

The default configuration will be read in ``conf/store-vortex-free-default.ini``
but for ``mass-archive.domain.fr`` the configuration will be read in
``conf/store-vortex-free-mass-archive.ini`` instead.

Note that ``generic_remoteconfN_uri`` and ``restrict`` clauses present. They
define that, for any ``location`` matching the ``generic_remoteconfN_restrict``
regular expression, the configuration file referred by ``generic_remoteconfN_uri``
should be used (in addition to the default one).

With our example, when accessing **experiment** ``world01@teamA_reanalysis``,
the configuration file hosted by "privileged_user" will be considered (in
addition to ``conf/store-vortex-free-mass-archive.ini``).

Such configuration files look like (example for the one hosted by "privileged
user"):

.. code-block:: ini

   [teamA_reanalysis]
   storeroot=/home/some_real_user/reanalysis

   [teamA_reforecast]
   storeroot=/home/henry_username/reforecast

   [teamA_reforecast hosted by john]
   first_idrestrict=^proxima\d+$
   second_idrestrict=^(jupyter|saturn)\d+$
   storeroot=/home/john_username/reforecast

It tells that any experiments with the ``teamA_reanalysis`` location will be
looked for in ``/home/some_real_user/reanalysis`` (e.g.
``world01@teamA_reanalysis``)

It also tells that experiments with the ``teamA_reforecast`` location will be
looked for in ``/home/henry_username/reforecast``; except if **experiment** is
something like ``proxima01@teamA_reforecast`` or
``jupyter01@teamA_reforecast`` (that are hosted by John). These exceptions are
defined using:

* a dedicated configuration section whose name finishes by " hosted by someone";
* "?_idrestrict" entries that contain regular expressions.
