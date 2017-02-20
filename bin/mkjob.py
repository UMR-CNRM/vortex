#!/opt/softs/python/2.7.5/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

import argparse
import os
import re
from shutil import copyfile
import sys
import tempfile

# Export de la version de vortex à utiliser (celle de l'application concernee)
vortex_path = os.path.join(os.path.realpath(os.getcwd()).rstrip('/jobs'), 'vortex')
pathdirs    = [os.path.join(vortex_path, xpath) for xpath in ('site', 'src', )]
for d in pathdirs:
    if os.path.isdir(d):
        sys.path.insert(0, d)

import vortex
from vortex.layout.jobs import mkjob
from vortex.util.config import load_template

_INFO_PRINT_FMT = ' > {:<16s}: {!s}'

DEFAULT_JOB_FILE = 'create_job'


def parse_command_line():
    description = "Create or modify vortex jobs for a specific application"
    parser = argparse.ArgumentParser(description=description)

    helpstr = ('file containing a list of dict describing all the jobs of the ' +
               'application (defaults to "%(default)s"). This file must have ' +
               'dict-like lines such as: name=jobname task=taskname')
    parser.add_argument('-f', '--file', help=helpstr, default=DEFAULT_JOB_FILE)
    parser.add_argument('-n', '--name', nargs='+', help="Name(s) of the job(s) to handle " +
                        "(must match the corresponding name(s) in the 'create_job' file")
    parser.add_argument('-j', '--job', nargs='+', help="Command line containing " +
                        "all informations to make one specific job, ex : \n name=jobname task=taskname")
    parser.add_argument('-o', '--oper', action='store_true', help='Activate oper specifications ' +
                        'in the jobs (op_mail=True, ad.route_on(),... The default option is the test configuration')
    parser.add_argument('-a', '--add', nargs='+', help='Add (and replace if necessary) argument(s) to the ' +
                        'description of all the jobs concerned.')
    parser.add_argument('-w', '--write', action='store_true', help="If -j option is activated, " +
                        "add the command line to the 'jobs' file")
    parser.add_argument('-l', '--list', action='store_true', help='Only list the name of the ' +
                        'jobs to handle, and exit')
    parser.add_argument('-b', '--backup', nargs='?', const='.backup', help='Save old jobs with the given extension ' +
                        '(default is ".backup") before creating new ones with specified options')
    parser.add_argument('-v', '--verbose', help='verbose mode', action='store_true')
    parser.add_argument('-i', '--info', action='store_true', help='Full list of available ' +
                        'variables that can be used to make an OP job (according to the job template)')

    args = parser.parse_args()

    report = list()
    jobs = list()

    # Les descriptifs de jobs sont ranges dans une liste
    # Si un descriptif est passé manuellement (avec l'option -j) on ne traite que lui
    if not args.job and os.path.isfile(args.file):
        report.append('Generation of the jobs defined in the file : {} \n'.format(args.file))
        with open(args.file, 'r') as fp:
            for line in fp.readlines():
                if bool(line.rstrip()):
                    job = make_cmdline(line.rstrip())
                if args.name is None or job['name'] in args.name:
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

    dflt_profile = 'oper' if args.oper else 'test'
    for job in jobs:
        job.setdefault('profile', dflt_profile)

    return args, jobs, report


def list_jobs(jobs):
    print('Processed jobs:')
    for job in jobs:
        print(job)


def make_cmdline(description):
    t = vortex.ticket()
    if type(description) is str:
        description = description.split(' ')
    return t.sh.rawopts(description)


def list_variables():
    t = vortex.ticket()
    core = load_template(t, '@opjob-variables.tpl')
    with open(core.srcfile, 'r') as f:
        for line in f:
            print(line)


def add_report(report, jobname, oper, backup=None):
    if backup is not None:
        report.append('Save the job ' + jobname + ' under ' + jobname + backup)
    else:
        configuration = 'oper' if oper else 'test'
        report.append('Job ' + jobname + ' created in configuration ' + configuration)
    return report


def display_report(report):
    t = vortex.ticket()
    t.sh.header('Review of actions taken')
    for item in report:
        print(item)
    print()


def makejob(job):
    t = vortex.ticket()

    defaults = dict(python=t.sh.which('python'))
    opts = dict(defaults.items() + job.items())

    t.sh.header(' '.join(('Vortex', vortex.__version__, 'job builder')))

    for k, v in opts.iteritems():
        print(_INFO_PRINT_FMT.format(k, v))

    if not opts['name']:
        vortex.logger.error('A job name sould be provided.')
        exit(1)

    opts['wrap']     = False
    opts['mkopts']   = ' '.join(sys.argv[1:])

    corejob, tplconf = mkjob(t, **opts)

    t.sh.header('Template configuration')

    for k, v in sorted(tplconf.iteritems()):
        print(_INFO_PRINT_FMT.format(k, v))

    def _wrap_launch(jobfile):
        '''Launch the **jobfile** script using **extra_wrapper*.'''
        t.sh.spawn(tplconf.get('extra_wrapper').format(injob=jobfile,
                                                       tstamp=vortex.tools.date.now().ymdhms,
                                                       pwd=tplconf['pwd'],
                                                       name=tplconf['name'],
                                                       file=tplconf['file']),
                   output=False, shell=True)

    if tplconf.get('extra_wrapper', None):
        # Launch the script with the designated wrapper
        if tplconf.get('extra_wrapper_keep', False):
            # In this case, we generate the job file as usual and it is kept
            with open(tplconf['file'], 'w') as job:
                job.write(corejob)
            _wrap_launch(tplconf['file'])
        else:
            # Here the job is written in a temporary file submitted and deleted
            with tempfile.NamedTemporaryFile(prefix=re.sub(r'\.py$', '', tplconf['file']) + '_',
                                             dir=tplconf['pwd'], bufsize=0) as job:
                job.write(corejob)
                job.flush()
                t.sh.fsync(job)
                _wrap_launch(job.name)
    else:
        # Just create the job file...
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
            if os.path.isfile(jobname) and args.backup is not None:
                copyfile(jobname, jobname + args.backup)
                report = add_report(report, jobname, args.oper, args.backup)
            makejob(job)
            report = add_report(report, jobname, args.oper)
        display_report(report)
        if args.verbose:
            list_jobs(jobs)
