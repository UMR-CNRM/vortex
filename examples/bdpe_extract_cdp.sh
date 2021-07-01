#!/bin/sh
# Test the BDPE archive access for VORTEX

# The CDPH is available until J-5 online, and more in the archive.
# This test should end with something like this:
#    -rw-r--r-- 1 lamboleyp marp 35083785 19 avril 11:12 CDP_20210413180000_6_oui
#    -rw-r--r-- 1 lamboleyp marp 35328306 19 avril 11:12 CDP_20210414180000_5_oui
#    -rw-r--r-- 1 lamboleyp marp 35328306 19 avril 11:12 CDP_20210414180000_5_non

# meaning:
#   * ok for days J-5 and J-6 with archive access
#   * ok for J-5 only without archive access

case $(hostname) in
	belenos* | taranis*)
		echo "running on HPC"
		lirepe=/opt/softs/sopra/bin/lirepe.sh
		;;
	*)
		echo "running on $(hostname -s)"
		lirepe=/usr/local/sopra/bin/lirepe.sh
		;;
esac

export BDPE_TIMEOUT=5
export BDPE_RETRYS=1

export BDPE_CIBLE_PREFEREE=OPER
export BDPE_CIBLE_INTERDITE=INT
export DOMAINE_SOPRA=dev

for day in {5..6}; do
	date=$(date -d "$day days ago" "+%Y%m%d180000")
	for archive in oui non; do
		export BDPE_LECTURE_ARCHIVE_AUTORISEE=$archive
		$lirepe 7885 ${date} 000000 CDP_${date}_${day}_$archive
	done
done
ls -l *oui
ls -l *non
