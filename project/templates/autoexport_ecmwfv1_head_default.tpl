#!/bin/bash
#PBS -N %{jobname}
#PBS -S /bin/bash
#PBS -q ns
#PBS -l walltime=00:04:00
#PBS -l EC_memory_per_task=128mb
#PBS -j oe
#PBS -m a
