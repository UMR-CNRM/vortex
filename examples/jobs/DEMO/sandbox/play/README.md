# Example of jobs using `mkjob`

These jobs use the `sandbox` package and the very special `DEMO`
Vortex experiments. For these experiments, dedicated providers and stores
are defined in order to run solely on a local machine (i.e. there is no need
to access a mass storage system). However, the behaviour of a "real" job
is retained as much as possible.

* The archived data are stored in the `examples/demoarchive` subdirectory of
  the Vortex source code package;
* The Vortex cache is located in the user's home directory in
  `~/.vortexrc/democache` (it will not be cleaned at the end).

In the following example, the `void` profile is used. It implies that the
job will run locally and that the working directory will be located in
`./run/tmp`. If the job succeeds, the working directory is removed. if it
fails, the working directory content is moved to `./run/abort`. 

All of the examples available in this directory demonstrate various capabilties
of the Vortex's job creation system. To do so, the "fake" task `Beacon` is used
)see `tasks/commons.py`). It just creates a very small JSON and stores it in
the cache. For demonstration purposes, the `Beacon` tasks can be asked to fail
(by setting `failer=True` in the configuration file or at object creation time)  

## Demonstration of the `on_error` feature and of the use of a custom JobAssistant plugin

To launch the demo:
    
    cd jobs
    ../vortex/bin/mkjob.py -j profile=void \
        name=on_error_feature_job task=on_error_feature \
        rundate=2020102918
    python ./on_error_feature_job.py

Look at the code in `tasks/on_error_feature.py` in order to get some
explanation on the `on_error` feature.

In this job, the `ConfigFileAccessJobAssistantPlugin` JobAssistant's plugin
is used (because `loadedjaplugins = configfile_access` in the configuration)
file. The code of the plugin can be found in `tasks/commons.py`. Its purpose
is to access the application's configuration and export (to the environment)
any entry starting with "useless". This is a way to setup job-wide
environement variables.

## Demonstration of the `LoopFamily` class

To launch the demo:
    
    cd jobs
    ../vortex/bin/mkjob.py -j profile=void \
        name=loop_family_job1 task=loop_family1 \
        rundates=2020102918-2020110118-PT24H
    python ./loop_family_job1.py

The `Beacon` task will be started on :

* Several dates ("2020102918", 2020103018" and "2020103118". We will see we
  "2020110118" is "ignored")
* And several members (the member's list lies in the configuration file)

Look at the code in `tasks/loop_family1` for more explanations.

## Demonstration of the `active_callback.py` feature

To launch the demo:
    
    cd jobs
    ../vortex/bin/mkjob.py -j profile=void \
        name=active_cb_job task=active_cb \
        rundate=2020102918
    python ./active_cb_job.py

The `active_callback` feature allows to activate some nodes only on particular
conditions. In this example, too instances of the `Beacon` task will be
started if the member's number is even (only one instance otherwise).

Look at the code in `tasks/active_cb.py` for more explanations.

## Demonstration of the `paralleljobs` feature

To launch the first demo:
    
    cd jobs
    ../vortex/bin/mkjob.py -j profile=void \
        name=paralleljobs_basic_job task=paralleljobs_basic \
        rundate=2020102918
    python ./paralleljobs_basic_job.py

The `paralleljobs` feature allows to execute the content of a Family in
parallel. 

Look at the code in `tasks/paralleljobs_basic.py` for more explanations.

To launch the second demo:
    
    cd jobs
    ../vortex/bin/mkjob.py -j profile=void \
        name=paralleljobs_workshares_job task=paralleljobs_workshares \
        rundate=2020102918
    python ./paralleljobs_workshares_job.py

In addition to the `paralleljobs` feature it uses the `WorkshareFamily` to
provide additional flexibility.

Look at the code in `tasks/paralleljobs_workshares.py` for more explanations.