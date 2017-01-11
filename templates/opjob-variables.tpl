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
    - suitebg   : Backgroud of the application (defines in which environment it takes its resources), default=oper. Always put it in the conf file.
    - cutoff    : Cutoff of the job, default=production. Always put it in the conf file.

IMPORTANT BUT NOT NECESSARY MANDATORY VARIABLES :
    - time      : SBATCH variable. Time limit for the job, default=00:20:00. Put it in the conf file if necessary.
    - rundate   : Date and time of the run ('yyyymmddhh' format), default=None. Leave it at None exept if you want to run your job on a specific date.
    - mail      : Switch mails on or off, default=False. You can change this value with otpion -o (switch to True) or -t (switch to False) of this script.
    - rootapp   : Only for test configurations. Determines the way the job will be launched (either with sms of a sbatch command).
    - refill    : Bool that set the step to 'refill in the 'recextfiles' jobs (see vortex/layout/nodes.py for informations on the steps mecanism), default=False.

OTHER VARIABLES :
    - python    : Python version, set by default as the one used by Vortex (see the python alias in the .bashrc file).
    - pyopts    : Python options, default='-u'.
    - mem       : SBATCH variable. Memory of the job, default=62000.
    - partition : SBATCH variable. Default=oper.
    - exclusive : SBATCH variable. Default='exclusive'.
    - verbose   : SBATCH variable. Default=True.
    - alarm     : Switch alarm on or off, default=True. Not currently used.
    - archive   : Switch archive on or off, default=True. Not currently used.
    - fullplay  : Execution mode : full execution if True, else only inputs are runned. Default=True. Leave it at True.
    - jeeves    : Name of the jeeves repository, default=async. Leave it at its default value.

