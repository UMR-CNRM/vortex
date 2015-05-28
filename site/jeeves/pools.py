#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import pwd
import shutil
import io
import zipfile
import json

from glob import glob
from datetime import datetime

import footprints

#: No automatic export
__all__ = []


# Module Interface

def get(**kw):
    """Return actual session ticket object matching description."""
    return Deposit(**kw)

def keys():
    """Return the list of current session tickets names collected."""
    return Deposit.tag_keys()

def values():
    """Return the list of current session ticket values collected."""
    return Deposit.tag_values()

def items():
    """Return the items of the session tickets table."""
    return Deposit.tag_items()

def clear_all():
    """Clear internal references to existing deposits."""
    Deposit.tag_clear()

def timestamp():
    """Time stamp with raw precision of a second."""
    return datetime.now().strftime('%Y%m%d%H%M%S')

def logname():
    """Technical wrapper to overcome some strange results of the native os.getlogin function."""
    return pwd.getpwuid(os.getuid())[0]

class Request(object):
    """
    The basic meta structure of any `ask` to Jeeves.
    """

    def __init__(self, todo='show', user=None, task=None, date=None,
                 opts=None, data=None, jtag=None,
                 mail=tuple(), conf=tuple(), apps=tuple(), info='Nope'):
        self.todo = todo
        self.user = user or logname()
        self.task = task or os.environ.get('JOBNAME') or os.environ.get('SMSNAME')
        self.date = date or timestamp()
        self.opts = dict() if opts is None else dict(opts)
        self.data = data
        self.jtag = jtag
        self.mail = footprints.util.mktuple(mail)
        self.conf = conf
        self.apps = apps
        self.info = str(info)
        self._dumpfiles = list()

    def filename(self, radical='depot/config'):
        """Build a standard json file name for ask requests."""
        subpath, radical = os.path.split(os.path.normpath(self.jtag or radical))
        while '..' in radical:
            radical = radical.replace('..', '.')
        while radical.endswith('.json'):
            radical = radical[:-5]
        while radical.startswith('ask.'):
            radical = radical[4:]
        return os.path.join(
            subpath,
            '.'.join((
                'ask',
                datetime.now().strftime('%Y%m%d%H%M%S.%f'),
                'P{0:06d}'.format(os.getpid()),
                logname(),
                radical,
                'json'
            ))
        )

    def as_dict(self):
        """Return a plain dictionnay of arguments."""
        return { k : v for k, v in self.__dict__.items() if not k.startswith('_') }

    @property
    def last(self):
        return self._dumpfiles[-1] if self._dumpfiles else None

    @property
    def dumpfiles(self):
        return self._dumpfiles[:]

    def dump(self):
        """Dump request as a json file."""
        self._dumpfiles.append(self.filename())
        with io.open(self._dumpfiles[-1] + '.tmp', 'wb') as fd:
            json.dump(self.as_dict(), fd, sort_keys=True, indent=4)
        shutil.move(self._dumpfiles[-1] + '.tmp', self._dumpfiles[-1])
        return True

    def show(self, *args):
        """Display specified attributes values or all of them."""
        if not args:
            args = self.__dict__.keys() + ['last']
        for attr in sorted([ x for x in args if not x.startswith('_')]):
            print ' *', attr, '=', getattr(self, attr)


class Deposit(footprints.util.GetByTag):
    """Something simple to handle a directory used by Jeeves to process requests."""

    _tag_default = 'foo'

    def __init__(self, logger=None, path=None, active=False, target=None, cleaning=True, maxitems=128, maxtime='24H'):
        self._logger   = logger
        self._cleaning = cleaning
        self._target   = target
        self._path     = self.tag if path is None else path
        self.active    = active
        self.maxtime   = maxtime
        self.maxitems  = maxitems

    @property
    def logger(self):
        return self._logger

    @property
    def cleaning(self):
        return self._cleaning

    def _get_path(self):
        return self._path

    def _set_path(self, value):
        if os.path.isdir(str(value)):
            self._path = str(value)
        else:
            self.logger.critical('Invalid path setting', pool=self.tag, path=value)
            raise ValueError('Invalid pool path setting')

    path = property(_get_path, _set_path)

    def _get_active(self):
        return self._active

    def _set_active(self, value):
        self._active = bool(value)

    active = property(_get_active, _set_active)

    def _get_target(self):
        return self._target

    def _set_target(self, value):
        if value is not None:
            if value in self.tag_keys():
                self._target = value
            else:
                self.logger.critical('Invalid target tag', pool=self.tag, target=value)
                raise ValueError('Invalid pool target setting')

    target = property(_get_target, _set_target)

    def _get_maxitems(self):
        return self._maxitems

    def _set_maxitems(self, value):
        self._maxitems = int(value)

    maxitems = property(_get_maxitems, _set_maxitems)

    def _get_maxtime(self):
        return self._maxtime

    def _set_maxtime(self, value):
        try:
            value = int(value)
        except ValueError:
            value = str(value).lower().rstrip('h')
            if value.endswith('d'):
                value = value.rstrip('d')
                value = int(value) * 24
            else:
                value = int(value)
        self._maxtime = value

    maxtime = property(_get_maxtime, _set_maxtime)

    @property
    def contents(self):
        return sorted([ os.path.basename(x) for x in glob(self.path + '/ask.*.json') ])

    def clean(self):
        """Try to clean up the current pool."""
        items = self.contents
        psize = len(items)
        if 0 < self.maxitems < psize:
            justnow = datetime.now()
            oldfiles = list()
            for askfile in items:
                try:
                    askdate = datetime.strptime(askfile.split('.')[1], '%Y%m%d%H%M%S')
                except ValueError:
                    self.logger.error('Bad request format', item=askfile)
                    os.remove(os.path.join(self.path, askfile))
                else:
                    if (justnow - askdate).seconds / 3600 > self.maxtime:
                        oldfiles.append(askfile)
            if oldfiles:
                zipname = os.path.join(
                    self.path,
                    '.'.join((
                        'old', self.tag,
                        oldfiles[0].split('.')[1] + '-' + oldfiles[-1].split('.')[1],
                        'zip'
                    ))
                )
                self.logger.info('Zip', path=zipname, old=self.maxtime, size=len(oldfiles))
                with zipfile.ZipFile(zipname, 'w') as pzip:
                    for xfile in oldfiles:
                        actualfile = os.path.join(self.path, xfile)
                        pzip.write(actualfile, xfile)
                        os.remove(actualfile)

    def migrate(self, item, target=None):
        """Migrate the request to the chained pool."""
        rc = None
        if target is None:
            target = self.target
        if item is not None and target is not None and target != self.tag:
            target = Deposit(tag=target)
            os.rename(os.path.join(self.path, item), os.path.join(target.path, item))
            rc = target.tag
        return rc
