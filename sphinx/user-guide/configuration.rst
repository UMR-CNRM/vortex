====================
Configuring *vortex*
====================

The default behavior of *vortex* can be modified by altering the *configuration*.
The configuration is a set of *sections*, which themselves are sets of ``key=value`` pairs.

The configuration can be modified using two functions:

- :py:func:`config.set_config <vortex.config.set_config>`: Set a given key within a section to a value.
- :py:func:`config.load_config <vortex.config.load_config>`: Set multiple keys from a TOML file.

The value of a specific key can be queried using
:py:func:`config.from_confi <vortex.config.from_config>`.  It is also
possible to print the entire configuration using
:py:func:`config.print_config <vortex.config.print_config>`.

.. seealso::

   :doc:`../reference/configuration`

``data-tree``
^^^^^^^^^^^^^

``rootdir``

The path to the root directory for the data tree. Can be absolute or
relative to the current working directory.

**Type**: Abritrary string.

**Default value**: ``"$HOME/.vortex.d"``

``op_rootdir``

The path to the root directory for the additional data tree used by
special experiments ``oper`` and ``dble``.  If unspecified, *vortex*
will only lookup data files in the local data tree, and remote data
trees if they are specified.

**Type**: Arbitrary string.

**Default value**: None

``storage``
^^^^^^^^^^^

``address``

The address of the server hosting a remote data tree.

**Type**: Arbitrary string.

**Default value**: None

``rootdir``

The path to the root directory for the remote data tree. Can be absolute or
relative to the user's home directory on the remote machine.

**Type**: Arbitrary string.

**Default value**: ``"$HOME/.vortex.d"``

``op_rootdir``

The path to an alternative data tree specific to the ``oper`` and ``dble``
special experiments.

**Type**: Arbitrary string.

**Default value**: ``storage:rootdir``.

``export_mapping``

TODO

**Type**: boolean

**Default value**: ``false``

``usejeeves``

TODO

**Type**: boolean

**Default value**: ``false``


``mpitool``
^^^^^^^^^^^

``mpiname``

Command name for the MPI launcher to use.

**Values**:

- ``"mpirun"``:  Standard MPI launcher on most systems: ``mpirun``.
- ``"srun"``: Slum's ``srun`` launcher.
- ``"openmpi"``: OpenMPI's ``mpirun`` launcher.
- ``"mpiauto"``: *mpiauto* proxy launcher.
- ``"srun-ddt"``: Slurm's ``srun`` launcher with support for the Arm
  Distributed Debugging Tool.
- ``"openmpi-ddt"``: OpenMPI's ``mpirun`` launcher with support for
  the Arm Distributed Debugging Tool.

**Default**: ``"mpirun"``

``mpilauncher``

Path to the MPI launcher executable.  Must be absolute.

If unspecified, the command name is inferred form the value of
``mpitool:mpiname`` and must be found in the shell's command path.

**Type**: Arbitrary string.

**Optional**

``mpiopts``

Option flags to pass the MPI launcher command.

**Type**: Arbitrary string

**Default value**: ``""``

``mpienv``
^^^^^^^^^^

This section defines environment variables that will be exported prior
to running an MPI executable.

The section keys are arbitrary, and correspond to the name of the
environment variables to be exported.  The associated values
correspond to the value to give the environment variable.

.. topic:: Example

   .. code:: toml

      [mpienv]
      DAPL_ACK_RETRY = "7"
      DAPL_ACK_TIMER = "20"
      DAPL_IB_SL = "0"
      I_MPI_DAPL_UD = "on"
      I_MPI_DAPL_UD_PROVIDER = "ofa-v2-mlx5_0-1u"

.. attention::

   All values are **strings**.

``nwp-tools``
^^^^^^^^^^^^^

``lfi``

Path to a directory containing the LFI commands such as ``lfi_copy``
or ``lfi_merge``.  The path should be absolute.

**Type**: Arbitrary string

``odb``

Path to a directory containing the ``create`` and ``merge`` "ioassign"
commands. The path should be absolute.

``iomerge_cmd``

Name of the merge command.

**Type**: string

**Default value**: ``"merge_ioassign"``

``iocreate_cmd``

Name of the create command.

**Type**: string

**Default value**: ``"create_ioassign"``

``fortran``
^^^^^^^^^^^

This section defines environment variables that will be exported prior
to running a NWP model executable.

The section keys are arbitrary, and correspond to the name of the
environment variables to be exported.  The associated values
correspond to the value to give the environment variable.

.. topic:: Example

   .. code:: toml

      [fortran]
      OMP_STACKSIZE = "4G"
      KMP_BLOCKTIME = "12"
      OMP_WAIT_POLICY = "ACTIVE"
      TBB_MALLOC_USE_HUGE_PAGES = "1"
      MKL_CBWR = "AUTO,STRICT"

.. attention::

   All values are **strings**.

``ssh``
^^^^^^^

Some operations carried out by vortex require establishing a SSH
connection with a remote machine. A common example is sending a
request to a remote server from a compute node without network
access. In such a case the request would be sent from another machine,
through SSH.

``sshcmd``

Name of the SSH client executable.

**Type**: string

**Default value**: ``ssh``

``scp``

Name of the SSH copy client executable.

**Type**: string

**Default value**: ``scp``

``sshopts``

Options to pass the SSH client executable

**Type**: string

**Default value**: ``""`` (empty string)

``scpopts``

Options to pass the SSH copy client executable

**Type**: string

**Default value**: ``""`` (empty string)

Value for the above configuration options can be set for specific
machine by specifying the configuration key as the option name
(e.g. ``sshopts``) followed by a regular expression matching the
machine's hostname, separated by a dot. When specifying options for
one or more hostname pattern, a defaut configuration value *must* be
declared using the ``default`` keyword (e.g. ``sshopts.default``).

.. topic:: Example

   .. code:: toml

      [ssh]
      sshcmd = "/usr/bin/ssh"
      scpcmd = "/usr/bin/scp"
      sshopts.default = "-x -o NoHostAuthenticationForLocalhost=true -o PasswordAuthentication=false -o ConnectTimeout=6"
      sshopts."sotrtm\\d\\d-sidev" = "-x -o PasswordAuthentication=false"

.. attention::

   According to the `TOML specification
   <https://toml.io/en/v1.0.0#string>`_ , special characters used in
   regular expressions, such as backslashes, must be escaped.

``ecflow``
^^^^^^^^^^

``clientpath``

Path to the EcFlow client executable.

**Type**: string

**Default value**: ``ecflow_client``

``sshproxy_wait``

**Default value**: 6

``sshproxy_wait``

**Default value**: 2

``sshproxy_retrydelay``

**Default value**: 1

``services``
^^^^^^^^^^^^

``cluster_names``

A list of allowed cluster names, e.g ``["belenos", "taranis"]``

