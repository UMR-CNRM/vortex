#!/bin/bash
#PBS -N vtxlink
#PBS -S /bin/bash
#PBS -q ns
#PBS -l walltime=00:02:00
#PBS -l EC_memory_per_task=128mb
#PBS -j oe
#PBS -m a

echo "Hostname: $(hostname)"
echo

HEADDIR=%{headdir}
FROM=%{from}
TO=%{to}

# Always Fail on error
set -e
set -x

cd $HEADDIR
rm -f $TO
ln -sf $FROM $TO

if [ ! -e $FROM ] ; then
    echo "WARNING: Source is missing: $FROM"
fi 
