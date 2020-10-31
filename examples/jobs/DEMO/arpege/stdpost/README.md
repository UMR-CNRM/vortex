# Example of jobs using `mkjob`

These jobs use the `sandbox` package and the very special `DEMO` and `DREF`
Vortex experiments (+ the `@demo` Uget location). For these experiments and
location, dedicated providers and stores are defined in order to run solely on
a local machine (i.e. there is no need to access a mass storage system).
However, the behaviour of a "real" job is retained as much as possible.

* The archived data are stored in the `examples/demoarchive` subdirectory of
  the Vortex source code package;
* The Vortex cache is located in the user's home directory in
  `~/.vortexrc/democache` (it will not be cleaned at the end).

In the following example, the `void` profile is used. It implies that the
job will run locally and that the working directory will be located in
`./run/tmp`. If the job succeeds, the working directory is removed. if it
fails, the working directory content is moved to `./run/abort`. 

## Simple post-processing job

To launch the demo:
    
    cd jobs
    ../vortex/bin/mkjob.py -j profile=void \
        name=single_b_job task=single_b_stdpost \
        rundate=2020102918
    python ./single_b_job.py

Some (fake) Grib files are fetched, a md5 sum is computed for each of them and
a summary JSON file is generated.

## Simple post-processing job with promises and other refinements

To launch the demo:
    
    cd jobs
    ../vortex/bin/mkjob.py -j profile=void \
        name=single_bp_job task=single_bp_stdpost \
        rundate=2020102918
    python ./single_bp_job.py

It does the same thing as previously but, in this example, input files
can be expected (e.g. promised by other tasks) and dealt with in arbitrary
order. More over, the output files are promised (consequently they are stored
in the cache as soon as they are produced). 

To iterate on several dates (within a same job):

    cd jobs
    ../vortex/bin/mkjob.py -j profile=void \
        name=single_bp_multidate_job task=single_bp_multidate_stdpost \
        rundates=2020102912-2020103000-PT6H
    python ./single_bp_multidate_job.py

To achieve that, the loop mechanism of the Vortex job management system is used 
(the `LoopFamily` class).

## Script based post-processing

To launch the demo:

    cd jobs
    ../vortex/bin/mkjob.py -j profile=void \
        name=single_s_job task=single_s_stdpost \
        rundate=2020102918
    python ./single_s_job.py

It does the same thing as previously but, in this example, an external script
is used in order to compute the md5 sum: From a pure python point of view, this
is useless however it acts as an example since most users want to launch their
own script/program to compute some post processing.

The script as a 1 second sleep inside; consequently the sequential processing
of each of the input file takes a while.

## Parallel script based post-processing

A parallelized version was created in order to counteract the 1 second sleep.
It rely on the `taylorism` package that launches several instances of the script
concurrently. To launch the demo:

    cd jobs
    ../vortex/bin/mkjob.py -j profile=void \
        name=single_s_para_job task=single_s_stdpost \
        rundate=2020102918
    python ./single_s_para_job.py

Note: The same task file is used (`single_s_stdpost`) but the job as a
different name (`single_s_para_job` instead of `single_s_job`). It allows us
to specify different configuration data (see `conf/arpege_stdpost.ini`) in
order to activate the parallelized version or not. It is one of the beauty
of the Vortex job management system that allows efficient code re-use thanks
to the application's configuration file. 
