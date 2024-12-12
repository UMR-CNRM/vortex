========
Tutorial
========

This tutorial will guide you throughout writing a simple vortex
script.  This script will result in the execution of a Python program
whose behavior resembles this of a numerical weather prediction
forecast program.

To run succesfully, the program must be able to read two files in the
current directory:

- A file named ``ICSHMFCSINIT``, containing input data required by the
  program to run.  You can think of it as a file containing forecast
  initial condition data.

- A file named ``fort.4``, describing configuration keys and values
  required by the program. In this example, this file only specifies
  the value of a configuration key ``TERM`` which determines how many
  result files will be written to disk.  You can think of this
  configuration as the analoguous of a forecast term.

Therefore, prior to running our fake forecast program, our working
directory must look like this:

::

    fake-forecast.py
    fort.4
    ICMSHFCSINIT

Supposing the content of the configuration file ``fort.4`` is

::

    # fort.4
    TERM=3

after running the fake forecast program, the working directory will
contain three extra files to look like this:

::

    fake-forecast.py
    fort.4
    ICMSHFCSINIT
    ICMSHFCST+01:00.grib
    ICMSHFCST+02:00.grib
    ICMSHFCST+03:00.grib


Initial set up
--------------

To work through this tutorial, you will need to download the
:download:`input data archive <vortex-tutorial-data.zip>` and extract
its content on your computer. The exctraction location doesn't matter,
as long as it is somewhere where you have read and write access.

The archive contains the following files:

- ``fake-forecast.py``: A Python script that reads in a data file and a
  configuration file, both expected to be present in the current
  directory, and writes a set of files ``ICMSHFCST+01:00.grib``,
  ``ICMSHFCST+02:00.grib``, ``ICMSHFCST+03:00.grib``.  The number of output
  files is specified by the content of the configuration file.
- ``forecast_configuration_files/main_arpege.nam``: A configuration
  file consisting of one ``KEY=VALUE`` pair per line.
- ``data_tree``: The root directory for the *vortex data tree*, from
  which input files are fetched from and ouput files written to.

.. note::

   The examples in this tutorial assume that the tutorial data archive
   was extracted in directory ``/home/user``.  Be sure to replace this
   path by the path to the directory where your extracted the tutorial
   data archive.


This tutorial is a guide to writing a Python script, using the
*vortex* library, to fetch required input data from the data tree
directory, run the ``fetch-forecast.py`` program, and write output
files to the data tree.

Start by creating a empty directory. The location and name do not
matter and we'll just call it ``vortex-tutorial``.  Using your
favorite text editor, create a new Python file ``run-forecast.py`` and
write the following lines to it:

.. code:: python

   # run-forecast.py

   import vortex as vtx

   vtx.config.set_config(
       section="data-tree",
       key="rootdir",
       # Be sure to replace "/home/user/" by the path where you
       # extracted the tutorial data archive.
       value="/home/user/vortex-tutorial-data/vortex_data_tree",
   )

   print(
       "The data tree root is",
       vtx.config.from_config("data-tree", "rootdir"),
   )

The call to :py:func:`vortex.config.set_config` specifies the location
of the vortex data tree, a directory hierarchy that holds data files
that *vortex* can fetch data from and write data to. By default, the
data tree is located in the user's home directory, but for the purpose
of this tutorial you will configure the data tree root node to be the
directory ``vortex_data_tree`` located within the tutorial data files.

.. tip::

   You can run the script with ``python -i`` to execute the script in an
   interactive Python session.

.. seealso::

   See :doc:`../user-guide/configuration` for more information about
   configuring *vortex*, including setting an alternative location for
   the data tree.


Fetching input data
-------------------

Use the :py:func:`vortex.input` function to define an input resource
for the initial condition input file:

.. code:: python

    handlers = vtx.input(
        kind="analysis",
        date="2024082600",
        model="arpege",
        cutoff="production",
        filling="atm",
        geometry="global1798",
        nativefmt="grib",
        vapp="tutorial",
        vconf="fake-forecast",
        experiment="vortex-tutorial",
	block="4dupd2",
        local="ICMSHFCSTINIT",
    )

The :py:func:`vortex.input` function returns a list of objects of type
:py:class:`Handler <vortex.data.handlers.Handler>`.  In our case, this
list contains only a single item mapping to the initial condition
file.

.. code:: python

   initial_condition = handlers[0]

An instance of :py:class:`Handler <vortex.data.handlers.Handler>` is
able to compute the file path to the underlying physical file:

.. code:: python

    initial_condition.locate()

This path is computed from the values of the arguments passed to the
:py:func:`vortex.input` function. This path can be *computed* because
the initial condition file is a *ressource* that was stored by another
vortex script.  Its location is therefore well defined within a
standardised data tree layout, see :doc:`../user-guide/data-layout`.

.. note::

   The :py:func:`vortex.input` function does not actually fetch the
   corresponding file into the current working directory, it only
   *defines* (a) :py:class:`Handler <vortex.data.handlers.Handler>`
   object(s) that provide(s) access to the :py:func:`get
   <vortex.data.handlers.Handler.get>` method.

To fetch the file into the current working directory, use the
:py:func:`get <vortex.data.handlers.Handler.get>` method on the
resource handler:

.. code:: python

    initial_condition.get()

The second step is to fetch the configuration file in the current
working directory, as a file named ``fort.4`` since this is what the
fake forecast expects.

Similarly to the initial condition file, use the
:py:func:`vortex.input` function again:

.. code:: python

    config_file = vtx.input(
        kind="namelist",
	model="arpege",
        remote="/home/user/vortex-tutorial-data/forecast_configuration_files/main_arpege.nam",
        local="fort.4",
    )[0]

.. attention::

   Be sure to replace ``/home/user`` by the path to the directory
   where you extracted the tutorial data.

The call to :py:func:`vortex.input` is much simpler. This time, the
path to the configuration file is specified explicitly using the
`remote` argument, instead of being computed by *vortex* from the
arguments of :py:func:`vortex.input`.

.. seealso::

   See :doc:`../user-guide/explicit-paths`.

Finally, use the :py:func:`get <vortex.data.handlers.Handler.get>`
method on the ``config_file`` handler to fetch the file into the
current working directory.

.. code:: python

    config_file.get()

You can verify that a new file named ``fort.4`` was created in the
current working directory. This file is in fact a (hard) link pointing
to the location specified as a value to the ``remote`` argument to
:py:func:`vortex.input`.

Running the fake forecast program
---------------------------------

With the input data files copied into the current working directory,
you are now ready to run the program.  You will first fetch the
program itself -- in this case a Python script -- into the current
working directory, then instanciate an *algorithmic component* object
which will be responsible to actually run the script.

Fetching the fake forecast program
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The VORTEX library considers programs, whether they are scripts
written in interpreted languages or compiled binaries, as
*executables*. Fetching an executable is similar to fetching an input
data file:

.. code:: python

    exe = vtx.executable(
        kind="script",
        language="python",
	# Replace "/home/user" by the path to the directory you
	# extracted the tutorial data to.
        remote="/home/user/vortex-tutorial-data/fake-forecast.py",
        local="fake-forecast.py",
    )[0]

Similarly to :py:func:`vortex.input`, ``vortex.executable`` returns a
list of instances of the :py:class:`Handler
<vortex.data.handlers.Handler>` class, which you can call :py:func:`get
<vortex.data.handlers.Handler.get>` on:

.. code:: python

    # Fetch the Python script into the current working directory
    exe.get()

Running the script through an algo component
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The *vortex* library provides a collection of classes that define how to
run specific programs.  These classes are referred to as *algorithmic components*.

Algorithmic components classes are instanciated using the
:py:func:`vortex.task` function:

.. code:: python

    task = vtx.task(
        interpreter="python",
        engine="exec",
    )

With ``interpreter="python"`` and ``engine="exec"``, the ``vtx.algo``
returns an instance of :py:class:`vortex.algo.components.Expresso`.
This class encapsulates behavior required the run a Python script,
potentially setting up environment variables like ``PYTHONPATH`` or
switching to a different Python interpreter.

Finally, the script can be run using the ``run`` method on the ``task``
object, which takes an executable object as a argument.

.. code:: python

    task.run(exe)

At this point, the script ran and produced 3 files ``ICMSHFCST+01:00.grib``,
``ICMSHFCST+02:00.grib`` and ``ICMSHFCST+03:00.grib`` in the current working
directory.  The next step is to store them into the vortex data tree,
so that they can be retrieved later by other vortex scripts.

Storing outputs into the data tree
----------------------------------

In this section we use the :py:func:`vortex.output` function to store
the files generated by the fake forecast program into the :doc:`vortex
data tree <../user-guide/data-layout>`. This way, subsequent *vortex*
scripts will be able to retrieve them using the
:py:func:`vortex.input` function.

Storing files in the data tree is achieved by calling the
:py:func:`vortex.output`. Its interface is identical to
:py:func:`vortex.input`'s:

.. code:: python

    historic_files = vtx.output(
        kind="modelstate",
        date="2024082600",
        model="arpege",
        cutoff="production",
        geometry="global1798",
        nativefmt="grib",
        vapp="tutorial",
        vconf="fake-forecast",
        experiment="vortex-tutorial",
        term=[1, 2, 3],
	block="forecast",
        local="ICMSHFCST+[term].grib",
    )

The :py:func:`vortex.output` function returns a list Handlers
instances whose :py:func:`put <vortex.data.handlers.Handler.put>`
method works in the opposite direction of :py:func:`get
<vortex.data.handlers.Handler.get>`: instead of reading files from the
data tree, it writes to it files present in the current working
directory that are named as the value passed to the ``local`` argument
to :py:func:`vortex.output`.

Note the addition of the argument ``term``, also referenced within the
string passed to ``local``:

.. code:: python

     historic_files = vtx.output(
       # ...
       term=[1, 2, 3],
       local="ICMSHFCST+[term].grib",
    )

Values of arguments to functions such as :py:func:`vortex.input`,
:py:func:`vortex.output` or :py:func:`vortex.executable` can reference
the values of other arguments. Sequence are expanded into as many
elements as they contain. In this case, ``vtx.output`` returns a list
of 3 :py:class:`Handler <vortex.data.handlers.Handler>` objects instead
of a single object.

Finally, calling :py:func:`put <vortex.data.handlers.Handler.put>` on
the handlers will write the files into the data tree:

.. code:: python

    for handler in historic_files:
        handler.put()

You can now list the content of the ``forecast`` block to check that the
3 files where indeed written there:

.. code:: shell

    DATATREE_ROOT=<tutorial/data>/vortex_data_tree
    ls -l $DATATREE_ROOT/tutorial/fake-forecast/vortex-tutorial/20240826T0000P/forecast

.. _setting-default-values:

Setting default values
----------------------

Definitions of vortex inputs and outputs often feature the same
arguments and values. Vortex provides the :py:func:`vortex.defaults`
function, which can be used to prevent repeating arguments to
functions :py:func:`vortex.input`, :py:func:`vortex.output` or
:py:func:`vortex.executable`.

Using :py:func:`vortex.defaults`, the script becomes:

.. code:: python

    import vortex as vtx

    vtx.config.set_config(
        section="data-tree", key="rootdir",
	value="/home/user/vortex-tutorial-data/vortex_data_tree",
     )

    vtx.defaults(
        date="2024082600",
        model="arpege",
        cutoff="production",
        geometry="global1798",
	nativefmt="grib",
        vapp="tutorial",
        vconf="fake-forecast",
        experiment="vortex-tutorial",
    )

    initial_condition = vtx.input(
        kind="analysis",
        filling="atm",
        local="ICMSHFCSTINIT",
        block="4dupd2",
    )[0]
    initial_condition.get()

    config_file = vtx.input(
        kind="namelist",
        remote="/home/user/vortex-tutorial-data/forecast_configuration_files/main_arpege.nam",
        local="fort.4",
    )[0]
    config_file.get()

    exe = vtx.executable(
        kind="script",
        language="python",
        remote="/home/user/vortex-tutorial-data/fake-forecast.py",
        local="fake-forecast.py",
    )[0]
    exe.get()

    vtx.task(interpreter="python", engine="exec").run(exe)

    for output_handler in vtx.output(
        kind="modelstate",
        nativefmt="grib",
        local="ICMSHFCST+[term].grib",
        block="forecast",
        term=[1, 2, 3],
    ):
        output_handler.put()

.. attention::

   Be sure to replace ``"/home/user"`` by the path to the directory
   you extracted the tutorial data to.

A post-processing task
----------------------

We conclude this tutorial by implementing a second vortex script,
which will illustrate the way outputs of one vortex script can be used
as inputs of another.

This new vortex script will:

1. fetch all three forecast output files

2. concatenate them

3. write the resulting file back into the data tree

Open a new file ``aggregate-task.py`` and start with calling
:py:func:`vortex.input`:

.. code:: python

    import vortex as vtx

    vtx.config.set_config(
       section="data-tree",
       key="rootdir",
       # Be sure to replace "/home/user/" by the path where you
       # extracted the tutorial data archvie.
       value="/home/user/vortex-tutorial-data/vortex_data_tree",
   )

    vtx.defaults(
        date="2024082600",
        model="arpege",
        cutoff="production",
        vapp="tutorial",
        vconf="fake-forecast",
        experiment="vortex-tutorial",
        geometry="global1798",
    )

    historic_files = vtx.output(
        kind="modelstate",
        nativefmt="grib",
        term=[1, 2, 3],
        local="ICMSHFCST+[term].grib",
        block="forecast",
    )

    for handler in historic_files:
        handler.get()

.. note::

   Because the location of the data tree root is different from the
   default ``$HOME/.vortex.d``, it is necessary to call
   :py:func:`vortex.config.set_config` again at the beginning of the
   script.

   For convenience, we could instead use the default location or
   specify the location of the data tree in the :doc:`configuration
   <../user-guide/configuration>`.


Observe that the arguments specified are identical to those provided
to the :py:func:`vortex.output` function in section
:ref:`Setting-default-values`.

With the three files present in the working directory, let's
concatenate them:

.. code:: python

    with open("result.txt", "w") as target:
        for handler in historic_files:
            with open(handler.container.localpath(), "r") as source:
                target.writelines(source.readlines())

Finally, we write the resulting file into the data tree:

.. code:: python

    vortex.output(
        kind="dhh",
        scope="global",
        nativefmt="lfi",
        block="postprocessing",
    ).put()

.. code:: shell

    DATATREE_ROOT=/home/user/vortex-tutorial-data/vortex_data_tree
    ls -l $DATATREE_ROOT/tutorial/fake-forecast/vortex-tutorial/20240826T0000P/postprocessing
