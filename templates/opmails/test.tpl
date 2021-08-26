
Variable prise dans env  : env_var  = $env_var
Variable prise en add_on : extra    = $extra
Variable prise en add_on : op_suite = $op_suite
Variable manquante       : missing  = $missing
Syntaxe illégale         : op_suite = $(op_suite)

Substitution:
   $$op_suite         = $op_suite
   $${op_suite}       = ${op_suite}
   test_$$op_suite    = test_$op_suite
   test_$$op_suite@mf = test_$op_suite@mf

Accents:
   Portez ce vieux whisky au juge blond qui fume : dès Noël où
   un zéphyr haï le vêt de glaçons würmiens il dîne à s'emplir
   le cæcum d’exquis rôtis de bœuf à l’aÿ d’âge mûr et s'écrie
   "À Â É È Ê Ë Î Ï Ô Ù Û Ü Ç Œ Æ" !
