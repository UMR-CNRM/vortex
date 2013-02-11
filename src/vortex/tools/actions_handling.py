# -*- coding:Utf-8 -*-

r"""
Interface for sending messages, products...
The main class ActionsLoader contains the main methods so as to handle
actions related to sending.
"""

__all__ = []

#For the moment, we import explicitly iga/services/actions module. But we could think of
#another way to do that. For instance, we could check a global variable
#stored in the environment...
import env
operenv = env.current()

try:
    default_actions = __import__(operenv.default_actions)
    #import iga.services.actions as default_actions
except IndexError:
    try:
        import iga.services.actions as default_actions
    except:
        raise
#We also need the string value of the key controlling the update of the action,
#the name of the running command and finally the command names
from actions import _RUN_COMMAND, _COMMAND_NAMES

#We must define here a default construction of the ActionLoader object.
#For the moment, I decide to take the actions defined in the iga/service/actions module
_BASIS = default_actions._ACTIONS_DICT

def make_action(action):
    """
    Decorator used to build the function calling the dispatcher. The arguments
    varies cwaccording to the type of the action
    """
    def wrapper(self, **kwargs):
        try:
            prefix, suffix = action.split('_')
        except ValueError:
            suffix = '-9999'
        #if it's greater than -3 it implies that one elmt contains suffix
        if sum([elmt.find(suffix) for elmt in _COMMAND_NAMES]) > -3:
            return self.dispatch(suffix, prefix)
        #otherwise we're dealing with a direct action
        else:
            arg1 = _RUN_COMMAND
            return self.dispatch(arg1, kwargs)
    return wrapper

def dispatch(self, command, arg1=None, **kw):
    """
    This function tries to find and call the function enable to realize the
    action. This function must belong to the _def_module.
    """
    if hasattr(self._def_module, command):
        method = getattr(self._def_module, command)
        if type(arg1) == dict :
            return method(**arg1)
        else:
            return method(arg1)
    else:
        raise Exception

class MetaLoader(type):
    """
    This metaclass adds the elements linked to the available actions in the
    interface. For each key of args[0]['__basis__'], we must add a function.
    """
    def __init__(cls, name, bases, *args, **kwargs):
        type.__init__(cls, name, bases, *args, **kwargs)
        cls.dispatch = dispatch 
        for action in args[0]['__basis__']:
            for name in MetaLoader.get_name(action):
                setattr(cls, name, make_action(name))

    @classmethod
    def get_name(cls, action):
        res = [action  + elmt for elmt in _COMMAND_NAMES]
        res.insert(0, action)
        return res

    
class ActionsLoader(object):
    """
    Main interface to perform sending actions
    """
    __metaclass__ = MetaLoader
    __basis__ = _BASIS

    def __init__(self, def_module=default_actions):
        self._def_module = def_module

