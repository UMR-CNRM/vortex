#!/bin/sh
# Test the BDPE archive access for VORTEX

# The CDPH is available for J-1 online, and more in the archive.
# This test should end with something like this:
# 		-rw-r--r-- 1 lamboleyp mcdi 39539895 29 mai   17:13 CDP_20180526180000_oui
# 		-rw-r--r-- 1 lamboleyp mcdi 39229061 29 mai   17:13 CDP_20180527180000_oui
# 		-rw-r--r-- 1 lamboleyp mcdi 38258866 29 mai   17:13 CDP_20180528180000_oui
# 		-rw-r--r-- 1 lamboleyp mcdi 38258866 29 mai   17:13 CDP_20180528180000_non
# meaning:
#   * ok for the 3 last days with archive access
#   * ok yesterday only without archive access

case $(hostname) in
	belenos*|taranis*)
		echo "running on HPC"
		export HOME_SOPRA=/opt/softs/sopra
		export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/opt/softs/sopra/lib
		export base_transfert_agent=/home/ext/dsi/mtti/mtti023/agent-$(hostname)
		export DIAP_AGENT_NUMPROG_AGENT=0x20000011
		lirepe=/opt/softs/sopra/bin/lirepe
		;;
	*)
		echo "running somewhere"
		lirepe=lirepe
		;;
esac

export BDPE_CIBLE_PREFEREE=OPER
export BDPE_CIBLE_INTERDITE=INT
for day in 1 2 3 ; do
	date=$(date -d "$day days ago" "+%Y%m%d180000")
	for archive in oui non ; do
		export BDPE_LECTURE_ARCHIVE_AUTORISEE=$archive
		$lirepe 7885 ${date} 000000 CDP_${date}_$archive
	done
done
ls -l *oui
ls -l *non
