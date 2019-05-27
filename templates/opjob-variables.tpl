=========================================================================
LIST OF ALL AVAILABLE VARIABLES THAT CAN BE USED TO MAKE AN OPER_LIKE JOB
=========================================================================

MANDATORY EXPLICIT VARIABLES :
    - name      : Job name without '.py', you must always define it explicitly somewhere (either in the 'create_job' file, or with the '-n' or -j'  options).
    - task      : Name of the task file that is to be launched by the job, you must always define it explicitly somewhere (either in the 'create_job' file, or with the '-n' or -j'  options).

MANDATORY IMPLICIT VARIABLES :
    - nnodes    : SBATCH variable. Number of nodes for the job, default=1. Always put it in the conf file.
    - ntasks    : SBATCH variable. Number of tasks for the job, default=6. Always put it in the conf file.
    - openmp    : SBATCH variable.  Default=4. Always put it in the conf file.
    - cutoff    : Cutoff of the job, default=production. Always put it in the conf file.

IMPORTANT BUT NOT NECESSARY MANDATORY VARIABLES :
    - time      : SBATCH variable. Time limit for the job, default=00:20:00. Put it in the conf file if necessary.
    - rundate   : Date and time of the run ('yyyymmddhh' format), default=None. Leave it at None exept if you want to run your job at a specific date.
    - mail      : Switch mails on or off. This value is automatically set at True with otpion -o and at False in any other case.
    - hasmember : Pick the template with the members. This value is automatically set at False in all cases. If your task uses member, you should switch on True this variable.
    - suitebg   : Backgroud of the application (defines in which environment it takes its resources). If suitebg=None (default mode) it is then set to 'xpid' so if 'xpid' is not oper or dble, suitebg has to be specified with option -a.
    - refill    : Bool that set the step to 'refill' in the 'recextfiles' jobs (see vortex/layout/nodes.py for informations on the steps mecanism), default=False.
    - partition : SBATCH variable. Default=oper, automatically set to ft-oper if refill=True.

OTHER VARIABLES :
    - python    : Python version, set by default as the one used by Vortex (see the python alias in the .bashrc file).
    - pyopts    : Python options, default='-u'.
    - mem       : SBATCH variable. Memory of the job, default=62000.
    - exclusive : SBATCH variable. Default='exclusive'.
    - verbose   : SBATCH variable. Default=True.
    - runtime   : Time of the run, default=None. Leave it at None exept if you want to run your job on at specific time.
    - runstep   : Step of the run, default=None.
    - fullplay  : Execution mode : full execution if True, else only inputs are runned. Default=True. Leave it at True.
    - jeeves    : Name of the jeeves repository, default=async. Leave it at its default value.
    - package   : Name of the repository where the script to launch is located. Default=Tasks.
    - account   : SBATCH variable. default=mxpt001
