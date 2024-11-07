========
Tutorial
========


This tutorial will guide you throughout writing a simple vortex
script.  This script will result in the execution of a Python program
which behavior resembles this of a numerical weather prediction
forecast program.

To run succesfully,l the program must be able to read two files in the
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
contain threep extra files to look like this:

::

    fake-forecast.py
    fort.4
    ICMSHFCSINIT
    ICMSHFCST+1.grib
    ICMSHFCST+2.grib
    ICMSHFCST+3.grib

Fecthing input data
-------------------

To work through this tutorial, you will need to download the input
data archive and extract its content on your computer.  The
exctraction location doesn't matter, as long as it is somewhere where
you have read and write access.

It's time to write some Python code. Use the ``vortex.input`` function
to define an input resource for the initial condition file:

.. code:: python

    import vortex as vtx

    initial_condition = vtx.input(
        kind="analysis",
        date="2024082600",
        model="arpege",
        cutoff="production",
        filling="atm",
        geometry="franmgsp",
        nativefmt="grib",
        vapp="vapp",
        vconf="vconf",
        experiment="vortex-tutorial",
        archive=False,
        local="ICMSHFCSTINIT",
    )

The ``vortex.input`` function returns an object of type ``Handler``,
representing the initial condition file.  An instance of ``Handler`` is
able to compute the file path to the underlying physical file:

.. code:: python

    initial_condition.locate()

This path is computed from the values of the arguments passed to the
``vortex.input`` function.  This path can be *computed* because the
initial condition file is a *ressource* that was stored by another
vortex script.  Its location is therefore well defined in the
standardised vortex data layout. See ?? for more information regarding
the the vortex data layout.

To fetch the file into the current working directory, simply use the
``Handler.get`` method:

.. code:: python

    initial_condition.get()

We then need to fetch the configuration file in the current working
direcotry, as ``fort.4``.  Similarly to the initial condition file, use
the ``vortex.input`` again

.. code:: python

    config_file = vtx.input(
        kind="namelist",
        remote="../forecast_configuration_files/main_arpege.nam",
        local="fort.4",
    )

This time the call to ``vortex.input`` is much simpler, the path to the
configuration file is specified explicitly.

Finally, use the ``get`` method on the ``config_file`` handler to fetch
the file into the current directory, with the name ``fort.4``:

.. code:: python

    config_file.get()

Running the fake forecast program
---------------------------------

With the input data files copied into the current working directory,
we are ready to run the program.  We will first fetch the program
itself -- in this case a Python script -- into the current working
directory, then instanciate an *algorithmic component* object which
will allow use to actually run the script.

Fetching the fake forecast program
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The VORTEX library considers programs, whether they are scripts
written in interpreted languages or compiled binaries, as
*executables*. Fecthing an executable is similar to fecthing an input:

.. code:: python

    exe = vtx.executable(
        kind="script",
        language="python",
        remote="../../fake-forecast.py",
        local="fake-forecast.py",
    )

Similarly to ``vortex.input``, ``vortex.executable`` returns an instance of
``Handler``, which you can call ``get`` on:

.. code:: python

    # Fetch the Python script into the current working directory
    exe.get()

Running the script through an algo component
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The VORTEX library provides a collection of classes that define how to
run specific programs.  These classes are referred to as *algorithmic components*.

Algorithmic components classes are instanciated using the
``vortex.algo`` function:

.. code:: python

    algo = vtx.algo(
        interpreter="python",
        engine="exec",
    )

With ``interpreter="python"`` and ``engine="exec"``, the ``vtx.algo``
returns an instance of ``Expresso``.  This class encapsulates behavior
required the run a Python script, potentially setting up environment
variables like ``PYTHONPATH`` or switching to a different Python
interpreter.

Finally, the script can be run using the ``run`` method on the ``algo``
object, which takes an executable object as a argument

.. code:: python

    algo.run(exe)

At this point, the script ran and produced 3 files ``ICMSHFCST+0.grib``,
``ICMSHFCST+1.grib`` and ``ICMSHFCST+2.grib`` in the current working
directory.  The next step is to store them into the vortex data tree,
so that they be later retrieved by other vortex scripts.

Storing outputs into the data tree
----------------------------------

In this section we use the ``vortex.output`` function to store the files
generated by the fake forecast program into a location form where
later VORTEX scripts will be able to retrieve them.

You can think of this third step as writing outputs into the data
tree, next to inputs.  This way, an output from a vortex script can
act as an input of anoother.

Calling the ``vortex.output`` function is very similar to calling
``vortex.input``:

.. code:: python

    initial_condition = vtx.output(
        kind="modelstate",
        date="2024082600",
        model="arpege",
        cutoff="production",
        geometry="franmgsp",
        nativefmt="grib",
        vapp="vapp",
        vconf="vconf",
        experiment="vortex-tutorial",
        archive=False,
        term=[1, 2, 3],
        local="ICMSHFCST+[term].grib",
     )

It works in reverse from ``input``: instead of fetching files from the
data tree, it writes to it files present in the current working
directory that are named as the value passed to the ``local`` argument
to ``output``.

Note the addition of the argument ``term``, also referenced within the
string passed to ``local``:

.. code:: python

     historic_files = vtx.output(
       # ...
       term=[1, 2, 3],
       local="ICMSHFCST+[term].grib",
    )

Values of arguments to functions such as ``input``, ``output`` or
``executable`` can reference the values of other arguments.  If a value
is a sequence, then it is expanded into as many elements are there are
in the sequence.  In this case, ``vtx.output`` returns a list of
``Handler`` objects instead of a single object.

For example, the above call to ``output`` is equivalent to:

.. code:: python

    historic_files = [
        vtx.output(
            # ...
            term=term,
            local=f"ICMSHFCST+{term}.grib",
        )
        for term in range(1,4)
    ]

Finally, calling ``put`` on the handlers will write the files into the
data tree:

.. code:: python

    for handler in historic_files:
        handler.put()

You can now list the content of the ``forecast`` block to check that the
3 files where indeed written there:

.. code:: python

    ROOT=cache/vortex/tutorials/fake-forecast
    ls -l $ROOT/vortex-tutorial/20240826T0000P/forecast

Setting default values
----------------------

Definitions of vortex inputs and outputs often feature the same
arguments and values.  Vortex provides the ``defaults`` function, which
can be used to prevent repetition of arguments.

Using ``vortex.defaults``, the script becomes:

.. code:: python

    import vtx

    vtx.defaults(
        date="2024082600",
        model="arpege",
        cutoff="production",
        geometry="franmgsp",
        nativefmt="grib",
        vapp="vapp",
        vconf="vconf",
        experiment="vortex-tutorial",
        archive=False,
        term=[1, 2, 3],
    )

    initial_condition = vtx.input(
        kind="analysis",
        local="ICMSHFCSTINIT",
    )

    config_file = vtx.input(
        kind="namelist",
        remote="../forecast_configuration_files/main_arpege.nam",
        local="fort.4",
      )

    exe = vtx.executable(
        kind="script",
        language="python",
        remote="../../fake-forecast.py",
        local="fake-forecast.py",
    )

    vtx.algo(interpreter="python", engine="exec").run(exe)

    for output_handler in vtx.output(
        kind="modelstate",
        local="ICMSHFCST+[term].grib",
    ):
        output_handler.put()

A post-processing task
----------------------

We conclude this tutorial by implementing a subsequent vortex script,
illustring how outputs of one vortex script can be transparently used
as inputs of another.

This new vortex script will:

1. fetch all three forecast output files

2. concatenate themp

3. write the resulting file back into the data tree

Open a new file ``aggregate-task.py`` and start with calling ``vortex.input``:

.. code:: python

    import vortex as vtx

    vortex.defaults(
        date="2024082600",
        model="arpege",
        cutoff="production",
        vapp="tutorial",
        vconf="fake-forecast",
        experiment="vortex-tutorial",
        geometry="franmgsp",
        archive=False,
        term=[1, 2, 3],
    )

    historic_files = vtx.output(
        kind="modelstate",
        nativefmt="grib",
        local="ICMSHFCST+[term].grib",
        block="forecast",
    )

    for handler in historic_files:
        handler.get()

Observe that the arguments specified are identical to those provided
to the ``vortex.output`` function in section ??.

With the three files present in the working directory, let's
concatenate them:

.. code:: python

    with open("result.txt", "w") as target:
        for handler in historic_files:
            with open(handler.container.local, "r") as source:
                target.write(source.readlines())

Finally, we write the resulting file into the data tree:

.. code:: python

    vortex.output(
        kind="dhh",
        scope="global",
        nativefmt="lfi",
        block="postprocessing",
    ).put()
