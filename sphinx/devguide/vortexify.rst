.. _vortexify:

From OLIVE/ksh to OLIVE/python
==============================

This section describes auto to semi-automatically migrate from an OLIVE/ksh experiment to a OLIVE/python experiment
based on VORTEX facilities.

Base experiment
---------------

Create a new experiment, starting from a clean configuration (not a copy of a copy of... of an experiment).
It is a good practice to move this working experiment in a dedicated folder, making an other copy of the experiment
as a reference.

Be sure not to have any explicit date or explicit running hour defined in this experiment (no *symlink*).


Walking on the wild side
------------------------

On the local server of your SWAPP account, go to the admin script repository:

.. code-block:: console

    % cd $HOME/swapp/admin

and run the *walk* utility with the *vortexify* subbcommand:

.. code-block:: console

    % ./walk.pl *username* vortexify *full-path-to-experiment*

For example:

.. code-block:: console

    % ./walk.pl groucho vortexify /home/gmap/groucho/experiments/VORTEXIFY/A0UD

Some Cleaning
-------------

In the brand new *VORTEX* experiment, you may need to remove the following variables :

  * SWAPP_XXT ...

Add the following variables:

  * VORTEX_APP
  * VORTEX_CONF
  * VORTEX_NAMESPACE
  * GEOMETRY
  