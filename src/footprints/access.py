"""
Footprint descriptors for attributes access.
"""

import weakref

from bronx.fancies import loggers

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


# noinspection PyProtectedMember
class FootprintAttrDescriptor:
    """Abstract accessor class to footprint attributes."""
    access_mode = None

    def __init__(self, attr, doc='Undocumented footprint attribute', auth=None):
        self._attr = attr
        self._auth = auth
        self.__doc__ = doc

    def __get__(self, instance, owner):
        return instance.footprint_getattr(self._attr, auth=self._auth)


class FootprintAttrDescriptorRWD(FootprintAttrDescriptor):
    """Read-write-del accessor class to footprint attributes."""
    access_mode = 'rwd'

    def __set__(self, instance, value, weak=False):
        fp = instance.footprint
        if self._attr is not None:
            fpdef = fp.attr[self._attr]
            atype = fpdef.get('type', str)
            if fpdef.get('isclass', False):
                if not issubclass(value, atype):
                    raise ValueError('Attempt to set {:s} as a non compatible subclass {!s}'
                                     .format(self._attr, value))
            elif not isinstance(value, atype) and value is not None:
                logger.debug(' > Attr %s reclass(%s) as %s', self._attr, value, atype)
                initargs = fpdef.get('args', dict())
                try:
                    value = atype(value, **initargs)
                    logger.debug(' > Attr %s reclassed = %s', self._attr, value)
                except (ValueError, TypeError):
                    raise ValueError('Unable to reclass {!s} as {!s}'
                                     .format(value, atype))
            if fpdef['values'] and not fp.in_values(value, fpdef['values']):
                raise ValueError('Value {!s} not in range {!s}'
                                 .format(value, list(fpdef['values'])))
            if fpdef['outcast'] and fp.in_values(value, fpdef['outcast']):
                raise ValueError('Value {!s} excluded from range {!s}'
                                 .format(value, list(fpdef['outcast'])))
            if weak:
                value = weakref.proxy(value)
            instance.footprint_setattr(self._attr, value, auth=self._auth)

    def __delete__(self, instance):
        instance.footprint_delattr(self._attr, auth=self._auth)
        del self._attr


class FootprintAttrDescriptorWeakRWD(FootprintAttrDescriptorRWD):
    """Read-write accessor class to footprint attributes through a weak proxy."""
    access_mode = 'rwd-weak'

    def __set__(self, instance, value):
        super().__set__(instance, value, weak=True)


class FootprintAttrDescriptorRWX(FootprintAttrDescriptorRWD):
    """Read-write accessor class to footprint attributes."""
    access_mode = 'rwx'

    def __delete__(self, instance):
        raise AttributeError('Read-only attribute [' + self._attr + '] (delete)')


class FootprintAttrDescriptorWeakRWX(FootprintAttrDescriptorRWX):
    """Read-write accessor class to footprint attributes through a weak proxy."""
    access_mode = 'rwx-weak'

    def __set__(self, instance, value):
        super().__set__(instance, value, weak=True)


class FootprintAttrDescriptorRXX(FootprintAttrDescriptor):
    """Read-only accessor class to footprint attributes."""
    access_mode = 'rxx'

    def __set__(self, instance, value):
        raise AttributeError('Read-only attribute [' + self._attr + '] (write)')

    def __delete__(self, instance):
        raise AttributeError('Read-only attribute [' + self._attr + '] (delete)')


class FootprintAttrDescriptorWeakRXX(FootprintAttrDescriptorRXX):
    """Read-only accessor class to footprint attributes through a weak proxy."""
    access_mode = 'rxx-weak'


def attr_descriptors(refresh=False, _cache=dict()):
    """Return a dictionary of active descriptors accessible by their ``access_mode``."""
    if refresh or not _cache:
        _cache.clear()
        _cache.update({
            xobj.access_mode: xobj for xobj in globals().values()
            if hasattr(xobj, 'access_mode') and xobj.access_mode is not None
        })
    return _cache
