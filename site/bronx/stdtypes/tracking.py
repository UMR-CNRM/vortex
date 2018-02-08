#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
Tool to handle changes in some context.

Changes could be creation, deletion, modification.

TODO: More documentation + example
TODO: unittest
TODO: Properties' documentation
"""


class Tracker(object):
    """Handling of simple state status through ``deleted``, ``created`` or ``updated`` items."""

    def __init__(self, before=None, after=None, deleted=None, created=None, updated=None, unchanged=None):
        if before is not None and after is not None:
            before = frozenset(before)
            after  = frozenset(after)
            self._deleted = before - after
            self._created = after - before
            self._unchanged = before & after
        else:
            self._unchanged = frozenset()
            self._set_deleted(deleted)
            self._set_created(created)
            self._set_unchanged(unchanged)
        self._updated = frozenset()
        self._set_updated(updated)

    def __str__(self):
        return '{0:s} | deleted={1:d} created={2:d} updated={3:d} unchanged={4:d}>'.format(
            repr(self).rstrip('>'),
            len(self.deleted), len(self.created), len(self.updated), len(self.unchanged)
        )

    def _get_deleted(self):
        return self._deleted

    def _set_deleted(self, value):
        if value is not None:
            try:
                self._deleted = frozenset(value)
                self._unchanged = self._unchanged - self._deleted
            except TypeError:
                self._deleted = frozenset()

    deleted = property(_get_deleted, _set_deleted, None, None)

    def _get_created(self):
        return self._created

    def _set_created(self, value):
        if value is not None:
            try:
                self._created = frozenset(value)
                self._unchanged = self._unchanged - self._created
            except TypeError:
                self._created = frozenset()

    created = property(_get_created, _set_created, None, None)

    def _get_updated(self):
        return self._updated

    def _set_updated(self, value):
        if value is not None:
            try:
                self._updated = frozenset(value)
                self._unchanged = self._unchanged - self._updated
            except TypeError:
                self._updated = frozenset()

    updated = property(_get_updated, _set_updated, None, None)

    def _get_unchanged(self):
        return self._unchanged

    def _set_unchanged(self, value):
        if value is not None:
            try:
                self._unchanged = frozenset(value)
                self._updated = self._updated - self._unchanged
            except TypeError:
                self._unchanged = frozenset()

    unchanged = property(_get_unchanged, _set_unchanged, None, None)

    def __contains__(self, item):
        return item in self.deleted or item in self.created or item in self.updated or item in self.unchanged

    def __iter__(self):
        for item in self.deleted | self.created | self.updated | self.unchanged:
            yield item

    def __len__(self):
        return len(self.deleted | self.created | self.updated)

    def dump(self, *args):
        """Produce a simple dump report."""
        if not args:
            args = ('deleted', 'created', 'updated', 'unchanged')
        for section in args:
            print 'Section {0:s}: {1:s}'.format(section, str(getattr(self, section)))

    def differences(self):
        """Dump only created, deleted and updated items."""
        return self.dump('deleted', 'created', 'updated')
