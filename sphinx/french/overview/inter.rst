.. _overview-inter:

*****************
VORTEX interactif
*****************

======================
Configuration standard
======================

Autant se mettre dans des pantoufles confortables. Voici par exemple un fichier de configuration standard
sur un calculateur de Météo-France::

    # Some defaults settings for python using vortex

    import atexit
    import os
    import sys
    import readline
    import rlcompleter

    # Version de Vortex utilisée sous Olive
    toolbox_root = '/home/mf/dp/marp/verolive/vortex/vortex-olive'

    readline.parse_and_bind("set show-all-if-ambiguous on")
    readline.parse_and_bind('tab: complete')

    historyPath = os.path.expanduser("~/.pyhistory")

    def save_history(historyPath=historyPath):
        import readline
        readline.write_history_file(historyPath)

    if os.path.exists(historyPath):
        readline.read_history_file(historyPath)

    atexit.register(save_history)
    del os, atexit, readline, rlcompleter, save_history, historyPath

    try:
        sys.path.insert(0, toolbox_root + '/site')
        import footprints as fp
        try:
            sys.path.insert(0, toolbox_root + '/src')
            import vortex
            from vortex import toolbox
            from vortex.tools import date
            from vortex.tools import lfi, odb
            t = vortex.ticket()
            sh = t.sh
            e = t.env
            fpx = fp.proxy
            shlfi = fpx.addon(shell=sh, kind='lfi')
            shodb = fpx.addon(shell=sh, kind='odb')
        except Exception as trouble:
            print trouble
            print "vortex: not loaded"
    except Exception as pbfp:
        print pbfp
        print "footprints: not loaded"

Tout le code avant le bloc :keyword:`try` est sans surprise. Il ne sert qu'à gérer l'historique
de vos commandes, l'expansion automatique, la sauvegarde de l'historique, etc.

Nous faisons ensuite en fait deux blocs :keyword:`try`:
un pour le chargement du package :mod:`footprints`, un autre pour celui du package :mod:`vortex`.

Par pur comfort, nous rendons également dispobibles deux modules super-stars:

  * l'interface procédurale nommée :mod:`~vortex.toolbox` qui permet de charger rapidement des *handlers* de resources ou de générer directement des sections *input*, *output*, *algo*, *promise*, etc. -- tout ceci sera détaillé par après.
  * le module :mod:`~vortex.tools.date`, qui l'on peut s'en douter est un n-ième outil de manipulation de dates, qui étend celui de python ;

Histoire de tout de suite pouvoir manipuler des ressources dans ces formats spécifiques, nous chargeons
explicitement les modules :mod:`~vortex.tools.lfi` et :mod:`~vortex.tools.odb`, et générons à la volée
des extensions du shell courant.

.. seealso:: pour tous ces modules regroupés dans :mod:`vortex.tools`, voir la section :ref:`overview-tools`.
