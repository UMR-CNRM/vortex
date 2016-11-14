#!/opt/softs/python/2.7.5/bin/python
# -*- coding: utf-8 -*- 

import os, sys
import argparse
import string
from shutil import copyfile

import vortex
from iga.util import swissknife
from vortex.util.config import GenericConfigParser, load_template

# Export de la version de vortex à utiliser (celle de l'application concernée)
vortex_path = os.path.join(os.path.realpath(os.getcwd()).rstrip('/jobs'), 'vortex')
pathdirs    = [ os.path.join(vortex_path, xpath) for xpath in ('', 'site', 'src', 'bin') ]
for d in pathdirs :
    if os.path.isdir(d):
        sys.path.insert(0, d)

DEFAULT_JOB_FILE = 'create_job'

# A essayer de mettre en fichier de conf
sbatch_rootapp   = 'os.getcwd()'
sms_rootapp      = 'os.environ["DMT_PATH_EXEC"]'
test_template    = 'job-test-default.tpl'
oper_template    = 'job-oper-default.tpl'


def parse_command_line():
    description = "Create or modify vortex jobs for a specific application"
    parser = argparse.ArgumentParser(description=description)

    helpstr = 'file containing a list of dict describing all the jobs of the application (defaults to "{}").\n This file must have dict-like lines such as :\n name=jobname task=taskname '
    parser.add_argument('-f', '--file', help=helpstr.format(DEFAULT_JOB_FILE))
    parser.add_argument('-n', '--name', help="Name of je job to handle (must match the corresponding name in the 'jobs' file")
    parser.add_argument('-j', '--job', help="Command line (dict-like string) containing all informations to make a specific job, ex : \n 'name=jobname task=taskname'")
    parser.add_argument('-o', '--oper', help='Activate oper specifiactions in the jobs (op_mail=True, ad.route_on(),... The default option is the test configuration', action='store_true')
#    parser.add_argument('-t', '--template', help='Parse a specific template file to create the jobs (even if option -o is activated)')
    parser.add_argument('-a', '--add', help='Add (and replace if necessary) argument to the description of all the jobs concerned.')
    parser.add_argument('-w', '--write', help="If -j option is activated, add the command line to the 'jobs' file", action='store_true')
    parser.add_argument('-l', '--list', help='Only list the name of the jobs to handle, and exit', action='store_true')
    parser.add_argument('-s', '--sms',  help='Make a job in test configuration but that can be launched with sms.', action='store_true')
    parser.add_argument('-b', '--backup', help='Save old jobs before creating new ones with specified options', action='store_true')
    parser.add_argument('-v', '--verbose', dest='verbose', help='verbose mode', action='store_true')
    parser.add_argument('-i', '--info', help='Full list of available variables that can be used to make a job (according to the job template)', action='store_true')
     
    args = parser.parse_args()

    jobs = list()
    if not args.file:
        args.file = DEFAULT_JOB_FILE

    # Les descriptifs de jobs sont rangés dans une liste
    # Si un descriptif est passé manuellement (avec l'option -j) on ne traite que lui
    os.path.isfile(args.file)
    if not args.job and os.path.isfile(args.file):
        with open(args.file, 'r') as fp:
            for line in fp.readlines():
                if (args.name is None or args.name in line) and bool(line.rstrip()):
                    job = make_cmdline(line.rstrip())
                    jobs.append(job)
                         
    elif args.job:
        job = make_cmdline(args.job)
        jobs.append(job)
        if args.write:
            with open(args.file, 'a') as fp:
                fp.write(args.job + "\n") 
    else:
        print('No job description, nothing to do')
        sys.exit() 

    if args.add:
        newparams = make_cmdline(args.add)
        jobs = [ dict(job.items() + newparams.items()) for job in jobs ]
    
    for job in jobs:
        if 'template' not in job.keys():
            job['template'] = oper_template if args.oper else test_template 
        if 'inifile' not in job.keys():
            job['inifile'] = job['template'].split(".")[0]+'.ini'
        if not args.oper: 
            job['rootapp'] = sms_rootapp if args.sms else sbatch_rootapp

    return args, jobs



def list_jobs(jobs):
    print 'jobs traités :'
    for job in jobs:
        print job 

def make_cmdline(description):
    job_description = dict((k.strip(), v.strip()) for (k, v) in (item.split('=') for item in description.split(' ')))
    return job_description

def list_variables():
    t = vortex.ticket()
    core = load_template(t, 'opjob-variables.tpl')

    with open(core.srcfile, 'r') as f:
        for line in f:
            print line

def add_report(report, jobname, oper, sms, backup=False):
    if backup:
        report.append('Save the job ' + jobname + ' under ' + jobname + '_backup') 
    else:
        configuration = 'oper' if oper else ('test with sms' if sms else 'test without sms')
        report.append('Job ' + jobname + ' created in configuration ' + configuration)
    return report

def display_report(report):
    t = vortex.ticket()
    t.sh.header('Review of actions taken')
    for item in report:
        print(item) 
    print

def makejob(job):
    t = vortex.ticket()   

    defaults = dict(python=t.sh.which('python'))
    opts = dict(defaults.items() + job.items())

    t.sh.header(' '.join(('Vortex', vortex.__version__, 'job builder')))

    for k, v in opts.iteritems():
        print ' >', k.ljust(16), ':', v

    if not opts['name']:
        vortex.logger.error('A job name sould be provided.')
        exit(1)
    
    opts['wrap']     = False
    opts['mkopts']   = ' '.join(sys.argv[1:])
 
    corejob, tplconf = swissknife.mkjob(t, **opts)

    t.sh.header('Template configuration')

    for k, v in sorted(tplconf.iteritems()):
        print ' >', k.ljust(16), ':', v

    with open(tplconf['file'], 'w') as job:
        job.write(corejob)

    t.sh.header('Job creation completed')


if __name__ == "__main__":
    args, jobs = parse_command_line()
    # L'option -l ne renvoie que la liste des jobs qui seraient traités si l'option n'avait pas été passée
    # Si une des options -o ou -d est passée, on modifie les jobs existants et l'option -c défini le comportement pour ceux qui n'existent pas encore
    if args.list:
        list_jobs(jobs)
    elif args.info:
        list_variables()
    elif not jobs:
        print "No 'jobs' file or job description (-j option), nothing to do. See --help for more informations."
        sys.exit(1)   
    else:
        report=list()
        report.append('Generation of the jobs defined in the file : {} \n'.format(args.file))
        for job in jobs:
            jobname = job['name'] + '.py'
            if os.path.isfile(jobname) and args.backup:
                copyfile(jobname, jobname + '_backup')
                report=add_report(report, jobname, args.oper, args.sms, args.backup)
            makejob(job)
            report=add_report(report, jobname, args.oper, args.sms)
        display_report(report) 
        if args.verbose: 
            list_jobs(jobs)
