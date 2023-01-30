"""
A template of configuration file for TNT.
"""

# 1. Blocks to be added.
new_blocks = {'NAMNEW',
              }
# 2. Blocks to be moved. If target block exists, raise an error.
blocks_to_move = {'NAMOLD': 'NAMMOVED',
                  }
# 3. Keys to be moved. If target exists or target block is missing, raise an error.
# Blocks need to be consistent with above blocks movings.
keys_to_move = {('NAMMOVED', 'KEYOLD'): ('NAMNEW', 'KEYNEW'),  # change the key from block, and/or rename it
                }
# 4. Keys to be removed. Already missing keys are ignored.
# Blocks need to be consistent with above movings.
keys_to_remove = {('NAMBLOCK', 'KEYTOREMOVE'),
                  }
# 5. Keys to be set with a value (new or modified). If block is missing, raise an error.
# Blocks need to be consistent with above movings.
keys_to_set = {('NAMBLOCK1', 'KEY1'): 46.5,
               ('NAMBLOCK2', 'KEY2(1:3)'): [5, 6, 7],
               ('NAMBLOCK3', 'KEY3(50)'): -50,
               }
# 6. Blocks to be removed. Already missing blocks are ignored.
blocks_to_remove = {'NAMBLOCK',
                    }
# 7. Macros: substitutions in the namelist's values. A *None* value ignores
# the substitution (keeps the keyword, to be substituted later on).
macros = {'VAL_TO_SUBSTITUTE': 8,
          'VAL_TO_KEEP_AND_BE_SUBSTITUTED_LATER': None}
