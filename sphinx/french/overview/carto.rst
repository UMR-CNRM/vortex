.. _overview-carto:

*********************************
Cartographie de la boîte à outils
*********************************

Comme annoncé dans la présentation des principes de base, VORTEX est une boîte à outils.

Ce n'est donc pas, en soi, une application (à l'exception du daemon destiné aux traitements asynchrones, voir plus bas).
La boîte à outils vous servira à construire des applications, des scripts, des outils de contrôle, etc.,
mais il n'y a rien dedans qui dispense de réfléchir à ce que l'on veut effectivement faire.
Par contre, ce que l'on veut faire, on doit pouvoir le faire de façon plus rationnelle et, espérons-le,
de façon plus élégante que la simple accumulation de lignes de shell.

Cela signifie aussi qu'il sera toujours possible de faire évoluer cette boîte à outils.
Si un outil manque, on l'ajoute. Si un autre est usé, on le remplace.
Si un autre encore est obsolète, on s'en débarrasse.

Pour tout de suite bien prendre les dimensions de cette « boîte à outils », le mieux est d'en faire une cartographie,
sous l'angle de son organisation comme ensemble logiciel, et sous celui de ses principales modalités d'utilisation.


========================
Organisation des sources
========================

Jetons un coup d'œil au répertoire principal...

.. code-block:: bash

    % ls -l
    total 84
    drwxr-xr-x 2 esevault algo  4096 juin  16 10:28 bin/
    drwxr-xr-x 2 esevault algo  4096 juin  16 10:28 conf/
    drwxr-xr-x 7 esevault algo  4096 juin  16 10:28 examples/
    -rw-r--r-- 1 esevault algo 21863 sept. 30  2014 LICENSE-en.txt
    -rw-r--r-- 1 esevault algo 22755 sept. 30  2014 LICENSE-fr.txt
    -rw-r--r-- 1 esevault algo  1937 mai    2  2013 README.md
    drwxr-xr-x 5 esevault algo  4096 mars  27 10:52 site/
    drwxr-xr-x 8 esevault algo  4096 juin  16 11:15 sphinx/
    drwxr-xr-x 9 esevault algo  4096 mars  12  2013 src/
    drwxr-xr-x 2 esevault algo  4096 juin  16 10:28 templates/
    drwxr-xr-x 6 esevault algo  4096 mars  18 16:13 tests/

Installation de site
--------------------

Sont regroupés dans ce répertoire les packages développés indépendamment de VORTEX. Il est donc possible
par exemple de pointer :envvar:`PYTHONPATH` uniquement sur ce répertoire.

.. code-block:: bash

    % export PYTHONPATH=/home/sevault/git-dev/vortex/site

On dispose dans ce cas des deux packages suivants:

    * footprints
    * jeeves


Le package vortex proprement dit
--------------------------------

Sous le répertoire principal :file:`src` se trouvent les principaux packages proposés par défaut dans le VORTEX.
Le seul qui soit absolument indispensable est celui nommé :mod:`vortex`. Les autres sont des extensions.
Il faut pour les utiliser étendre :envvar:`PYTHONPATH`.

.. code-block:: bash

    % export PYTHONPATH=/home/sevault/git-dev/vortex/site:/home/sevault/git-dev/vortex/src

Les importations suivantes sont alors possibles::

    >>> import vortex
    Vortex 0.9.20 loaded ( Thursday 18. June 2015, at 10:42:59 )
    >>> import common, olive, iga, gco

L'extension (ou package) :mod:`common` est tout spécialement recommandable puisqu'elle contient
toutes les classes de bases utilisées conjointement par l'équipe d'intégration des applications opérationnelles
et l'équipe de gestion des cycles opérationnels (GCO).

Répertoire bin
--------------

Le répertoire :file:`bin`, sans surprise, contient quelques exécutables, des utilitaires d'une importance relativement
marginale par rapport à la conception d'expériences de prévision numérique, ce qui ne veut pas dire que l'on pourrait
s'en passer facilement:

  * ggetall.py : récupération d'un jeu complet de composants versionnés par GCO ;
  * mkjob.py : génération de jobs opérationnels sur base d'un template ;
  * tbinterface.py : génération de l'interface de la toolbox VORTEX pour usage dans SWAPP/OLIVE ;

Il faut mentionner à part l'outil de lancement du daemon de traitement de tâches asynchrones, *litj.py*,
c'est-à-dire *Leave It To Jeeves* dont l'usage sera détaillé dans la section :ref:`overview-async`.

Répertoire conf
---------------

Il contient tous les fichiers au format *ini* de python qui pourraient éventuellement servir en cours d'exécution
et dont l'usage sera détaillé par après en fonction de la mise en œuvre de tel ou tel composant de la toolbox.

.. code-block:: bash

    % ls -l conf
    total 56
    -rw-r--r-- 1 esevault algo  764 juin  16 10:28 auth-perms-actions.ini
    -rw-r--r-- 1 esevault algo  266 mai   28 18:59 auth-users-groups.ini
    -rw-r--r-- 1 esevault algo 2177 avril  3 16:03 geometries.ini
    -rw-r--r-- 1 esevault algo 5895 févr. 14  2014 helper-namselect.ini
    -rw-r--r-- 1 esevault algo 1776 mai   28 18:59 iga-map-resources.ini
    -rw-r--r-- 1 esevault algo 1111 juin  16 10:28 jeeves-test.ini
    -rw-r--r-- 1 esevault algo  479 juin  16 10:28 job-default.ini
    -rw-r--r-- 1 esevault algo  342 nov.  18  2014 oparchive-glue.ini
    -rw-r--r-- 1 esevault algo  681 juin  16 10:28 opmail-catalog.ini
    -rw-r--r-- 1 esevault algo 1654 juin  16 10:28 opmail-directory.ini
    -rw-r--r-- 1 esevault algo 1901 mai   28 18:59 target-beaufix.ini
    -rw-r--r-- 1 esevault algo  565 févr. 11  2014 target-necsx9.ini
    -rw-r--r-- 1 esevault algo 1868 mai   28 18:59 target-prolix.ini

Répertoire templates
--------------------

Il contient les *templates* qui seront remplis pour des créations de jobs opérationnels types,
des maquettes de courrier, des outils de synchronisation au fil de l'eau, etc.

.. code-block:: bash

    % ls -l templates
    total 20
    -rw-r--r-- 1 esevault algo 1727 juin  16 10:28 job-default.tpl
    -rw-r--r-- 1 esevault algo 1889 juin  16 10:28 job-optest.tpl
    -rw-r--r-- 1 esevault algo  635 juin  16 10:28 opmail-test.tpl
    -rw-r--r-- 1 esevault algo 2615 juin  16 10:28 sync-fetch.tpl
    -rw-r--r-- 1 esevault algo 1168 juin  16 10:28 sync-skip.tpl

Répertoire examples
-------------------

Les exemples sont le plus souvent pris dans le sens de bac à sable. Ils sont maintenus avec plus ou moins
de régularité en phase avec les développements. La plus grande prudence est donc de mise sur ce que l'on
peut déduire (ou pas) de l'exécution d'un des exemples.

La rationalisation des exemples et leur phasage sur la dernière *release* est une proposition toujours
renouvelée, et pour laquelle il manque toujours un-e volontaire ;-)

Répertoire tests
----------------

Les tests sont quant à eux maintenus avec une certaine attention. En particulier ceux sur les composants de base.
Mais il y a aussi toute une batterie de tests de manipulation des ressources météorologiques, dans les espaces
de nom "recherche" ou "oper".

=======================
Les modes d'utilisation
=======================

Ils sont au nombre de quatre: l'interactif, l'usage indifférencié de l'API dans un
développement quelconque, le scriptage automatique OLIVE, le layout de jobs/tasks de l'OPER.

Mode interactif
---------------

C'est un mode d'utilisation fondamental et qui n'est pas sans influence sur ce qu'il est possible
de concevoir en terme de boîte à outils: tout ce qu'il est possible de faire avec l'API complète
doit être accessible en interactif.


.. seealso:: les pages dédiées au mode d'utilisation olive et oper...

    * :ref:`overview-olive`
    * :ref:`overview-opjobs`
