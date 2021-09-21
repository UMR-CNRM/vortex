.. _uget-fr:

***********************************************
Documentation utilisateur Uenv/Uget (in French)
***********************************************

:Release: |version|
:Author: Alexandre Mary et contributeurs.
:Date: |today|

L'utilitaire *uenv/uget* développé dans Vortex est le pendant de
*genv/gget*, mais propre à chaque utilisateur (d'où le **u** à la place du **g**)
et partageable avec les autres utilisateurs !
Il permet donc, dans des expériences sous Vortex, de récupérer des ressources
comme on le fait via un *genv* officiel, mais chez soi ou chez le collègue
d'en face (oui, même s'il est de l'autre côté de la passerelle !).

Cet outil permet donc de travailler en mode "recherche" de la même manière
qu'avec des cycles officiels GCO, sans devoir modifier à la main tout un
ensemble de ressources dans une expérience Olive (Olive/Vortex uniquement,
ça ne marche pas avec une (obsolescente) expérience Olive/Perl).

Bref, c'est super, mais comment ça marche ?
C'est simple, mais il y a quelques petites règles à observer pour bien faire les
choses...


Tutoriel
========

L'exemple montre comment partir d'un Genv Arome France, pour en modifier des composants.

.. highlight:: none


Avant la première utilisation
-----------------------------

.. highlight:: bash

* charger Genv/Gget (dans votre *profile*, si ce n'est pas déjà fait)::

    export PATH=/home/mf/dp/marp/gco/public/bin:$PATH

* charger Vortex (dans votre *profile*, si ce n'est pas déjà fait)::

      module load python
      VORTEX_INSTALL_DIR=/home/mf/dp/marp/verolive/vortex/vortex-olive
      PYTHONPATH=$VORTEX_INSTALL_DIR/src:$PYTHONPATH
      PYTHONPATH=$VORTEX_INSTALL_DIR/site:$PYTHONPATH
      PYTHONPATH=$VORTEX_INSTALL_DIR/project:$PYTHONPATH
      export PYTHONPATH
      export PATH=$VORTEX_INSTALL_DIR/bin:$PATH

* initialisation des répertoires::

      uget.py bootstrap_hack [user]

  Ex::

      uget.py bootstrap_hack mary

 Pour bien faire (éviter les copies entre ``$HOME`` et ``/scratch``), il est
 préférable de déplacer/linker les répertoires de travail (commandes
 ci-dessous)::

      cd $HOME/.vortexrc
      mv hack /scratch/work/[user]/hack
      ln -s /scratch/work/[user]/hack

.. highlight:: none

.. _uget-clone-existant:

Clone d'un cycle existant
-------------------------

Syntaxe::

    uget.py hack genv [cycle_source] into [cycle_cible]@[user]

Ex::

    uget.py hack genv al42_arome-op2.30 into al42_arome-dble.02@mary

Ce "hack" crée une copie du fichier de conf de GCO (``genv al42_arome-op2.30``),
sous: ``$HOME/.vortexrc/hack/uget/mary/env/al42_arome-dble.02``.

Le cycle source peut être un cycle "officiel" GCO, ou celui d'un autre
utilisateur; dans ce cas la syntaxe est légèrement différente, afin de préciser
chez qui on veut récupérer le cycle::

    uget.py hack env al42_arome-dble.01@faure into al42_arome-dble.02@mary

Il s'agit d'un sorte de convention avec *uget* : ``genv blabla``
correspond à un cycle GCO dénommé ``blabla`` alors qu'une notation du type
``env blabla@quelqu'un`` désigne un cycle *uget/uenv* dénommé ``blabla``
hébergé chez ``quelqu'un``.


Modification du cycle cloné
---------------------------

Pour chaque élément du fichier de conf du cycle cloné (obtenu à l'étape
:ref:`uget-clone-existant`), on peut modifier la ressource (i.e. ce qui
est à droite du signe ``=``), en pointant vers le "GCO official store",
chez un collègue ou chez soi (sous ``$HOME/.vortexrc/hack/uget/$USER/data/``).

On peut panacher ainsi les éléments d'un *uenv*...

Ex:
    | Je suis l'user ``mary``, l'élément:
    |    ``CLIM_FRANMG_01KM30=clim_franmg.01km30.03`` (chez GCO)
    | peut être remplacé par:
    |    ``CLIM_FRANMG_01KM30=uget:mes_clims@mary`` (``uget:`` parce qu'il s'agit d'un élément géré par *uget* et ``@mary`` car l'élément est chez moi)
    | ou bien:
    |    ``CLIM_FRANMG_01KM30=uget:mes_clims.04@faure`` (``@faure`` parce qu'il  s'agit d'un élément hébergé chez Ghislain Faure)

Attention, petite différence par rapport à ``genv`` pour les packs de namelists:
ces packs étant stockés sous forme de tar/tgz, il faut l'écrire explicitement
dans le uenv.

Ex (noter la présence de l'extension en ``.tgz``)::

    NAMELIST_AROME=uget:mon_pack_de_namelist.tgz@mary

Cela dit, *uget* sera capable de récupérer soit le répertoire
``$HOME/.vortexrc/hack/uget/mary/data/mon_pack_de_namelist`` soit le tgz
``$HOME/.vortexrc/hack/uget/mary/data/mon_pack_de_namelist.tgz`` (en fait, le
plus récent des deux).

On peut également rajouter de nouvelles ressources dans notre *uenv*.
C'est juste un peu plus délicat, du fait que les clés doivent suivre une syntaxe
précise pour automatiquement être prises en compte par Vortex; par exemple pour
une clim: ``CLIM_[AREA]_[RESOLUTION]``.

Pour modifier un élément existant (par exemple un pack de namelist), on le
récupère via uget::

    uget.py hack gdata [element] into [clone_element]@[user]

Ex::

    uget.py hack gdata al42_arome-op2.15.nam into al42_arome-op2.16.nam.tgz@mary

ou::

    uget.py hack data al42_arome-dble.01.nam.tgz@faure into al42_arome-op2.16.nam.tgz@mary

La convention utilisée ici par *uget* est cohérente avec celle utilisée
précédement : ``gdata blabla`` correspond à une donnée GCO dénommé ``blabla``
alors qu'une notation du type ``data blabla@quelqu'un`` désigne une donnée gérée
par *uget/uenv* dénommé ``blabla``  hébergé chez ``quelqu'un``.

Historisation
-------------

On peut tout d'abord vérifier qu'il n'y a pas d'incohérence dans son *uenv*,
c-à-d. vérifier que tous les éléments listés existent bien, soit en local soit
sur archive, chez soi, chez GCO ou chez un autre utilisateur::

    uget.py check env al42_arome-dble.02@mary

Puis, pour figer une version et la partager avec ses petits copains, il faut
"pousser" le *uenv* sur Hendrix::

    uget.py push env al42_arome-dble.02@mary

La commande (qui peut prendre un certain temps) archive le uenv ET les éléments
(data) indexés sur Hendrix.
Il est alors fortement recommandé, à partir du moment où l'on pousse et donc met
à disposition, de nettoyer localement (pour éviter de modifier quelque chose qui
a été archivé !)::

    uget.py clean_hack

Attention: tous les *uenv* et éléments ayant été poussés sont alors effacés
des répertoires locaux ``env`` et ``data`` !

On peut aussi vouloir pousser un élément avant même de pousser un cycle
*uenv*, pour le mettre à disposition avant que le *uenv* complet soit prêt.

Dans ce cas::

    uget.py push data [element]@[user]}

Ex::

    uget.py push data al42_arome-op2.16.nam.tgz@mary


Explorer le champ des possibles
-------------------------------

*(new in Vortex-1.2.3)*

Il est possible de lister les cycles existants chez un utilisateur::

    uget.py list env from faure

ou bien les éléments, avec un éventuel filtre (équivalent à un grep, c'est à
dire basé sur une expression régulière)::

    uget.py list data from faure matching .nam


D'un cycle à l'autre
--------------------

*(new in Vortex-1.2.3)*

Il est également possible de comparer deux cycles *uenv*::

    uget.py diff env [cycle_a_comparer] wrt env [cycle_reference]

Ex::

    uget.py diff env al42_arome-dble.02@mary wrt genv al42_arome-op2.30

ou::

    uget.py diff env al42_arome-dble.02@mary wrt env al42_arome-dble.01@faure

Si votre cycle a été généré en utilisant ``uget.py hack``, un commentaire de
traçage présent en tête de fichier vous permet d'utiliser le raccourci ``parent``
suivant::

    uget.py diff env [mon_cycle] wrt parent


Livraison de conf ou d'éléments à GCO
-------------------------------------

*(new in Vortex-1.2.3)*

La commande ``uget.py export`` est une variante du *diff*, permettant de
lister les éléments mis à jour par rapport à une référence avec leur chemin sur
archive. Ce peut être utile pour livrer des éléments et/ou une conf à GCO.

Ex::

    uget.py export env al42_arome-dble.02@mary wrt genv al42_arome-op2.30


Utilisation dans Olive
======================

Pour utiliser un cycle *uenv* dans vos expériences Olive (Vortex) à la place
du *genv*,  il vous suffit de modifier le ``CYCLE`` en tête d'expérience avec
la syntaxe::

    uenv:[mon_cycle]@[user]

Cela simplifie également la livraison de confs à GCO, qui pourra récupérer votre
*uenv*, l'historiser en *genv*, sans avoir à remodifier toutes les boîtes
Olive.

Olive et Vortex se basent parfois sur le nom du cycle GCO/genv pour détecter le
cycle du modèle (pour générer les bons *gnam*, ajouter si besoin une ligne de
commande lors du lancement du binaire...): il faut donc choisir des noms qui
ressemblent à ceux choisis par GCO, par ex: ``uenv:cy42_blabla`` ou
``uenv:al42t1_truc``.


Remarques et Bonnes pratiques
=============================

* les clims (et autres éléments mensuels) sont "expansées": la clé
  ``CLIM_BLABLA=uget:mes_clims@mary`` concerne tous les fichiers
  ``mes_clims.m??`` se trouvant dans mon répertoire ``data`` ;
* même si c'est techniquement faisable, il est très fortement recommandé de
  s'interdire de modifier un *uenv* ou un élément (data) une fois archivé. Au
  risque de récupérer un élément qui n'est pas le bon...
* du coup, une bonne habitude inspirée de Stéphane est de numéroter tout cycle
  et tout élément, et de les incrémenter !
* sur hendrix, les *uenv* et éléments sont archivées sous une arborescence
  "éclatée" et arbitraire. On peut se demander pourquoi et râler de ne pas y
  retrouver ses petits à la main:

    1. raison de performance sur Hendrix
    2. c'est aussi une incitation à ne plus y toucher après *push* ! et à
       passer par ``uget.py`` pour les récupérer proprement. Uget, une amie
       qui vous veut du bien.

* tant qu'on n'a pas fait de *push*, mes *uenv* et éléments ne sont
  accessibles que pour moi, pas pour les collègues !
* si on a de gros éléments à historiser, il peut être judicieux de se logger sur
  un noeud de transfert pour faire le *push*.
* il est possible de mettre des lignes de commentaire dans son *uenv*,
  en les commençant par ``#``.


Quelques fonctions "avancées" (mais pratiques)
==============================================


Notion d'utilisateur par défaut
-------------------------------

Il peut être assez pénible d'avoir à préciser son nom d'utilisateur (``@mary``)
à chaque fois que l'on manipule un cycle *uget/uenv*. Il a donc été prévu de
pouvoir définir un utilisateur par défaut::

   uget.py set location mary

On peut "retrouver" le nom de l'utilisateur par défaut en tapant ``uget.py info``.
Une fois ce réglage effectué, il est possible de taper simplement::

   uget.py check env al42_arome-dble.02

ou::

   uget.py diff env al42_arome-dble.02 wrt env al42_arome-dble.01@faure

(Au lieu, de ``uget.py check env al42_arome-dble.02@mary`` et
``uget.py diff env al42_arome-dble.02@mary wrt env al42_arome-dble.01@faure``)

Attention, ça ne vous dispensera toutefois pas de mettre l'utilisateur (e.g. ``@mary``)
dans l'identification des ressources, ni dans Olive !

Utilisation de *uget.py* en mode console
----------------------------------------

Dans les exemples précédents, l'utilisation de ``uget.py`` s'est faite
exclusivement par le biais d'une succession de commandes shell indépendantes. Un
autre mode d'utilisation existe pour ``uget.py`` : il s'agit d'une utilisation
en mode "invite de commande". Pour cela, il lancer simplement ``uget.py`` (sans
arguments) ; cela ouvrira une invite de commande (que l'on peut quitter avec
``Ctrl-D``) dans laquelle on peut saisir les commandes évoquées ci-dessus::

      $ uget.py
      Vortex 1.2.2 loaded ( Monday 05. March 2018, at 14:07:13 )
      (Cmd) list env from mary

      al42_test.02
      [...]
      cy43t2_clim-op1.05
      cy43t2_climARP.01

      (Cmd) pull env cy43t2_clim-op1.05@mary

      ARPREANALYSIS_SURFGEOPOTENTIAL=uget:Arp-reanalysis.surfgeopotential.bin@mary
      [...]
      UGAMP_OZONE=uget:UGAMP.ozone.ascii@mary
      USNAVY_SOIL_CLIM=uget:US-Navy.soil_clim.bin@mary

      (Cmd) check env cy43t2_clim-op1.05@mary

      Hack   : MISSING (/home/meunierlf/.vortexrc/hack/uget/mary/env/cy43t2_clim-op1.05)
      Archive: Ok      (meunierlf@hendrix.meteo.fr:~mary/uget/env/f/cy43t2_clim-op1.05)

      Digging into this particular Uenv:
        [...]
        ARPREANALYSIS_SURFGEOPOTENTIAL: Archive  (uget:Arp-reanalysis.surfgeopotential.bin@mary)
        [...]
        UGAMP_OZONE                   : Archive  (uget:UGAMP.ozone.ascii.m01@mary for month: 01)
        UGAMP_OZONE                   : Archive  (uget:UGAMP.ozone.ascii.m02@mary for month: 02)
        UGAMP_OZONE                   : Archive  (uget:UGAMP.ozone.ascii.m03@mary for month: 03)
        UGAMP_OZONE                   : Archive  (uget:UGAMP.ozone.ascii.m04@mary for month: 04)
        UGAMP_OZONE                   : Archive  (uget:UGAMP.ozone.ascii.m05@mary for month: 05)
        UGAMP_OZONE                   : Archive  (uget:UGAMP.ozone.ascii.m06@mary for month: 06)
        UGAMP_OZONE                   : Archive  (uget:UGAMP.ozone.ascii.m07@mary for month: 07)
        UGAMP_OZONE                   : Archive  (uget:UGAMP.ozone.ascii.m08@mary for month: 08)
        UGAMP_OZONE                   : Archive  (uget:UGAMP.ozone.ascii.m09@mary for month: 09)
        UGAMP_OZONE                   : Archive  (uget:UGAMP.ozone.ascii.m10@mary for month: 10)
        UGAMP_OZONE                   : Archive  (uget:UGAMP.ozone.ascii.m11@mary for month: 11)
        UGAMP_OZONE                   : Archive  (uget:UGAMP.ozone.ascii.m12@mary for month: 12)
        USNAVY_SOIL_CLIM              : Archive  (uget:US-Navy.soil_clim.bin@mary)

      (Cmd) [Ctrl-D]
      Vortex 1.2.2 completed ( Monday 05. March 2018, at 14:09:06 )
      $

Cela peut présenter quelques avantages :

   * Pour les systèmes où le chargement de Vortex prend un certain temps (*belenos*
     par exemple), cela peut éviter de charger ``uget.py`` de trop nombreuses fois.
   * Une auto-complétion existe (touche ``Tab``)
   * Au sein d'une session de l'invite de commande, il est possible de naviguer
     dans l'historique des commandes (en modes Emacs ou vi selon la configuration
     de votre shell)


Pense-bête
==========

Environnement
-------------

* le Vortex préconisé sur Bull se trouve sous : ``/home/mf/dp/marp/verolive/vortex/vortex-olive``
* ``uget.py`` se trouve sous: ``/home/mf/dp/marp/verolive/vortex/vortex-olive/bin/uget.py``
* Genv/Gget se trouve sous: ``/home/mf/dp/marp/gco/public/bin``
* le répertoire de travail uenv/uget est : ``$HOME/.vortexrc/hack/uget/$USER/``

    * ``env/`` : fichiers de conf (*i.e.* définition des "cycles" *uenv*)
    * ``data/`` : les ressources


Commandes
---------

* cloner un cycle GCO::

    uget.py hack genv al42_arome-op2.30 into al42_arome-dble.02@mary

* cloner un cycle collègue/perso::

    uget.py hack env al42_arome-dble.01@faure into al42_arome-dble.02@mary

* interroger un cycle collègue/perso (print écran, equiv. commande ``genv``)::

    uget.py pull env cy43t2_clim-op1.05@mary

* cloner une ressource GCO::

    uget.py hack gdata al42_arome-op2.15.nam into al42_arome-op2.16.nam.tgz@mary

* cloner une ressource collègue/perso::

    uget.py hack data al42_arome-dble.01.nam.tgz@faure into al42_arome-op2.16.nam.tgz@mary

* vérifier que tous les éléments existent bien, soit en local soit sur archive,
  chez soi, chez GCO ou chez un autre utilisateur::

    uget.py check env al42_arome-dble.02@mary

* historiser un cycle perso (y/c les ressources modifiées localement)::

    uget.py push env al42_arome-dble.02@mary

* historiser une ressource::

    uget.py push data al42_arome-op2.16.nam.tgz@mary

* nettoyer son répertoire de travail (hack) vis-à-vis de ce qui a été historisé::

    uget.py clean_hack

* lister les cycles/ressources disponibles chez un utilisateur::

    uget.py list env from faure
    uget.py list data from faure

* comparer deux cycles::

    uget.py diff env al42_arome-dble.02@mary wrt genv al42_arome-op2.30

* lister mes ressources pour livraison à GCO::

    uget.py export env al42_arome-dble.02@mary wrt genv al42_arome-op2.30

* je suis perdu::

    uget.py help

  et::

    uget.py help [hack|pull|check|push|diff|list|...]

