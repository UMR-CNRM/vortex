#!/opt/softs/python/2.7.5/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

import os, sys
import argparse
from shutil import copyfile

# Export de la version de vortex à utiliser (celle de l'application concernée)
vortex_path = os.path.join(os.path.realpath(os.getcwd()).rstrip('/jobs'), 'vortex')
pathdirs    = [os.path.join(vortex_path, xpath) for xpath in ('site', 'src', )]
for d in pathdirs:
    if os.path.isdir(d):
        sys.path.insert(0, d)

import vortex
from iga.util import swissknife
from vortex.util.config import load_template


DEFAULT_JOB_FILE = 'create_job'

# A essayer de mettre en fichier de conf
sbatch_rootapp   = 'os.getcwd()'
sms_rootapp      = 'os.environ["DMT_PATH_EXEC"]'
test_template    = 'job-test-default.tpl'
oper_template    = 'job-oper-default.tpl'


def parse_command_line():
    description = "Create or modify vortex jobs for a specific application"
    parser = argparse.ArgumentParser(description=description)

    helpstr = ('file containing a list of dict describing all the jobs of the ' +
               'application (defaults to "%(default)s"). This file must have ' +
               'dict-like lines such as: name=jobname task=taskname')
    parser.add_argument('-f', '--file', help=helpstr, default=DEFAULT_JOB_FILE)
    parser.add_argument('-n', '--name', help="Name of the job to handle " +
                        "(must match the corresponding name in the 'jobs' file")
    parser.add_argument('-j', '--job', nargs='+', help="Command line (dict-like string) containing " +
                        "all informations to make a specific job, ex : \n 'name=jobname task=taskname'")
    parser.add_argument('-o', '--oper', action='store_true', help='Activate oper specifications ' +
                        'in the jobs (op_mail=True, ad.route_on(),... The default option is the test configuration')
    parser.add_argument('-a', '--add', nargs='+', help='Add (and replace if necessary) argument to the ' +
                        'description of all the jobs concerned.')
    parser.add_argument('-w', '--write', action='store_true', help="If -j option is activated, " +
                        "add the command line to the 'jobs' file")
    parser.add_argument('-l', '--list', action='store_true', help='Only list the name of the ' +
                        'jobs to handle, and exit')
    parser.add_argument('-s', '--sms', action='store_true', help='Make a job in test ' +
                        'configuration but that can be launched with sms.')
    parser.add_argument('-b', '--backup', action='store_true', help='Save old jobs before ' +
                        'creating new ones with specified options')
    parser.add_argument('-v', '--verbose', help='verbose mode', action='store_true')
    parser.add_argument('-i', '--info', action='store_true', help='Full list of available ' +
                        'variables that can be used to make an OP job (according to the job template)')

    args = parser.parse_args()

    report = list()
    jobs = list()

    # Les descriptifs de jobs sont rangés dans une liste
    # Si un descriptif est passé manuellement (avec l'option -j) on ne traite que lui
    if not args.job and os.path.isfile(args.file):
        report.append('Generation of the jobs defined in the file : {} \n'.format(args.file))
        with open(args.file, 'r') as fp:
            for line in fp.readlines():
                if (args.name is None or args.name in line) and bool(line.rstrip()):
                    job = make_cmdline(line.rstrip().split(' '))
                    jobs.append(job)

    elif args.job:
        job = make_cmdline(args.job)
        jobs.append(job)
        if args.write:
            with open(args.file, 'a') as fp:
                fp.write(args.job + "\n")

    if args.add:
        newparams = make_cmdline(args.add)
        for job in jobs:
            job.update(newparams)

    for job in jobs:
        if 'template' not in job.keys():
            job['template'] = oper_template if args.oper else test_template
        if 'inifile' not in job.keys():
            job['inifile'] = job['template'].split(".")[0] + '.ini'
        if not args.oper:
            job['rootapp'] = sms_rootapp if args.sms else sbatch_rootapp

    return args, jobs, report


def list_jobs(jobs):
    print('Processed jobs:')
    for job in jobs:
        print(job)


def make_cmdline(description):
    print(description)
    job_description = dict((k.strip(), v.strip()) for (k, v) in (item.split('=') for item in description))
    return job_description


def list_variables():
    t = vortex.ticket()
    core = load_template(t, 'opjob-variables.tpl')
    with open(core.srcfile, 'r') as f:
        for line in f:
            print(line)


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
        print(' >', k.ljust(16), ':', v)

    if not opts['name']:
        vortex.logger.error('A job name sould be provided.')
        exit(1)

    opts['wrap']     = False
    opts['mkopts']   = ' '.join(sys.argv[1:])

    corejob, tplconf = swissknife.mkjob(t, **opts)

    t.sh.header('Template configuration')

    for k, v in sorted(tplconf.iteritems()):
        print(' >', k.ljust(16), ':', v)

    with open(tplconf['file'], 'w') as job:
        job.write(corejob)

    t.sh.header('Job creation completed')


if __name__ == "__main__":
    args, jobs, report = parse_command_line()
    # L'option -l ne renvoie que la liste des jobs qui seraient traités si l'option n'avait pas été passée
    # Si une des options -o ou -d est passée, on modifie les jobs existants et l'option -c défini le comportement pour ceux qui n'existent pas encore
    if args.list:
        list_jobs(jobs)
    elif args.info:
        list_variables()
    elif not jobs:
        print("No 'jobs' file or job description (-j option), nothing to do. See --help for more informations.")
        sys.exit(1)
    else:
        for job in jobs:
            jobname = job['name'] + '.py'
            if os.path.isfile(jobname) and args.backup:
                copyfile(jobname, jobname + '_backup')
                report = add_report(report, jobname, args.oper, args.sms, args.backup)
            makejob(job)
            report = add_report(report, jobname, args.oper, args.sms)
        display_report(report)
        if args.verbose:
            list_jobs(jobs)
