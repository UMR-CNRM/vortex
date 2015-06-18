.. _overview-data:

*********************
Gestion de ressources
*********************

Nous avons beaucoup insisté dans l'exposé des principes philosophiques sur les différents niveaux du flux de données. 
Nous allons maintenant voir comment VORTEX propose de se dépatouiller avec la gestion des ressources qui participent
de ce flux.

===================================
Récupérer et utiliser une ressource
===================================

D'une façon ou d'une autre, tout se résume à être capable de nommer une ressource *source*, à en disposer localement
au contexte d'exécution du modèle de PNT, ou de la mettre à disposition après exécution (sauvegarde, partage, etc.).

Le shell et ses non-dits
------------------------

Une façon commune de gérer la chose en shell repose peu ou prou
sur les commandes de base de *manipulation de fichiers*.

.. code-block:: bash

    % cd $TMPDIR
    % cp /home/toto/data/analysis ICMSHFCSTINIT

On peut enrober un peu, ou paramétrer la chose avec des variables d'environnement, etc.,
mais en gros, c'est ça l'idée.

La première chose que l'on peut dire c'est que c'est simple et efficace.

Si toutefois... c'est bien ce que l'on voulait faire, si le nom de la cible ne change pas. Si l'on est toujours
assuré de trouver la ressource source à cet endroit, avec ce nom. Si c'est encore vrai demain, dans un mois,
dans un an quand il faudra vérifier un bout de l'expérience, etc.

Et puis que se passe-t-il si le fichier source est éclaté car c'est une sortie du serveur d'IO par exemple ?
Et si je me sers de cette ressource comme d'un état analysé (ce que nous intuitons péremptoirement de la ligne
de commande), à quoi bon la copier, puisqu'elle sera en lecture seule, donc autant faire un *hard link*. Est-on sure
que la ressource est à la bonne date ? La bonne géométrie ? Que faire si avant le traitement l'on souhaite modifier
un champ, en éliminer un autre ? Etc.

Considérons aussi une opération "inverse", de sauvegarde d'un résultat d'exécution.

.. code-block:: bash

    % cp ICMSHFCST+0006 /home/toto/data/forecast.06

Même question que précédemment : quid si fichier LFI éclaté ? Et ai-je besoin de le copier ou de faire un *hard-link* ?
Sommes-nous sur le même *filesystem* ? Et si l'on veut sauvegarder cette ressource en ligne, sur le disque, mais aussi
sur la machine d'archivage. Ou sur un autre système distant. Ou sur le disque en ligne ET la machine d'archivage ?
Ou sur le disque en ligne ET la machine d'archivage ET un autre système distant ? Et si dans le transfert vers l'archivage
il faut d'abord "compacter" la ressource ? 

Et puis, comment savoir que la ressource est vraiment dans /home/toto/data ? Est-ce que cela peut changer ?
Que faire si la ressource n'est pas disponible ?

Pour simple que soit la commande shell elle mélange complètement plusieurs niveaux conceptuels.
Le plus contraignant et le plus inextricable à tout point de vue est quelle fusionne la *ressource logique*
(quelle est le type de la ressource et sa description) et la *ressource physique* (ici, quelle fichier contient
ladite ressource logique).

Par exemple, ici la ressource logique est par exemple : un état analysé de l'atmosphère
(altitude et surface) produit par un modèle arpege sur une géométrie tl798c2.4/l70, dans le format modèle,
le 18 juin 2015 sur le réseau de production de 06H.

La ressource physique dans laquelle l'on souhaiterait "ranger" notre ressource logique est ici un simple fichier,
dénommé :file:`ICMSHFCSTINIT`, et on suppose que c'est le petit nom sympa sous lequel le modèle qui s'exécutera ensuite
souhaitera le trouver (question en passant: et si ce n'est pas ou plus le cas?).

Mais peut-être souhaitons nous juste inspecter le contenu de se fichier en nous souciant peu de savoir où il sera
"rangé" (un fichier temporaire et volatile ferait alors parfaitement l'affaire). Mieux encore, nous pourrions récupérer
un "petit" fichier de configuration que nous souhaiterions manipuler en mémoire pour gagner du temps et ne pas polluer
l'espace de fichiers local. Bref, un fichier, c'est bien, mais ce n'est pas forcément la seule possibilité.

Nous comprenons donc maintenant que nous avons manipulé implicitement dans notre simple commande shell au moins
deux entités : la resource logique (ou resource métier proprement dite, c'est là qu'est la *science*) et la resource
physique ou *conteneur* (elle contient, dans un certain format, la ressource logique).

Mais ce n'est pas tout: nous avons bien dit que la resource logique était un état analysé d'un modèle, et nous
avons caractérisé sans date, son cutoff, sa géométrie, etc. Mais de quelle occurrence du modèle s'agit-il exactement ?
Celle tournée sur votre quoi de table ce week-end, celle en opération, celle en évaluation, celle en test ?
Pour le dire autrement : qui vous *fournit* un moyen de savoir quelle la ressource que vous pouvez utiliser dans
l'immensité des ressources logiques de caractéristiques identiques (ou presque) ? Car il doit y en avoir plusieurs,
dans des espaces de noms éventuellement totalement différents...

Et une fois que vous avez ce *fournisseur* d'informations permettant de localiser une ressource, qui est en charge
de physiquement stocker cette ressource ? Il doit bien y avoir un espace de stockage (votre disque / répertoire,
la machine d'archivage, etc.) qui fait ce boulot. 

Nous venons de faire l'analyse minimaliste qui va permettre, sur la base d'un peu modèle descriptif compatible
avec l'utilisation des footprints, de définir une première topologie d'objets en charge de ces aspects.

Soyons explicites
-----------------

Nous allons donc nommer ce qui ne l'était pas.

Nous appellerons *resource* ce qui correspond à une ressource logique. La classe de base sera :class:`~vortex.data.resources.Resource`.

Nous appellerons *container* ce qui correspond à une ressource physique. La classe de base sera :class:`~vortex.data.containers.Container`.

Nous appellerons *provider* ce qui correspond à un fournisseur d'accès. La classe de base sera :class:`~vortex.data.providers.Providers`.

Nous appellerons *store* ce qui correspond à espace de stockage. La classe de base sera :class:`~vortex.data.stores.Store`.

Toutes ces classes sont des classes abstraites qui héritent de :class:`footprints.FootprintBase`, elles sont donc
instanciables via le mécanisme de résolution des empreintes, au travers par exemple de *footprints.proxy*.

Passons en mode interactif, pour savoir quelles sont les *containers* disponibles::

    >>> fpx.containers()
    [<class 'vortex.data.containers.SingleFile'>, <class 'vortex.data.containers.MayFly'>, <class 'vortex.data.containers.InCore'>]

Notre conteneur de base de l'exemple shell serait donc tout aussi bien de la forme suivante::

    >>> c = fpx.container(filename='ICMSHFCSTINIT')
    >>> print c
    <vortex.data.containers.SingleFile object at 0x7fe92d1ed810 | path='ICMSHFCSTINIT'>
    >>> c.totalsize
    1467580416L
    >>> c.footprint_attributes
    ['actualfmt', 'cwdtied', 'filename', 'maxreadsize', 'mode']
    >>> c.mode
    'rb'
    >>> c.abspath
    '/home/sevault/tmp/rundir/ICMSHFCSTINIT'

Si l'on regarde le catalogue de ressources, la récolte est maigre::

    >>> fpx.resources()
    [<class 'vortex.data.executables.Script'>, <class 'vortex.data.resources.Unknown'>, <class 'vortex.data.executables.BlackBox'>]

Deux resources exécutables et une resource de type *Unknown* dont on devine confusément qu'elle ne risque pas d'enrichir
notre vocabulaire descriptif d'analyse::

    >>> fpx.resource()
    # [2015/18/06-12:36:55][footprints.collectors][pickup:0151][WARNING]: No 'resource' found in description 
        dict(
            resource = None,
        )

    Report Footprint-Resource: 

        vortex.data.executables.BlackBox
            kind       : {'why': 'Missing value'}

        vortex.data.executables.Script
            language   : {'why': 'Missing value'}

        vortex.data.resources.Unknown
            unknown    : {'why': 'Missing value'}

On pourrait toutefois se résoudre à jouer le jeu avec cette ressource inconnue::

    >>> x = fpx.resource(unknown=True)
    >>> x.footprint_attributes
    ['clscontents', 'nativefmt', 'unknown']
    >>> print x.unknown
    True
    >>> print x.nativefmt
    foo

On n'ira pas loin de cette façon. Et si l'on chargeait le package :mod:`common` ?

    >>> import common
    >>> pprint.pprint(fpx.resources())
    [<class 'common.data.obs.BlackList'>,
     <class 'common.data.obs.Refdata'>,
     <class 'common.data.binaries.ProTool'>,
     <class 'common.data.gridfiles.GridPointFullPos'>,
     <class 'common.data.consts.RRTM'>,
     <class 'gco.data.resources.MiscGenv'>,
     <class 'common.data.namelists.Namelist'>,
     <class 'common.data.climfiles.ClimBDAP'>,
     <class 'common.data.gridfiles.GridPointExport'>,
     <class 'common.data.diagnostics.ISP'>,
     <class 'common.data.obs.ObsRaw'>,
     <class 'common.data.consts.RtCoef'>,
     <class 'common.data.obs.ObsMap'>,
     <class 'common.data.diagnostics.DDH'>,
     <class 'vortex.data.resources.Unknown'>,
     <class 'common.data.namelists.NamelistSelectDef'>,
     <class 'common.data.consts.AtmsMask'>,
     <class 'common.data.consts.RtCoefAirs'>,
     <class 'vortex.data.executables.BlackBox'>,
     <class 'common.data.namelists.NamelistUtil'>,
     <class 'common.data.binaries.IOAssign'>,
     <class 'common.data.obs.VarBC'>,
     <class 'common.data.obs.Bcor'>,
     <class 'common.data.logs.Listing'>,
     <class 'common.data.binaries.Arome'>,
     <class 'common.data.consts.ChanSpectral'>,
     <class 'common.data.binaries.Odbtools'>,
     <class 'vortex.data.executables.Script'>,
     <class 'common.data.binaries.ProGrid'>,
     <class 'common.data.surfex.AmvError'>,
     <class 'common.data.consts.RszCoef'>,
     <class 'common.data.consts.AtlasEmissivityPack'>,
     <class 'common.data.consts.Stabal'>,
     <class 'common.data.consts.Correl'>,
     <class 'common.data.obs.BackgroundStdError'>,
     <class 'common.data.consts.ODBRaw'>,
     <class 'common.data.binaries.LopezMix'>,
     <class 'common.data.surfex.PGDLFI'>,
     <class 'common.data.consts.BatodbConf'>,
     <class 'common.data.consts.MatFilter'>,
     <class 'common.data.consts.SigmaB'>,
     <class 'common.data.consts.RmtbError'>,
     <class 'common.data.climfiles.ClimLAM'>,
     <class 'common.data.consts.ScatCMod5'>,
     <class 'common.data.logs.ParallelListing'>,
     <class 'common.data.consts.RtCoefAtovs'>,
     <class 'common.data.climfiles.ClimGlobal'>,
     <class 'common.data.surfex.AmvBias'>,
     <class 'common.data.obs.ObsODB'>,
     <class 'common.data.consts.CoefModel'>,
     <class 'common.data.consts.CstLim'>,
     <class 'common.data.modelstates.Historic'>,
     <class 'common.data.boundaries.LAMBoundary'>,
     <class 'common.data.surfex.IsbaParams'>,
     <class 'common.data.namelists.NamelistFullPos'>,
     <class 'common.data.consts.GPSList'>,
     <class 'common.data.consts.AtlasEmissivityInstrument'>,
     <class 'common.data.surfex.PGDFA'>,
     <class 'common.data.binaries.Batodb'>,
     <class 'common.data.modelstates.Analysis'>,
     <class 'common.data.surfex.CoverParams'>,
     <class 'common.data.namelists.NamelistSelect'>,
     <class 'common.data.binaries.IFSModel'>,
     <class 'common.data.consts.BcorIRSea'>,
     <class 'common.data.namelists.NamelistTerm'>,
     <class 'common.data.binaries.VarBCTool'>]

C'est mieux. Maintenant essayons d'obtenir une analyse::

    >>> a = fpx.resource(
        kind='analysis',
        date='2015061806',
        geometry='globalsp',
        cutoff='prod',
        model='arpege',
    )
    >>> print a
    <common.data.modelstates.Analysis object at 0x7fe92cf66f50 | cutoff='production' geometry='<vortex.data.geometries.SpectralGeometry | id='ARPEGE spectral geometry' area='france' t=798 c=2.4>' filling='full' filtering='None' date='2015-06-18T06:00:00Z' model='arpege'>
    >>> a.footprint_attributes
    ['clscontents', 'cutoff', 'date', 'filling', 'filtering', 'geometry', 'kind', 'model', 'nativefmt']

Qui pourrait nous fournir une telle ressource ? Demandons par exemple au bloc de production *canari*
d'une expérience OLIVE quelconque *X001*::

    >>> p = fpx.provider(experiment='X001', block='canari')
    print p
    <vortex.data.providers.VortexStd object at 0x7fe92cf70410 | namespace='vortex.cache.fr' block='canari'>
    >>> p.experiment
    'X001'

Nous voyons surgir, explicitement maintenant, un espace de nom ou *namespace*. Il sera en effet possible
de distingueur (ou pas, selon les mystères de la résolution des footprints), des fournisseurs de localisation
de ressources pour tel ou tel espace de nom. Nous aurions aussi pu demander explicitement l'archive::

    >>> p = fpx.provider(experiment='X001', block='canari', namespace='vortex.archive.fr')
    >>> p.namespace
    'vortex.archive.fr'

Ce qui devient intéressant, c'est que nous pouvons faire travailler maintenant ce *provider* sur notre *resource*
en lui demandant la seule et unique chose qu'il sache faire (ou presque): produire une URI::

    >>> p.uri(a)
    'vortex://vortex.archive.fr/play/sandbox/X001/20150618T0600P/canari/analysis.full-arpege.tl798-c24.fa'

Nous remarquons au passage, dans le pseudo-path de cette URL, des sections aux noms étranges: *play* et *sandbox*.
Ce sont respectivement les noms d'application et de configuration VORTEX::

    >>> p.vapp, p.vconf
    ('play', 'sandbox')

Ces valeurs sont données par défaut par votre *glove*, le *GLObal Versatile Environment* (on y reviendra, ou pas),
mais il est bien entendu possible de les modifier à la volée::

    >>> p = fpx.provider(experiment='X001', block='canari', vapp='arpege', vconf='france')
    >>> p.uri(a)
    'vortex://vortex.cache.fr/arpege/france/X001/20150618T0600P/canari/analysis.full-arpege.tl798-c24.fa'

Ce qui doit commencer à évoquer quelque chose pour certains d'entre vous.

===================
Le Resource Handler
===================

Dans la mesure où ces trois éléments sont presques toujours associées les uns aux autres et collaborent mutullement
deux à deux, il était tout naturel de les composer dans un autre objet, le :class:`~vortex.data.Handler` de ressource.
Il peut être instancié directement, mais il est bien plus commode de passer par l'interface fournie
dans le module :mod:`~vortex.toolbox` où nous pourrons allègrement mélanger les empreintes de *resources*,
*providers* et *containers*::

    >>> r = toolbox.rh(
        kind='analysis',
        date='2015061806',
        geometry='globalsp',
        cutoff='prod',
        model='arpege',
        experiment='X001',
        block='canari',
        vapp='[model]',
        vconf='france',
        filename='ICMSHFCSTINIT',
    )
    >>> r.complete
    True
    >>> print r.idcard()
    Handler <vortex.data.handlers.Handler object at 0x7fe92cf85690>
        Role      : Anonymous
        Alternate : None
        Complete  : True
        Options   : {}
        Location  : vortex://vortex.cache.fr/arpege/france/X001/20150618T0600P/canari/analysis.full-arpege.tl798-c24.fa

    Resource <common.data.modelstates.Analysis object at 0x7fe92cf85250>
        Realkind   : analysis
        Attributes : {'cutoff': 'production', 'kind': 'analysis', 'nativefmt': 'fa', 'geometry': <vortex.data.geometries.SpectralGeometry object at 0x7fe92d639910>, 'filling': 'full', 'filtering': None, 'date': Date(2015, 6, 18, 6, 0), 'clscontents': <class 'vortex.data.contents.FormatAdapter'>, 'model': 'arpege'}

    Provider <vortex.data.providers.VortexStd object at 0x7fe92cf85510>
        Realkind   : vortex
        Attributes : {'namebuild': <vortex.util.names.VortexNameBuilder object at 0x7fe92d685f10>, 'namespace': 'vortex.cache.fr', 'member': None, 'experiment': 'X001', 'expected': False, 'vconf': 'france', 'block': 'canari', 'vapp': 'arpege'}

    Container <vortex.data.containers.SingleFile object at 0x7fe92cf85650>
        Realkind   : container
        Attributes : {'actualfmt': 'fa', 'cwdtied': False, 'mode': 'rb', 'maxreadsize': 67108864, 'filename': 'ICMSHFCSTINIT'}

Nous pouvons maintenant accéder directement à son URL de locatisation::

    >>> r.location()
    'vortex://vortex.cache.fr/arpege/france/X001/20150618T0600P/canari/analysis.full-arpege.tl798-c24.fa'

=========================
Le stockage de ressources
=========================

Mais surtout, il est dorénavant possible de savoir quel espace de stockage abrite notre ressource::

    >>> print r.store
    <vortex.data.stores.VortexCacheStore object at 0x7fe92cf18410 | footprint=6>

Ouvrant la possibilité d'accéder à la localisation *physique* de la ressource (quand cela est possible)::

    >>> print r.locate()
    /tmp/mtool/cache/vortex/arpege/france/X001/20150618T0600P/canari/analysis.full-arpege.tl798-c24.fa
    >>> print r.check()
    None
    >>> r.get()
    # [2015/18/06-13:27:51][vortex.tools.systems][smartcp:0808][ERROR]: Missing source /tmp/mtool/cache/vortex/arpege/france/X001/20150618T0600P/canari/analysis.full-arpege.tl798-c24.fa
    False

Les méthodes super-stars du *handler* de ressources sont:

  * location()
  * locate()
  * check()
  * get()
  * put()
  * delete()
  * clear()
  * wait()

===================
Les espaces de noms
===================

Examinons la liste des *stores*::

    >>> import iga, gco, olive
    >>> pprint.pprint(fpx.stores())
    [<class 'vortex.data.stores.VortexCacheStore'>,
     <class 'vortex.data.stores.Finder'>,
     <class 'olive.data.stores.OliveStore'>,
     <class 'olive.data.stores.OpCacheStore'>,
     <class 'vortex.data.stores.VortexPromiseStore'>,
     <class 'vortex.data.stores.PromiseCacheStore'>,
     <class 'olive.data.stores.OliveArchiveStore'>,
     <class 'vortex.data.stores.MagicPlace'>,
     <class 'iga.data.stores.IgaFinder'>,
     <class 'vortex.data.stores.VortexStdArchiveStore'>,
     <class 'gco.data.stores.GcoStore'>,
     <class 'iga.data.stores.SopranoStore'>,
     <class 'vortex.data.stores.VortexStore'>,
     <class 'olive.data.stores.OpArchiveStore'>,
     <class 'olive.data.stores.OliveCacheStore'>,
     <class 'olive.data.stores.OpStore'>,
     <class 'gco.data.stores.GcoCentralStore'>,
     <class 'vortex.data.stores.VortexOpArchiveStore'>,
     <class 'vortex.data.stores.CacheStore'>,
     <class 'gco.data.stores.GcoCacheStore'>,
     <class 'iga.data.stores.IgaGcoCacheStore'>]

et celle des *providers*::

    >>> pprint.pprint(fpx.providers())
    [<class 'vortex.data.providers.VortexStd'>,
     <class 'olive.data.providers.OpArchiveCourt'>,
     <class 'vortex.data.providers.Magic'>,
     <class 'iga.data.providers.IgaGEnvProvider'>,
     <class 'iga.data.providers.SopranoProvider'>,
     <class 'olive.data.providers.Olive'>,
     <class 'gco.data.providers.GEnv'>,
     <class 'olive.data.providers.OpArchive'>,
     <class 'vortex.data.providers.VortexOp'>,
     <class 'iga.data.providers.IgaProvider'>,
     <class 'gco.data.providers.GGet'>,
     <class 'vortex.data.providers.Remote'>]

Il y a comme un air de famille. En fait le *store* du *ressource handler* est produit dynamiquement
(c'est une *property*) sur la base d'une résolution de footprint dont les deux principaux attributs
sont le *scheme* et le *netloc* issus du parsage de l'URL produite par le provider. Il y a donc un 
rapport entre les deux, mais totalement indirect puisque que médiatisé par la résolution des footprints
des *stores*. 

Un des arguments les plus décisif devient donc dans ce contexte l'espace de nom (ou domaine du *netloc*).
Le module :mod:`~vortex.toolbox` nous fournit une commande pour visualiser ceux définis par défaut
dans les footprints de classes *Store* ou *Provider*::

    >>> toolbox.print_namespaces()
    + dbl.archive.fr    [olive.data.stores.OpArchiveStore]
    + dbl.inline.fr     [iga.data.providers.IgaProvider,
                        iga.data.stores.IgaFinder]
    + dble.archive.fr   [olive.data.providers.OpArchiveCourt,
                        olive.data.providers.OpArchive,
                        olive.data.stores.OpArchiveStore]
    + dble.cache.fr     [olive.data.stores.OpCacheStore]
    + dble.inline.fr    [iga.data.providers.IgaProvider,
                        iga.data.stores.IgaFinder]
    + dble.multi.fr     [olive.data.providers.OpArchiveCourt,
                        olive.data.providers.OpArchive,
                        olive.data.stores.OpStore]
    + gco.cache.fr      [gco.data.stores.GcoCacheStore]
    + gco.meteo.fr      [gco.data.stores.GcoCentralStore]
    + gco.multi.fr      [gco.data.stores.GcoStore]
    + intgr.soprano.fr  [iga.data.providers.SopranoProvider,
                        iga.data.stores.SopranoStore]
    + multi.olive.fr    [olive.data.providers.Olive]
    + olive.archive.fr  [olive.data.providers.Olive,
                        olive.data.stores.OliveArchiveStore]
    + olive.cache.fr    [olive.data.providers.Olive,
                        olive.data.stores.OliveCacheStore]
    + olive.multi.fr    [olive.data.providers.Olive,
                        olive.data.stores.OliveStore]
    + open.archive.fr   [vortex.data.providers.VortexStd,
                        vortex.data.providers.VortexOp,
                        olive.data.stores.OliveArchiveStore]
    + open.cache.fr     [vortex.data.providers.VortexStd,
                        vortex.data.providers.VortexOp,
                        olive.data.stores.OliveCacheStore,
                        vortex.data.stores.CacheStore]
    + open.multi.fr     [vortex.data.providers.VortexStd,
                        vortex.data.providers.VortexOp]
    + oper.archive.fr   [olive.data.providers.OpArchiveCourt,
                        olive.data.providers.OpArchive,
                        olive.data.stores.OpArchiveStore]
    + oper.cache.fr     [olive.data.stores.OpCacheStore]
    + oper.inline.fr    [iga.data.providers.IgaProvider,
                        iga.data.stores.IgaFinder]
    + oper.multi.fr     [olive.data.providers.OpArchiveCourt,
                        olive.data.providers.OpArchive,
                        olive.data.stores.OpStore]
    + opgco.cache.fr    [iga.data.stores.IgaGcoCacheStore]
    + prod.soprano.fr   [iga.data.providers.SopranoProvider,
                        iga.data.stores.SopranoStore]
    + promise.cache.fr  [vortex.data.stores.PromiseCacheStore]
    + test.inline.fr    [iga.data.providers.IgaProvider,
                        iga.data.stores.IgaFinder]
    + vortex.archive.fr [vortex.data.providers.VortexStd,
                        vortex.data.providers.VortexOp,
                        vortex.data.stores.VortexStdArchiveStore]
    + vortex.cache.fr   [vortex.data.providers.VortexStd,
                        vortex.data.providers.VortexOp,
                        vortex.data.stores.VortexCacheStore]
    + vortex.multi.fr   [vortex.data.providers.VortexStd,
                        vortex.data.providers.VortexOp,
                        vortex.data.stores.VortexStore]
    + vsop.archive.fr   [vortex.data.stores.VortexOpArchiveStore]
    + vsop.cache.fr     [vortex.data.stores.VortexCacheStore]
    + vsop.multi.fr     [vortex.data.stores.VortexStore]
