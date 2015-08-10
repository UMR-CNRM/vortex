.. _overview-async:

***********************************
Traitements asynchrones avec Jeeves
***********************************

=========================
Éléments de configuration
=========================

C'est la section *driver* du fichier de configuration qui permet de paramétrer le fonctionnement général du daemon *jeeves*::

    [driver]
    pools    = in,delay,retry,process,ignore,out,error
    actions  = foo,vortex,dayfile,level,show,update,sleep,reload,active,mute,seton,setoff,ftput
    maxsleep = 15
    silent   = 4
    maxprocs = 2
    maxtasks = 128
    maxdelay = 21600
    retries  = 0
    rdelay   = 300
    rslow    = 1
