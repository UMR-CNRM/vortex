# -*- coding:Utf-8 -*-

r"""
Authorizations module.

This modules allow the system to check if the processed actions is authorized or
not. Via the sessions module, glove et environment objects support the
verification.
"""

import logging
from vortex import sessions
from collections import namedtuple, _itemgetter
from vortex.tools.config import GenericConfigParser


#get the current ticket
tck = sessions.current()
#get the attached environment
env = tck.env

class GroupHandler(tuple):
        'GroupHandler(grp_permis, grp_users)'

        __slots__ = ()

        _fields = ('grp_permis', 'grp_users')

        def __new__(_cls):
            ConstPermissions = namedtuple(
                                       'ConstPermissions',
                                       ConstGrpActConfigParser().fields_name(),
                                   )
            dico_mga = ConstGrpActConfigParser().as_dict()
            dico_mgu = ConstGrpUsrConfigParser().as_dict()
            mga = ConstPermissions(**dico_mga)
            mgu = ConstPermissions(**dico_mgu)
            return tuple.__new__(_cls, (mga, mgu))

        @classmethod
        def _make(cls, iterable, new=tuple.__new__, len=len):
            'Make a new GroupHandler object from a sequence or iterable'
            result = new(cls, iterable)
            if len(result) != 2:
                raise TypeError('Expected 2 arguments, got %d' % len(result))
            return result

        def __repr__(self):
            return 'GroupHandler(grp_permis=%r, grp_users=%r)' % self

        def _asdict(t):
            'Return a new dict which maps field names to their values'
            return {'grp_permis': t[0], 'grp_users': t[1]}

        def _replace(_self, **kwds):
            'Return a new GroupHandler object replacing specified fields with new values'
            result = _self._make(map(kwds.pop, ('grp_permis', 'grp_users'), _self))
            if kwds:
                raise ValueError('Got unexpected field names: %r' % kwds.keys())
            return result

        def __getnewargs__(self):
            return tuple(self)

        def get_grp_permis(self, name=None):
            if name:
                return getattr(self.grp_permis, name, None)
            else:
                return None

        def get_grp_users(self, name=None):
            if name:
                return getattr(self.grp_users, name, None)
            else:
                return None

        def get_list_users(self):
            """docstring for get_list_users"""
            for user_grp in self.grp_users._asdict().keys():
                yield user_grp, self.grp_users._asdict()[user_grp]

        grp_permis = property(_itemgetter(0))
        grp_users = property(_itemgetter(1))

        def get_grp_permis_fields(self):
            return self.grp_permis._fields

        def get_grp_users_fields(self):
            return self.grp_users._fields

class ConstGrpUsrConfigParser(GenericConfigParser):

    def __init__(self):
        GenericConfigParser.__init__(self, 'const_grpuser_iga.ini')

    def as_dict(self):
        dico = {}
        for key in self.sections():
            dico[key] = [elmt for elmt in self.options(key)]
        return dico

    def sections_as_tuple(self):
        return tuple(self.sections())

    def fields_name(self):
        return " ".join(self.sections_as_tuple())

class ConstGrpActConfigParser(GenericConfigParser):

    def __init__(self):
        GenericConfigParser.__init__(self, 'const_grpact_iga.ini')

    def as_dict(self):
        dico = {}
        list_key = []
        list_values = []
        for key in self.sections():
            for option in self.options(key):
                list_key.append(option)
                value = self.get(key, option)
                if value in ["true", "on" "True", "1"]:
                    value = True
                else:
                    value = False
                list_values.append(value)
            dico[key] = dict(zip(list_key, list_values))
            list_key = []
            list_values = []
        return dico

    def sections_as_tuple(self):
        return tuple(self.sections())

    def fields_name(self):
        return " ".join(self.sections_as_tuple())

def getuser():
    r"""
    Return the “login name” of the user.

     function checks the environment variables LOGNAME, USER, LNAME and
    USERNAME, in order, and returns the value of the first one which is
    set to a non-empty string. If none are set, the login name from the
    password database is returned on systems which support the pwd module,
    otherwise, an exception is raised (for now it returns None).
    """
    global env
    _ALIAS = ['LOGNAME', 'USER', 'LNAME', 'USERNAME']
    for elmt in _ALIAS:
        user = env.getvar(elmt)
        if user:
            return user
    return None


def is_user_authorized(action_type):
    r"""
    Check if the user of the current session know if the current user is
    allowed to perform the task. It also check if the rights had been altered
    in any ways.

    :returns True or False
    """
    user = getuser()
    grp = None
    b_right = False
    group_hdl = GroupHandler()
    for grp_name, values  in group_hdl.get_list_users():
        if user in values:
            grp = grp_name
            break
    if grp:
        #group_hdl became an attribute of the module thanks to prepare function
        #call above
        #search for the permissions of the found group
        b_right = group_hdl.get_grp_permis(grp)[action_type]
    else:
        logging.error("No group found")
    if not b_right:
        logging.warning("Action %s is not authorized for the current user %s",
                        action_type, user)
    #check if the permissions were altered only if the operation is
    #authorized
    if b_right:
        genuine_grp = GroupHandler()
        if group_hdl.get_grp_permis(grp) != genuine_grp.get_grp_permis(grp):
            logging.error("Permissions were altered !!!")
    return b_right

