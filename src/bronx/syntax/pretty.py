"""
Making things pretty.
"""

import pprint

#: No automatic export
__all__ = []


def smooth_string(s, escaped_characters={' ': '_',
                                         '{': '', '}': '',
                                         '(': '', ')': '',
                                         '[': '', ']': '',
                                         '*': '', '?': ''}):
    """
    Returns str(*s*) escaping special characters that may
    be forbidden in filenames.

    :param escaped_characters: special characters to escape,
                               and their replacement in case.
    """
    result = str(s).strip()
    for repl in escaped_characters.items():
        result = result.replace(*repl)
    return result


EncodedPrettyPrinter = pprint.PrettyPrinter
