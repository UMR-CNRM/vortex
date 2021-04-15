.. _examples_and_howto:

Various examples
################

Simple bits of code to demonstrate how to use Vortex in simple scripts
**********************************************************************

These are scripts written by several members of the Vortex team. They are
located in the ``examples`` sub-directory of the Vortex code package. Be aware
they may need some adaptations prior to being run (setup your email address,
...).

Retrieve and archive data using Vortex
--------------------------------------

* Get some data from a Vortex experiment (*e.g.* from the Operational suite,
  from an Olive-Vortex experiment, ...):
  ``examples/get_analysis_from_vortex.py``
* Get some data from an "historical" Olive-Perl experiment:
  ``examples/get_analysis_from_olive.py``
* Get some data using the remote provider (*i.e.* manually provide the
  address/path from where the data can be retrieved):
  ``examples/get_analysis_from_remote.py``
* Get a climatology file (a constant file) from the Genv database:
  ``examples/get_climatology_from_genv.py`` (*N.B.*: the ``genv`` command
  needs to be installed)
* Get a namelist file (a constant configuration file) from the Genv database:
  ``examples/get_namelist_from_genv.py`` (*N.B.*: the ``genv`` command
  needs to be installed)
* Simple manipulation of data using a Vortex' ResourceHandler:
  ``examples/get_simple_resource.py``
* Get data from the BDAP database and store it on the mass archive:
  ``examples/get_files_from_bdap.py`` (to be executed on a Meteo-France Soprano
  Server)
* Extract data from the BDPE database: ``examples/bdpe_extract.py`` (to be
  executed on a Meteo-France Soprano Server)

Useful things to retrieve data more efficiently
-----------------------------------------------

* Basic manipulations on dates: ``examples/dealing_with_dates_and_terms.py``
* Use of footprint's *glob* mechanism: ``examples/dealing_with_glob.py``
* Use of the *hook* mechanism to manipulate the content of an input resource:
  ``examples/dealing_with_hooks.py``
* Inspect and update the contents of a Fortran's namelists file:
  ``examples/dealing_with_namelist.py``

Run simple scripts with Vortex
------------------------------

* How to run a simple script using a Vortex' AlgoComponent:
  ``examples/run_simple_script.py`` and ``examples/run_script_variations.py``

A few nice utility programs and objects
---------------------------------------

* How to send an email: ``examples/actions.py``
* How to send an email in the operational suite context: ``examples/opmail.py``
* Send a prestaging request to the mass archive system:
  ``examples/vtxprestage.sh``

.. _examples_algo:

AlgoComponent examples
**********************

.. _examples_algo_pp:

Example of post-processing AlgoComponents
-----------------------------------------

The first example is an AlgoComponent that works on several input data (those
with the "Gridpoint" role): They are dealt with sequentially (one at a time). Pure
Python is used to compute this "fake" post-processing. Have a look at the
:class:`sandbox.algo.stdpost.GribInfosSequential` class (that inherits a lot of
things from the :class:`sandbox.algo.stdpost._AbstractGribInfos` abstract class).

The second example adds extra refinements on top of the previous example:

* The input data may have been promised by another task (thus allowing on the
  fly processing);
* The input data are processed as soon as they are available (*e.g.* if there
  are several members, data with term 06h of member 2 may be available before
  term 03h of member 1);
* Additionally, if they have been promised, the output files are stored in cache
  as soon as they are available.

See the :class:`sandbox.algo.stdpost.GribInfosArbitraryOrder` class.

The third example does exactly the same thing as the previous one but
instead of using pure Python, an external script is used to compute the
"fake" post-processing: have a look at the
:class:`sandbox.algo.stdpost_script.GribInfosScript` class. This AlgoComponent
class is designed to run with a bash script described by the
:class:`sandbox.data.executables.StdpostScript` Resource.

The fourth example is an improved version of the previous one since it uses
the :mod:`taylorism` package to process the various input files in parallel:
have a look at the :class:`sandbox.algo.stdpost_script.GribInfosParaScript`
class. Since :mod:`taylorism` is used, this AlgoComponent it heavily relies
on the :class:`sandbox.algo.stdpost_script.GribInfosParaScriptWorker` "Worker"
class.

To see these various AlgoComponents in action, please refer to the job examples
described below (in :ref:`examples_jobs_pp`).

.. _examples_jobs:

Job examples using the Vortex' *mkjob* system
*********************************************

Such examples are located in the ``examples/jobs/DEMO`` sub-directory of the
Vortex code package.

.. _examples_jobs_pp:

Example of post-processing jobs and tasks
-----------------------------------------

They demonstrate the use of the AlgoComponents described above (in the
:ref:`examples_algo_pp` section). Please see the
``examples/jobs/DEMO/arpege/stdpost/README.md`` file that explains all there
is to know on these examples and, more importantly, how to launch them on your
own workstation.

Example of advanced features of the Vortex' *mkjob* system
----------------------------------------------------------

Dummy tasks are used to demonstrate the use of some advanced features of the
Vortex' *mkjob* system. Please see the
``examples/jobs/DEMO/sandbox/play/README.md`` file that explains all there
is to know on these examples and, more importantly, how to launch them on your
own workstation.

Here is a short description of the features demonstrated in theses examples:

* The ``on_error`` mechanism: it allows to instruct *mkjob* how to react when a
  Task or Family fails. The default behaviour is to crash rather abruptly.
  Alternatively, the failure can be:

  * silently ignored;
  * masked to allow the other tasks and families to run, but cause the job to
    crash when it finishes.

* The use of a custom :class:`vortex.layout.jobs.JobAssistantPlugin` class to
  customise the job environment.

* The use of the :class:`vortex.layout.nodes.LoopFamily` to easily creates
  loops on various dates, members, or whatever

* The ``active_callback`` mechanism: it allows to specify a complex
  condition (based on the configuration data) to determine if a given
  :class:`~vortex.layout.nodes.Node` should be executed or not.

* The ``paralleljobs`` mechanism: it allows to start several
  :class:`~vortex.layout.nodes.Node` s in parallel (this is nice
  but very limited...).

* The use of the :class:`vortex.layout.nodes.WorkshareFamily` to partition
  the work in slices (which is usefull when the ``paralleljobs`` mecahnism
  is used).
