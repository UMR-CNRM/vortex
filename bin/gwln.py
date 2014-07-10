#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, os, re

print "Gateway link uid:", os.getuid(), os.geteuid()

print "Gateway link cmd:", sys.argv

bank = '/home_nfs/mastergroup/masteruser/dev/setuid/store.' + str(os.getpid())

try:
    source = sys.argv[1]
    target = sys.argv[2]
except StandardError:
    print "Gateway link arg: Something weird in arguments"
    exit(1)

if re.search(r'[^\w\.\-]', source, re.IGNORECASE):
    print "Gateway link arg: Source argument badly formatted"
    exit(1)

if re.search(r'[^\w\.\-]', target, re.IGNORECASE):
    print "Gateway link arg: Target argument badly formatted"
    exit(1)


os.mkdir(bank)

os.link(source, bank + '/' + target)

exit(0)

