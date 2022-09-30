.. _vortex_data_export:

*****************************************
Export data to external/unusual locations
*****************************************

In a few use cases it is necessary to export/duplicate some data to another
location. Whenever possible, such a duplication must be avoided since it
consumes unnecessary storage and may be difficult to maintain in the long term.

Automatic copy of a job's input data to another location
========================================================

The :class:`~vortex.data.providers.Vortex` Provider includes a "set_aside"
feature that can be trigger using the **vortex_set_aside** attribute.

This feature will only affect retrieved data. With this feature activated,
whenever a data is fetched, in addition to being available in the *Container*,
it will also be pushed to another alternative location. This alternative
location will be described using the **vortex_set_aside** attribute that is a
dictionary.

In practice, it would be cumbersome to provide a **vortex_set_aside** attribute
each time a new *Provider* is created. That's why it is recommended to use the
:mod:`footprints` defaults for this attribute. Alternatively, a
``VORTEX_PROVIDER_SET_ASIDE`` environment variable, that will be converted to
a dictionary can be used (this is not recommended method).

If `mkjob` is used to create a job, any ``vortex_set_aside`` variable available
if the job's configuration (using the configuration file) will automatically
be added to :mod:`footprints` defaults.

As mentioned earlier, the **vortex_set_aside** attribute needs to be a
dictionary. Here is a basic example:

.. code-block:: python

    vortex_set_aside = dict(
        defaults = dict(
            namespace = 'vortex.archive.fr',
            storage = 'newhost.somewhere.com',
            storetube = 'ftp'
        )
    )

In this example, all input data will be uploaded to ``newhost.somewhere.com``
using FTP and the ``archive.meteo.fr`` namespace (this way nothing will be
written in cache). For very specific needs, it may be desired to update the
provider attributes for a given experiment. For example, because of write
permission issues, it may be a good idea to upload the ``OPER`` experiment
to ``mf_oper_mirror@myself``:

.. code-block:: python

    vortex_set_aside = dict(
        defaults = dict(
            namespace = 'vortex.archive.fr',
            storage = 'newhost.somewhere.com',
            storetube = 'ftp'
        ),
        edits = dict(
            OPER = dict(experiment='mf_oper_mirror@myself')
        )
    )

More generally, ``defaults`` and ``edits`` can be used to update any attribute
of the provider (e.g. ``namespace`` or ``experiment``) or any *Store*'s option
(e.g. ``storage`` or ``storetube``).

Mutually exclusive ``includes`` or ``excludes`` lists can also be providers. For
example, it is possible to re-upload only the "xp@myself" and "OPER" experiments:

.. code-block:: python

    vortex_set_aside = dict(
        defaults = dict(
            namespace = 'vortex.archive.fr',
            storage = 'newhost.somewhere.com',
            storetube = 'ftp'
        ),
        includes = ['xp@myself', 'OPER'],
        edits = dict(
            OPER = dict(experiment='mf_oper_mirror@myself')
        )
    )

A dedicated tool for Uenv/Uget
==============================

A similar need exists for constant data archived using the ``uget.py`` tool (see
:ref:`nbook-Uget`). A dedicated tool is provided in order to upload a whole
"Uenv" to either ECMWF's ECFS or a Vortex's bucket (see below).

Please type ``bin/uenv_mirror.py -h`` in your terminal.

The ``--gdata-target=somelocation`` will probably be used. It will cause "gget"
data to be re-archived with "Uget" in "somelocation". Since the "Uenv" file
itself won't be affected (i.e. it will still refer to the "gget" element), it
will be likely to cause issues at runtime.

That's why a session-wide Uenv configuration has been introduced. It can be
changed manually:

.. code-block:: python

    from gco.tools.uenv import config as u_config
    u_config('gdata_detour', value='somelocation')

However, when *mkjob.py* is used to create the job, it is more convenient to:

* load the "uenv_gdata_detour" :class:`~vortex.layout.jobs.JobAssistant` plugin
  (using ``loadedjaplugins`` in the job's configuration will do the trick)
* define a ``uenv_gdata_detour`` variable in the job's configuration
  (e.g. ``uenv_gdata_detour = somelocation``)

Manual exports: the *bucket* concept
====================================

Unfortunately, the "set_aside" feature won't be enough most of the time
since network restrictions will probably prevent Vortex to access the desired
target location. Conversely, without the *bucket* concept, the ``uenv_mirror.py``
utility would not be of any use outside of ECMWF.

The idea behind "buckets" is to use the "set_aside" feature and/or the
``uenv_mirror.py`` utility to drop exported data in a named location of the
local machine.

In a second phase, the user will be responsible to transfer this "bucket" to
the desired remote server (tar + hard-drive, rsync, ...).

Finally, on the remote server, the ``bin/bucket_upload.py`` utility will be
used to upload the "bucket" to the appropriate **storage**.

A typical workflow would look like this :

1. Export experiment data to a bucket
-------------------------------------

This could be achieved through the "set_aside" feature:

.. code-block:: python

    vortex_set_aside = dict(
        defaults = dict(
            namespace = 'vortex.archive.fr',
            storage = 'foo.bucket.localhost',
        ),
        edits = dict(
            OPER = dict(experiment='mf_oper_mirror@myself'),
            DBLE = dict(experiment='mf_dble_mirror@myself'),
        )
    )

2. Export Uenv data to a bucket
-------------------------------

The ``uenv_mirror.py --to-bucket=foo --gdata-target=somelocation uenv:myenv@myself``
command should do the trick.

3. Transfer the "bucket" wherever you need
------------------------------------------

In the previous steps, the "foo" bucket has been created in your home-directory
under ``~/vortexbucket/foo``: Do whatever you need to transfer it wherever you
want.

On the remote system, the bucket also needs to be located under
``~/vortexbucket/foo``.

The ``~/vortexbucket`` location may not the best choice on your system, if you
need to store buckets in another location, just replace the ``vortexbucket``
directory with a symbolic link to the appropriate location.

4. Export the data to the appropriate Vortex storage
----------------------------------------------------

For example, let's consider we exported the bucket to ECMWF. It would be a good
idea to put the data on ECFS:

The ``bucket_upload.py --ecmwf foo ecfs.ecmwf.int`` command should do the trick.

(The ``--ecmwf`` option just instructs ``bucket_upload.py`` to load ECMWF
specific addons (to support ECFS)).
