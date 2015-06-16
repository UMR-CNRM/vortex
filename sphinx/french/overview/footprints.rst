.. _footprints:

*************************
Le package « footprints »
*************************

Cette section présente les principales fonctionalités d'un package totalement indépendant de VORTEX en tant que tel,
mais qui fournit l'assise des principales classes d'objets utilisées dans VORTEX.

Une arlésienne de la programmation objet est que l'on aimerait bien le plus souvent ne pas avoir
à caractériser précisément l'objet que l'on veut utiliser pour remplir un certain rôle.
À tout le moins on ne voudrait pas à avoir à spécifier la classe qu'on instanciera pour obtenir ledit objet.
Il nous suffit le plus souvent de penser que tel ou tel objet réunit certaines qualités
ou être capable de réaliser telle ou telle action. On trouve souvent comme boutade
dans la littérature de programmation objet qu'un bon code objet est un code
où on ne manipule que des classes et jamais des objets.

C'est un peu ce rôle de dispensateur d'objets, sur la base de la simple description
de caractéristiques de classe, que le package « footprints » se propose faire.
C'est cela, et un peu plus, puisqu'il va permettre (à ce stade de la présentation il faut un peu faire acte de foi)
d'assurer la maintenabilité (dans le temps ou vis-à-vis de modifications de comportement
de tels ou tels « classes d'objets » qui ne s'imposeraient pas
immédiatement à l'esprit de leur créateur au moment de leur conception)
et surtout l'extensibilité de tout ensemble logiciel qui prendrait le package « footprints » comme fondement
de son développement. Cerise sur le gâteau, nous verrons qu'il assure même l’interopérabilité
entre différents ensembles logiciels pourvus qu'ils respectent des conventions purement formelles.

L'idée en est très simple. C'est une variante un tantinet élaborée du *Patern* de la fabrique.
Au lieu de décrire précisément un objet dans toutes ses caractéristiques (et notamment en fournissant sa classe),
on va prendre le problème à l'envers et tenter de répondre à la question : quelle classe serait suceptible
de s'instancier dans un objet qui aurait des caractéristiques compatibles avec celles dont j'ai connaissance a priori ?

Dit autrement, vous vous baladez dans un chemin forestier, et vous voyer des bouts d'empreintes mélangées,
dans la boue par exemple, ou parfois masquées par une flaque, ou des feuilles d'arbre arrachées, etc.,
et vous vous demandez : « quelle est donc la ou les bestiole-s qui ont pu laisser de telles empreintes » ?
Et si jamais il y a au moins une réponse à cette question eh bien, j'aimerai la connaître et en disposer
librement pour par exemple, évaluer ses autres caractéristiques (telle profondeur d'empreintes peut donner
une indication de poids par exemple, etc.) ou lui faire faire telle ou telle action (on dit : *méthode*).

Toute analogie ayant ses limites, jouons plutôt un peu avec ce package.

==========
Chargement
==========

On peut considérer ce composant de base sous différents angles :
celui de l'utilisateur de couches supérieures de la boîte à outils
qui ne s'apercevra pas de son existence (si tout va bien), ou celui du développeur
qui voudra pleinement profiter de l'extensibilité offerte par l'usage des « footprints » comme fabrique objet.
Et entre les deux, toutes une variété d'utilisations. A vous de faire le tri !

Un package ne se distingue pas d'un module pour un usage de premier niveau::

    >>> import footprints

Histoire de gagner du temps par la suite, nous adopterons la convention suivante::

    >>> import footprints as fp


En vrac::

    >>> fp.collectors.keys()
    []
