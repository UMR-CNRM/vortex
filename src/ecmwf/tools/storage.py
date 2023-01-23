"""
This package is used to implement the Archive Store class only used at ECMWF.
"""

from vortex.tools.storage import Archive
from vortex.tools.systems import ExecutionError


class EctransArchive(Archive):
    """The specific class to handle Archive from ECMWF super-computers"""

    _footprint = dict(
        info = 'Default archive description from ECMWF',
        attr = dict(
            tube = dict(
                values   = ['ectrans'],
            )
        )
    )

    @staticmethod
    def _ectransfullpath(item, **kwargs):
        """Actual _fullpath using ectrans"""
        return item, dict()

    def _ectransprestageinfo(self, item, **kwargs):
        """Actual _prestageinfo using ectrans"""
        raise NotImplementedError

    def _ectranscheck(self, item, **kwargs):
        """Actual _check using ectrans"""
        raise NotImplementedError

    def _ectranslist(self, item, **kwargs):
        """Actual _list using ectrans"""
        raise NotImplementedError

    def _ectransretrieve(self, item, local, **kwargs):
        """Actual _retrieve using ectrans"""
        remote = self.sh.ectrans_remote_init(remote=kwargs.get("remote", None),
                                             inifile=self.inifile,
                                             storage=self.storage)
        gateway = self.sh.ectrans_gateway_init(gateway=kwargs.get("gateway", None),
                                               inifile=self.inifile)
        extras = dict(fmt=kwargs.get('fmt', 'foo'),
                      cpipeline=kwargs.get("compressionpipeline", None))
        return self.sh.ectransget(source=item,
                                  target=local,
                                  gateway=gateway,
                                  remote=remote,
                                  ** extras), extras

    def _ectransinsert(self, item, local, **kwargs):
        """Actual _insert using ectrans"""
        remote = self.sh.ectrans_remote_init(remote=kwargs.get("remote", None),
                                             inifile=self.inifile,
                                             storage=self.storage)
        gateway = self.sh.ectrans_gateway_init(gateway=kwargs.get("gateway", None),
                                               inifile=self.inifile)
        extras = dict(fmt=kwargs.get('fmt', 'foo'),
                      cpipeline=kwargs.get('compressionpipeline', None))
        return self.sh.ectransput(source=local,
                                  target=item,
                                  gateway=gateway,
                                  remote=remote,
                                  sync=kwargs.get('enforcesync', False),
                                  ** extras), extras

    def _ectransdelete(self, item, **kwargs):
        """Actual _delete using ectrans"""
        raise NotImplementedError


class EcfsArchive(Archive):
    """The specific class to handle Archive from ECMWF super-computers"""

    _footprint = dict(
        info='Default archive description from ECMWF',
        attr=dict(
            storage=dict(
                values = ['ecgate.ecmwf.int', 'ecfs.ecmwf.int'],
            ),
            tube=dict(
                values=['ecfs'],
            ),
        )
    )

    def _ecfsfullpath(self, item, **kwargs):
        """Actual _fullpath using ecfs"""
        actual_fullpath = {
            'ecgate.ecmwf.int': "ec:{item!s}",
            'ecfs.ecmwf.int': "ec:{item!s}"
        }.get(self.storage, None)
        if actual_fullpath is None:
            raise NotImplementedError
        for char, repl in (('@', 'atsymbol'),
                           (':', 'semicol'),
                           ('%', 'percent'),
                           (' ', 'space')):
            item = item.replace(char, '__{:s}__'.format(repl))
        return actual_fullpath.format(item=item), dict()

    def _ecfsprestageinfo(self, item, **kwargs):
        """Actual _prestageinfo using ecfs"""
        raise NotImplementedError

    def _ecfscheck(self, item, **kwargs):
        """Actual _check using ecfs"""
        item = self._ecfsfullpath(item)[0]
        options = kwargs.get("options", None)
        return self.sh.ecfstest(item,
                                options=options), dict()

    def _ecfslist(self, item, **kwargs):
        """Actual _list using ecfs"""
        item = self._ecfsfullpath(item)[0]
        options = kwargs.get("options", None)
        try:
            return self.sh.ecfsls(item,
                                  options=options), dict()
        except ExecutionError:
            return None, dict()

    def _ecfsretrieve(self, item, local, **kwargs):
        """Actual _retrieve using ecfs"""
        item = self._ecfsfullpath(item)[0]
        options = kwargs.get("options", None)
        extras = dict(fmt=kwargs.get('fmt', 'foo'),
                      cpipeline=kwargs.get('compressionpipeline', None))
        return self.sh.ecfsget(source=item,
                               target=local,
                               options=options,
                               ** extras), extras

    def _ecfsinsert(self, item, local, **kwargs):
        """Actual _insert using ecfs"""
        item = self._ecfsfullpath(item)[0]
        options = kwargs.get("options", None)
        extras = dict(fmt=kwargs.get('fmt', 'foo'),
                      cpipeline=kwargs.get('compressionpipeline', None))
        rc = self.sh.ecfsmkdir(target=self.sh.path.dirname(item))
        rc = rc and self.sh.ecfsput(source=local,
                                    target=item,
                                    options=options,
                                    ** extras)
        rc = rc and self.sh.ecfschmod('644', item)
        return rc, extras

    def _ecfsdelete(self, item, **kwargs):
        """Actual _delete using ecfs"""
        item = self._ecfsfullpath(item)[0]
        options = kwargs.get("options", None)
        fmt = kwargs.get("fmt", "foo")
        return self.sh.ecfsrm(item,
                              options=options,
                              fmt=fmt), dict(fmt=fmt)
