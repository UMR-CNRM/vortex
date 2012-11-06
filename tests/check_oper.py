#!/usr/bin/python
# -*- coding: utf-8 -*-


import sys
from os import getcwd, walk
import os.path
from optparse import OptionParser
import unittest
from warnings import warn

options = [{'noms': ('-r', '--repertoire'), 'dest': 'rep',
            'help': ('Spécifie le repértoire à utiliser, si non fourni,'
                     'le chemin courant est utilisé')}]

def _print_line():
    print '-'*100

def main(options, arguments, parser):
    if options.rep is not None:
        chemin = options.rep
    else:
        if len(arguments) > 0:
            print parser.usage
            sys.exit(2)
        chemin = getcwd()

    chemin = os.path.normpath(chemin)
    if chemin.endswith(os.path.sep):
        chemin = chemin[:-1]

    print "chemin en cours %s" % chemin
    print 'Parcours du répertoire'
    test_modules = []
    for racine, reps, fichiers in walk(chemin):
        dossier = os.path.basename(racine)
        print "\n       dossier en cours %s\n" % dossier
        if dossier == 'tests' or dossier.startswith('tests_'):
            for fichier in fichiers:
                #print "       fichier en cours %s" % fichier
                if (fichier.startswith('test') and
                    fichier.endswith('_oper.py') and
                    fichier != 'test.py'):
                    nom_complet = os.path.join(racine, fichier)
                    test_modules.append((nom_complet, fichier[:-3]))
                    sys.stdout.write('.')
                    sys.stdout.flush()

    print '\n%d module(s) de test trouvé(s)\n' % len(test_modules)

    suite = unittest.TestSuite()
    dernier_contexte = None
    added_paths = []

    for module in test_modules:
        module_path = os.path.dirname(module[0])

        #chargement d'un script si nécessaire
        contexte = os.path.join(module_path, 'contexte.py')
        if os.path.exists(contexte) and dernier_contexte != contexte:
            execfile(contexte)
            dernier_contexte = contexte

        if module_path not in sys.path:
            sys.path.append(module_path)

        m = __import__(module[1])
        if 'get_test_class' in m.__dict__:
            class_type = m.get_test_class()
            print "class_type %s" % class_type
            if type(class_type) == list:
                for cls in class_type:
                    test_suite = unittest.TestSuite((
                        unittest.makeSuite(cls), ))
                    suite.addTest(test_suite)
            else:
                test_suite = unittest.TestSuite((
                    unittest.makeSuite(class_type), ))
                suite.addTest(test_suite)
        else:
            warn("%s n'a pas de fonction get_test_class" % module[0])

    nb_test_case = suite.countTestCases()
    if nb_test_case == 0:
        print "Aucun test."
        sys.exit(2)

    print '\nLancement de %d test(s)...' % nb_test_case
    _print_line()
    ferr = open('tmp.err.oper', 'w')
    campagne = unittest.TextTestRunner(stream = ferr, verbosity=2)
    campagne.run(suite)
    ferr.close()

    for added_path in added_paths:
        sys.path.remove(added_path)

if __name__  == '__main__':
    parser = OptionParser()
    parser.usage = 'tester [-r repertoire]'
    for option in options:
        param = option['noms']
        del option['noms']
        parser.add_option(*param, **option)
    options, arguments = parser.parse_args()
    sys.argv[:] = arguments
    main(options, arguments, parser)





