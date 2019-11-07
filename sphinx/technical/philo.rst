.. _overview-philo:

******************
Quelques principes
******************

Cette section s'efforce de donner une vue d'ensemble de quelques notions simples,
mais... qui furent parfois longuement discutées ! La capacité à nommer les choses de façon claire
(on espère) et homogène (entre équipes) est un pas en avant important... indépendamment de la moindre ligne de code !

=================
Le système de PNT
=================

Nous rappellerons ici de pures généralités... l'idée étant de réduire progressivement
le champ d'investigation aux aspects spécifiques qui sont dans le périmètre du projet VORTEX,
au prix de simplifications permettant d'obtenir un découpage à la serpe entre les :

1. systèmes de veille, de collecte et de prétraitement des observations ;
2. systèmes de prévision numérique du temps ;
3. systèmes de post-traitement et de mise à disposition des données produites ou analysées.

Chacun de ces systèmes combine :

* des données spécifiques (nature, format, traitement) ;
* des programmes informatiques dédiés (essentiellement développés en interne ou collaboration) ;
* des cibles d'exécution (ou ressources informatiques) pour ces programmes (systèmes linux pour l'essentiel).

.. note::
    C'est bien entendu le **système n°2** qui retiendra ici notre attention, celui dit de *PNT* !

Les données manipulées (ou ressources) sont :

* en entrée : une sélection d'observations issues du **système n°1** ;
* des données produites mais réentrantes ;
* des champs climatologiques, des coefficients ou paramètres considérés comme « constants », etc.

Les programmes informatiques mobilisés sont :

* pour l'essentiel des composants de l'ensemble logiciel IFS-ARPEGE (collaboration CEPMMT et consortium ALADIN/HIRLAM) ; on parlera de « noyau de calcul » pour ces composants ;
* rédigés en FORTRAN, C, C++ et compilés spécifiquement pour nos systèmes informatiques.

Les cibles d'exécution sont :

* pour l'essentiel les supercalculateurs BULL (tournant sous Linux) ;
* mais aussi d'autres clusters Linux périphériques ;
* et en sortie, des systèmes d'archivages ou bases de données (du **système n°3**).

==========================
Notion de mode d'exécution
==========================

La mise en œuvre d'un modèle de PNT ne se résume pas à sa simple « exécution » (lancement d'une app).
Cette mise en œuvre s'appuie sur des présupposés et des modalités pratiques.

Parmi les présupposés, le cadre le plus général est bien entendu donné par le système d'exploitation
de la cible d'exécution (Linux dans le cas des supercalculateurs BULL) mais aussi par :

* les librairies systèmes ou applicatives, avec une attention toute particulières pour celles en charge du parallélisme ou de l'optimisation ;
* les variables d'environnement ou de configuration du système.

Mais pour un programme ou un « modèle » donné, il faudra également spécifier :

* des arguments éventuels (paramètres variables) ;
* des paramètres de configuration du modèle (en général regroupés dans des fichiers spécifiques) ;
* des variables d'environnement ;
* des noms spécifiques à attribuer aux ressources d'entrée ;
* des paramètres d'interaction avec le système et d'allocation de ressources (parallélisme encore une fois, par exemple).

=========================
Notion de flux de données
=========================

La finalité d'un mode d'exécution est toujours, sur la base de ressources qui lui sont fournies (ou pas) en entrée,
de produire (ou pas) de nouvelles ressources. On parle de données d'entrée et de données de sortie.
L'ensemble constitue le flux de données *local* à un mode d'exécution.

Exemple d'une prévision ARPEGE :

* en entrée : un état analysé de l'atmosphère ;
* en sortie : un ou plusieurs états prévus de l'atmosphère (à diverses échéances).

À ces ressources qui constituent le « flux de données » proprement dit,
il convient d'ajouter les ressources « hors flux » que sont les pseudo-constantes
et de ressources de paramétrisation (voir plus haut).

Nous parlons souvent de séquence **ixo** pour désigner cette séquence *inputs-execution-outputs*
qui constitue la trame de base de toute tâche élémentaire.

.. warning:: La très grande trivialité de cette séquence **ixo** masque deux écueils\

    1. une vision simplificatrice qui oublie la relative complexité qui se cache derrière cette abstraction et les actions complémentaires, qui peuvent être nombreuses (en contexte opérationnel tout au moins) ;
    2. une vision particulariste qui ne verrait pas que ce caractère générique reste le fondement de la capacité objective à partager des outils communs ;

Des données « en sortie » d'un mode d'exécution peuvent bien entendu se retrouver « en entrée » d'un autre,
ou du même à une autre date, etc. C'est le flux de données *global* d'une simulation de PNT.

=======================
Notion de configuration
=======================

On désigne communément (dans la sphère recherche comme en opérations) un groupement logique
d'une ou plusieurs occurrences de tâches de traitement de données par des programmes informatiques
comme étant une *configuration*. Celle-ci vise en général à satisfaire une exigence
de relativement « haut niveau » : produire un état analysé de l'atmosphère, une prévision d'ensemble, etc.

Une assimilation ARPEGE se compose ainsi de 17 tâches différenciées.
Une assimilation AROME d'une quinzaine.
L'assimilation d'ensemble ARPEGE se compose de 13 tâches hors membres de l'ensemble et de 24 autres par membre
(et il y a 25 membres dans la nouvelle version HR de la chaîne).

Chaque configuration a son propre flux de données, que l'on peut qualifier de flux « interne »
mais aussi des dépendances à des ressources d'autres configurations, créant ainsi un flux « externe ».

Par exemple l'assimilation puis la prévision AROME requièrent les états prévus de l'atmosphère par ARPEGE
comme conditions aux limites, etc.

Il se crée ainsi un vaste réseau de dépendances entre tâches de mêmes configurations ou de configurations différentes.

Nous verrons comment VORTEX se propose de clarifier ces flux de données.

==================================================
La mise en œuvre opérationnelle des modèles de PNT
==================================================

On le voit, « lancer » un simple « modèle », selon le langage courant, recouvre tout un ensemble de tâches,
de paramétrisations, d'interactions, qui sont très largement « cachées » au profane,
d'autant que d'autres aspects se surajoutent dans le cadre proprement opérationnel
(phasage entre supercalculateurs, sauvegarde asynchrone, reporting, etc.)

On désigne l'ensemble des outils développés pour une telle mise en œuvre par le doux vocable de  « tuyauterie ».

Pour ce qui est de Météo-France, cette tuyauterie opérationnelle se compose essentiellement de « scripts shell »
(langage interprété natif du système d'exploitation, ici Linux/bash) et de fichiers de paramétrisations
servant à positionner des variables d'environnement.

L'ensemble de ces scripts sont invoqués dans des « jobs » (meta-scripts) qui recouvrent plus ou moins
la notion de « configuration » évoquée précédemment (en fait il faut un ou quelques jobs pour une configuration donnée).

Le séquencement (gestion explicite des dépendances, lancements de tâches, etc.) de ces jobs est assuré
par un système séparé (*SMS*, à Météo-France, *ECFlow* au CEPMMT), maintenu en dehors du périmètre d'analyse de VORTEX.

=================================================
Modalités de la transition recherche – opérations
=================================================

Ce transfert de configurations de PNT d'un contexte dit de *recherche* à un contexte dit *opérationnel* est clairement
une des principales motivations du projet VORTEX.

Pour illustrer la chose, nous prendrons le cas d'une configuration développée au GMAP.
Dans ce cas, celle-ci est déjà disponible sous OLIVE, le système interactif de création
et lancement d'expériences de PNT du CNRM, co-administré avec DirOP/COMPAS/GCO.

Le transfert proprement dit
---------------------------

Les étapes du processus de transfert sont alors les suivantes :

1. versionnement de tous les composants constitutifs de la nouvelle configuration opérationnelle (ou de sa mise à jour) effectué par DirOP/COMPAS/GCO ;
2. transfert de ces composants à DSI/OP/IGA qui les renomme, les copie, selon une logique différente et spécifique sur les espaces disques permanents du supercalculateur ;
3. description du flux de données par l'équipe DirOP/COMPAS/GCO et des nouveaux modes d'exécution, avec le soutien du CNRM/GMAP ;
4. conversion de cette description et de ces informations en script shell par DSI/OP/IGA ;
5. tests de bonne exécution par DSI/OP/IGA avec le support de DirOP/COMPAS/GCO et CNRM/GMAP ;
6. contre-validation par DirOP/COMPAS/GCO après mise en opérations.

Mais il est possible de faire mieux (ou pire, en l’occurrence) dans le cas d'une configuration
à vocation opérationnelle qui pour une raison ou une autre est hors cadre OLIVE ou GMAP.
Dans ce cas, une quatrième équipe est mobilisée (à la DP en général) pour assurer
le suivi en opérations de ladite configuration. On a ainsi un double ou triple transfert, parfois simultanés :

* transfert du CNRM vers DP/XXX ;
* transfert de DP/XXX vers DirOP/COMPAS/GCO ;
* transfert partiel et « officieux » de DP/XXX vers DSI/OP/IGA pour anticiper la transition ;
* transfert « officiel » de DirOP/COMPAS/GCO vers DSI/OP/IGA reprenant les 6 points exposés précédemment.

Et bien entendu pour chacun des espaces de travail, une version différente :

* du stockage des ressources constantes ;
* de l'espace de nommage des ressources du flux de données.

La contre-validation
--------------------

Si la tuyauterie n'est que rarement sous le feu des projecteurs
(et *a priori*, il n'y a pas de raison que ce soit le cas outre mesure),
c'est encore plus vrai d'une composante essentielle du transfert de la recherche aux opérations : la contre-validation.

Que peut-on en dire ?

* Il s'agit de vérifier qu'après le transfert dans le contexte opérationnel et la mise en œuvre effective de la nouvelle configuration ou de toute mise à jour partielle, la configuration opérationnelle est strictement reproductible (au bit près) dans l'environnement de développement (ie, sous OLIVE).

* C'est une tâche colossale, récurrente, très consommatrice en temps et non-déterministe, mais absolument indispensable : elle seule nous permet d'assurer que ce qui tourne aux opérations est bien ce qui est attendu et, plus encore, que les nouveaux développements en mode recherche se fondent sur une base indiscutable.

* Cette tâche est assurée par DirOP/GMAP/COMPAS. Elle soulage DSI/OP/IGA de la nécessité de faire la démonstration de la totale validité des mises à jour opérationnelles.

=================
Pourquoi VORTEX ?
=================

Une façon (parmi d'autres) de répondre à la question du « pourquoi vortex » est de penser
à ce qui se passe en cas d'anomalie dans le processus de contre-validation décrit précédemment : il faut
alors partir en chasse de la première « bifurcation » de résultats entre deux systèmes n'ayant strictement
rien d'autre en commun que les modèles eux-mêmes (en tant que programmes compilés) :

* ni le rangement et la nomenclature des constantes ;
* ni l'espace de noms dans lequel s'inscrit le flux de données ;
* ni les modalités pratiques (scriptage) des modes d'exécutions.

Et pourtant ! À force de rigueur et de travail, on arrive à assurer cette contre-validation,
preuve que fondamentalement (et météorologiquement parlant) on fait la même chose (ce qui est somme toute plutôt rassurant) !

::

    Cette simple constatation doit constituer le socle du travail collaboratif entre équipes.

L'idée est donc de créer un outil mutualisé entre intervenants qui permettrait d'avoir sur les trois points exposés
ci-dessus un usage commun entre les opérations et toutes les équipes de recherche,
indépendamment des fioritures des uns et des autres pour couvrir des fonctionnalités plus spécifiques.

La question se transforme et devient : quelle forme devrait prendre cet « outil » ?

============================
Principes généraux de VORTEX
============================

Partons de l'acronyme, qui finalement est plutôt explicite
et décrit assez bien les spécifications générales attendues de cet outil :

* **V** ersatile

  * attention : dans le sens anglais, ie : pouvant se comporter de façon différente, adaptée, etc. Ainsi, selon tel ou tel contexte, des objets différents peuvent entrer dans la danse et leur comportement peut varier.

* **O** bjects

  * nous manipulerons donc des « objets », des entités au plus près des aspects métiers, ou des contraintes techniques...

* **R** ounded-up in a

  * ces objets ne traîneront pas dans la nature, nous prendrons soin de les regrouper, versionner, etc., pour les regrouper...

* **T** oolbox for

  * dans une boîte à outils, c'est-à-dire que l'on n'impose pas une application, mais que l'on fournit les composants pour construire les applications de son choix

* **E** nvironmental

* e **X** periments

  * il s'agit bien d'expériences de simulation numérique, en privilégiant notre domaine : les géo-sciences « environnementales » (ok, c'est un peu fourre-tout).

L'usage de la boîte à outils VORTEX permet (entre autres choses) :

* non plus d'aller chercher des ressources pour les modèles en fonction de leur localisation « physique » (nommage dans l'arborescence du système de fichiers de la cible d'exécution), mais selon un modèle descriptif : une analyse, de tel jour, à telle heure, sur le réseau de production, produite par tel modèle, sur telle géométrie, etc.
* de bénéficier de modes d'exécution communs, donc validés par la communauté des utilisateurs ;
* de propager à tous les utilisateurs les bénéfices du versionnement systématique de tous les composants opérationnels effectué par DirOP/COMPAS/GCO ;
* de mutualiser les modes de manipulation et de micro-traitements de formats de données spécifiques (GRIB, FA, namelistes FORTRAN, fichiers issus du serveur d'IO parallèle, etc.) ;
* de rationaliser l'usage des données en ligne sur le supercalculateur par rapport à leur archivage quasi-systématique par chaque utilisateur ;
* d'effectuer des expériences de PNT auto-validantes, entre expériences en mode recherche ou en mode opérationnel par exemple ;
* de formaliser et de généraliser l'usage d'actions asynchrones, via un serveur dédié.

===========================
Ce que peut résoudre VORTEX
===========================

Dans la mesure où il s'appuie abondamment sur un modèle descriptif,
découplé de la récupération effective de telle ou telle ressource,
ou de l'activation de tel ou tel mode d'exécution,
l'usage commun d'une boîte à outils comme VORTEX va permettre de « rédiger » ou de « décrire »
une tâche en mode opérationnel de façon extrêmement proche de sa version recherche,
facilitant considérablement les opérations de transfert.
Notamment, le flux de données devient **explicite** et **partagé**.

Dans le contexte opérationnel, la validation de premier niveau est donc grandement facilitée,
tout comme la contre-validation dans le contexte recherche.

De nouvelles possibilités s'ouvrent aux opérations, notamment la capacité à se dissocier
du temps réel pour combler des « trous » d'exécution liés à des interruptions
de la chaîne opérationnelle (en particulier pour sa version d'évaluation).

====================================
... et ce qu'il ne peut pas résoudre
====================================

En vrac... mais la liste est probablement bien bien plus longue !

* l'interaction avec le système de lancement ;
* les aléas des tests de reproductibilité (contre-validation) ;
* l'agencement des tâches et jobs au sein d'une configuration ;
* l'optimisation sur un système donné ;
* etc.

===================
Où en sommes-nous ?
===================

Plusieurs niveaux de réponse sont possibles. Si l'on prend un calendrier et que l'on regarde en arrière,
il y a de quoi être saisi de vertige devant l'incroyable durée, et de ce projet (effectif en 2010),
et de la réflexion sur le sujet, ou même les premières tentatives avortées (1995).

La dimension technique n'est évidemment pas spécialement en cause. Je serai tenté de dire que l'on
trouve toujours une solution technique, plus ou moins bonne, pour résoudre ce genre de problème.

Alors ? Alors, rien de décisif pour expliquer cet état de fait.
Il faut bien reconnaître que la tentation de ne rien bousculer est grande,
et souvent même légitime dans le système d'organisation du travail qui est le nôtre.
Reconnaître que les dissensions et divers savonnages entre directions ont aussi pu avoir un impact.
Que l'on n'arrive pas toujours à faire prendre la mayonnaise du travail collaboratif.
Que l'on gère la pénurie au mieux...

Aussi faut-il essayer de prendre le problème par le bon bout : prendre la mesure des développements réalisés,
jeter un œil bienveillant aux premières réalisations pratiques,
et, sur la base cette évaluation des fondements logiciels du VORTEX, voir si un usage commun peut tout de même voir le jour.
