#!/bin/sh

# This bash script execute vtxprestage to get files
# between to given date and from a given suite
#
# A few notes about this script:
# --date: "" to let the $dat1 and $dat2 being interpreted
# --local: '' to avoid the [ and ] interpretation
# If several terms are defined using rangex, the following syntax could be used:
# --term='rangex(0-0-1)'

exp=DBLE
dat1=2018060206
dat2=2018060406
vtxprestage.py \
--date="daterangex($dat1,$dat2,PT24H)" --cutoff=production --origin=historic\
--model=arpege --vapp=arpege --vconf=pearp --namespace=olive.archive.fr \
--kind=historic --term=0 --block=restart --experiment=$exp --geometry=globalsp2 \
--format=fa --local='toto_[date:ymd]_r[date:hh]+[term:fmth].[format]'
