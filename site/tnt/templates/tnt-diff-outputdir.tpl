# -*- coding: utf-8 -*

# 1. Blocks to be added.
new_blocks = set([
    ${TPL_NEWBLOCKS}])

# 4. Keys to be removed. Already missing keys are ignored.
keys_to_remove = set([
    ${TPL_RMKEYS}])

# 5. Keys to be set with a value (new or modified). If block is missing, raise an error.
keys_to_set = {
    ${TPL_NEWKEYS}}
# of which modified values:
${TPL_MODIFIED}

# 6. Blocks to be removed. Already missing blocks are ignored.
blocks_to_remove = set([
    ${TPL_RMBLOCKS}])
 