#!/bin/sh

# This bash script gets files between two given dates and from a given suite.
# As is, it only asks hendrix to transfer the files from tape to (fast) cache.
# Replace vtxprestage.py with vtxget.py for an effective local transfer.

# Note about quotes:
#    --date             : "" to allow for $dat1 and $dat2 shell variable expansion
#    --local and --term : '' to avoid brackets and parenthesis interpretation

expe=DBLE
dat1=2018060206
dat2=2018060406

vtxprestage.py \
	--date="daterangex($dat1,$dat2,PT24H)" \
	--cutoff=production \
	--origin=historic \
	--model=arpege \
	--vapp=arpege \
	--vconf=pearp \
	--namespace=olive.archive.fr \
	--kind=historic \
	--term='rangex(0-3-1)' \
	--block=restart \
	--experiment=$expe \
	--geometry=globalsp2 \
	--format=fa \
	--local='toto_[date:ymd]_r[date:hh]+[term:fmth].[format]'
