.. _epygram:

*****************
VORTEX et EPyGrAM
*****************

Un développement indépendant de VORTEX enrichit considérablement la capacité de manipulation des ressources
météorologiques de celui-ci : il s'agit du package *EPyGrAM*.

Nous allons voir que la puissance de collaboration entre les deux packages vient de leur usage commun des footprints.

========================
L'installation d'EPyGrAM
========================

Les informations de cette section sont issues d'un courrier d'Alexandre Mary en date du 24 mars 2016.
La documentation peut avoir évolué par ailleurs.

.. todo:: faire le point régulièrement avec Alex.

Il vous faut tout d'abord vérifier que vous disposez d'une installation locale du package **epygram**.
C'est très simple pour tous les PC CNRM et sur les supercalculateurs *beaufix* et *prolix*.

Installation sur PC
-------------------

  * Des versions pré-installées sont disponibles sous :file:`/home/common/epygram`
  * Lire les rapides instructions de :file:`/home/common/epygram/EPyGrAM.current/_install/INSTALL_README_cnrm_bull.txt` (et nettoyer l'ancienne installation, le cas échéant)

.. note:: si le répertoire `/home/common/epygram` n'apparaît pas sur votre PC, contacter E. Escalière et/ou CTI.

Installation sur supercalculateur
---------------------------------

  * EPyGrAM est également disponible sur *beaufix* et *prolix*, avec un jeu réduit d'outils (tout ce qui n'est pas graphique).
  * Lire les rapides instructions de :file:`/home/gmap/mrpe/mary/public/EPyGrAM.0.6.7/_install/INSTALL_README_cnrm_bull.txt`
  * Attention toutefois, n'allez pas saturer la mémoire et le cpu des nœuds de login avec !!!

Usage générique
---------------

  * Un certain nombre d'outils se lancent depuis votre shell courant, ils sont disponibles sous :file:`$EPYGRAM_INSTALL_DIR/apptools` (inclus dans le :envvar:`PATH`) ;
  * Pour chaque outil, l'option ``-h`` (ou ``--help``) vous renseignera sur la syntaxe et les options (parfois nombreuses) de l'outil en question.
  * Pour utiliser EPyGrAM dans vos scripts et librairies Python, effectuer une commande *import epygram*.
  * La documentation de la librairie est sous :file:`/home/common/epygram/EPyGrAM.current/epygram/doc_sphinx/index.html`.


=================================
Imbrication d'EPyGrAM dans VORTEX
=================================

Encore une fois : les footprints
--------------------------------

La grande chance de VORTEX est que le package EPyGrAM fait un usage raisonné et judicieux des *footprints*
pour définir les classes de base en charge de la gestion des différents formats de données.

Cela signifie notamment que dès qu'un import du package a été effectué :

  * Il existe un collecteur de formats de données : celui-ci se nomme *dataformats* ;
  * Tout un chacun peut instancier un gestionnaire de format de données par le mécanisme usuel de chargement de :mod:`footprints`, en particulier via *footprints.proxy*, par exemple la commande :func:`footprints.proxy.dataformat` ;
  * Le fait que telle ou telle classe soit sélectionnée pour l'instanciation se fera comme d'habitude sur la base de la correspondance entre le descriptif fourni et les valeurs d'attributs compatibles ;
  * Mais cela veut également dire que tout développeur peut proposer des extensions de ces gestionnaires de format de données, ou même en proposer d'autres.
  * Comme toujours avec l'usage des footprints, la résolution sera dynamique et ne dépendra que des classes effectivement chargées et disponibles dans le collecteur au moment de l'instanciation.


Une propriété dynamique : contents
----------------------------------

La plupart du temps une ressource météorologique est gérée, comme toute autre ressource,
par l'entremise d'un *Resource Handler*, objet qui compose entre une *resource* proprement dite,
un *container* et un *provider*. Mais ce *Resource Handler* dispose également d'un attribut spécial,
qui est en fait une *property* : l'attribut *contents* qui a les caractéristiques suivantes,
et qui va jouer un rôle central dans l'interfaçage d'EPyGrAM avec VORTEX :

  * L'attribut ne peut être renseigné que si le *Resource Handler* est complet (*resource*, *container* et *provider* définis) et que le container a été rempli, c'est-à-dire qu'un *get(...)* a été effectué ou que, inversement on est déjà à l'étape *put* ;
  * La résolution de la propriété (ie: l'invocation de *rh.contents*) essaye d'instancier un objet spécial en charge de la gestion du contenu de la ressource, en se basant sur une classe de base fournie par la ressource elle-même. Cette classe est renseignée par l'attribut du footprint de l'objet *resource* sous le nom de *clscontents*.
  * Dans la mesure où cette classe de base dérive de la classe :class:`~vortex.data.contents.FormatAdapter` définie dans le module :mod:`vortex.data.contents`, deux comportements seront possibles :
    * soit le module *epygram* a été chargé précédemment, et alors la résolution se fait sur la base d'une correspondance valide avec les empreintes des classes du collecteur *footprints.proxy.dataformats* ;
    * soit le module *epygram* n'a pas été chargé, et c'est alors une classe par défaut quelconque qui fera aussi office de gestionnaire de contenu, mais évidemment sans aucune des fonctionnalités fournies par les classes objets d'EPyGrAM.

Un exemple simple
-----------------

Nous allons maintenant prendre un exemple de code assez simple en supposant une ressource locale déjà disponible,
une analyse quelconque qui traîne depuis une éternité sur votre disque dur...

=== Récupération du resource handler ===

Nous ne faisons pas d'autre hypothèque que l'existence du fichier local::


    >>> import common
    >>> a = toolbox.rh(
            kind='analysis',
            date='20130501',
            geometry='globalsp',
            cutoff='assim',
            model='arpege',
            remote='bigdata',
            local='ICMSHFCSTINIT',
        )
    >>> a.resource
    <common.data.modelstates.Analysis object at 0x31f8990>
    >>> a.container
    <vortex.data.containers.File object at 0x31f8dd0>
    >>> a.provider
    <vortex.data.providers.Remote object at 0x31f8c10>
    >>> a.complete
    True

Nous avons donc maintenant une description "logique" complète de notre analyse. Nous allons la récupérer "physiquement"::

    >>> a.container.filled
    False
    >>> a.get()
    # [2015/27/02-16:28:28][vortex.data.stores][fileget:0467][INFO]: Ignore intent <in> for remote input bigdata
    True
    >>> a.container.filled
    True
    >>> a.container.actualpath()
    '/home/sevault/tmp/rundir/ICMSHFCSTINIT'
    >>> a.container.actualfmt
    'fa'

Avec mode graphique
-------------------

C'est maintenant que la magie commence::

    >>> import epygram
    >>> a.contents
    <vortex.data.contents.FormatAdapter object at 0x3928750>
    >>> a.contents.datafmt
    'fa'
    >>> a.contents.size
    1467580416L
    >>> a.contents.data
    <epygram.FA.FA object at 0x39be1d0>
    >>> d = a.contents.data
    >>> d.isopen
    False
    >>> d.format
    'FA'
    >>> d.processtype
    'analysis'
    >>> d.reference_pressure
    101325.0

Plusieurs des appels ou lecture d'attributs ci-dessus ne sont là qu'à titre documentaire
et n'ont pas besoin d'être effectués systématiquement. À ce stade, le fichier n'a pas encore
été réellement lu, ce qui sera fait après une commande comme *open(...)* ou *listfields(...)*, etc.

    >>> d.open()
    >>> d.validity
    <epygram.base.FieldValidity object at 0x3a3f110>
    >>> d.validity.getbasis()
    datetime.datetime(2013, 5, 1, 0, 0)
    >>> d.validity.term()
    datetime.timedelta(0)

Nous allons maintenant sélectionner à titre d'exemple un champ sympa, la température de surface::

    >>> temp = d.readfield('SURFTEMPERATURE')
    >>> temp
    <epygram.H2DField.H2DField object at 0x3a3f4d0>
    >>> temp.spectral
    False
    >>> temp.mean(), temp.min(), temp.max()
    (287.05675300463179, 203.04280028590733, 318.18446174093083)
    >>> temp.data
    masked_array(data =
    [[284.2541355549939 284.26027062824346 284.184966711169 ..., -- -- --]
    [283.9433296258083 283.98361476953704 283.94618387395 ..., -- -- --]
    [283.69276584372915 283.6249512584526 283.60180457889146 ..., -- -- --]
    ...,
    [286.69922743467566 287.1151548821877 287.4599432750657 ..., -- -- --]
    [287.1682963136163 287.3482373729095 287.3944778656557 ..., -- -- --]
    [287.1040234538394 287.14781708051885 287.15390700824224 ..., -- -- --]],
                mask =
    [[False False False ...,  True  True  True]
    [False False False ...,  True  True  True]
    [False False False ...,  True  True  True]
    ...,
    [False False False ...,  True  True  True]
    [False False False ...,  True  True  True]
    [False False False ...,  True  True  True]],
        fill_value = 1e+20)
    >>> temp.stats()
    {'std': 13.615257590798031, 'nonzero': 864696, 'quadmean': 287.37946113949158, 'min': 203.04280028590733, 'max': 318.18446174093083, 'mean': 287.05675300463179}

Et finalement la fameuse visualisation graphique tant attendue::

    >>> import matplotlib.pyplot as plt
    >>> x = temp.plotfield(graphicmode='points')
    >>> x
    <matplotlib.figure.Figure object at 0x4156bd0>
    >>> x.show()
    ...

Sans mode graphique
-------------------

Il peut être utile de désactiver toute interaction avec le DISPLAY de l'utilisateur,
et éviter le chargement de librairies dynamiques de visualisation. Pour cela,
avant l'utilisation d'autres modules, on peut spécifier à ''matplotlib'' de ne pas utiliser X11 comme *backend* graphique::

    >>> import matplotlib
    >>> matplotlib.use('Agg')
    >>> import matplotlib.pyplot as plt

En reprenant l'exemple plus haut, au lieu de faire x.show(...), on peut sauvegarder le graphique dans un fichier par exemple::

    >>> temp.plotfield(graphicmode='points')
    >>> plt.savefig('surftemp.png')

