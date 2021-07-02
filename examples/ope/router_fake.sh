#!/bin/sh
# Projet vortex - 25 Novembre 2014
# Simulation d'appel à router_pe.bin ou router_pa.bin.

# Appelé par vortex depuis un noeud de transfert, ce
# script logue quelques infos qui seront accessibles
# dans le TMPDIR de l'utilisateur appelant.

# $TMPDIR is not defined on transfer nodes
TMPDIR=${TMPDIR:-/scratch/utmp/$USER}
if [ ! -d $TMPDIR ] ; then
    TMPDIR=$HOME/tmp
fi
mkdir -p $TMPDIR/vortex
log=$TMPDIR/vortex/router_fake.log
echo "Log file for $0: $log"

(
	echo
	echo $(date '+%Y%m%d %H:%M:%S')
	echo "	$0" "$@"
	while read n ; do
		eval echo "\	$n="\$$n
	done <<- eof
		HOME_SOPRA
		LD_LIBRARY_PATH
		base_transfert_agent
		DIAP_AGENT_NUMPROG_AGENT
	eof
	echo "	$(md5sum $1)"
) >> $log

exit 0
