"""
Module that deals with part of the Arpege/IFS listings related to the variational
data assimilation's cost functions.
"""

from io import StringIO

import re
from collections import OrderedDict, namedtuple


from bronx.fancies.display import print_tablelike
from .util import read_listing

#: Automatic export
__all__ = ['CostFunctions', ]


class CostFunctionsMismatchError(Exception):
    """Items from Experiment and Reference CostFunctions do not match."""
    pass


class CostFunctionKey(namedtuple('BareCostFunctionKey', ('iter', 'sim'))):
    """A unique key that identifies cost function information.

    :param int iter: The iteration number
    :param int sim: The simulation number
    """
    def __new__(cls, *kargs, **kwargs):
        kargs = [int(n) for n in kargs]
        kwargs = {k: int(n) for k, n in kwargs.items()}
        return super().__new__(cls, *kargs, **kwargs)


class CostFunctionData:
    """A bunch of information about the cost function (at a given step)."""

    def __init__(self):
        """
        No conructor's arguments needed. Use the :meth:`init_cost` and
        :meth:`init_grad` methods to initialise the object.
        """
        self._j = None
        self._jo = None
        self._jb = None
        self._jc = None
        self._jq = None
        self._jp = None
        self._gradj = None

    def init_cost(self, **kwargs):
        """Set data about the cost function's components.

        :param dict kwargs: A dictionary that holds informations about Jo, Jb,
            Jc, Jq and Jp
        """
        self._jo = float(kwargs.get('Jo', None))
        self._jb = float(kwargs.get('Jb', None))
        self._jc = float(kwargs.get('Jc', None))
        self._jq = float(kwargs.get('Jq', None))
        self._jp = float(kwargs.get('Jp', None))

    def init_grad(self, **kwargs):
        """Set data about the cost function and its gradient.

        :param dict kwargs: A dictionary that holds informations about J and gradJ
        """
        self._j = float(kwargs.get('J', None))
        self._gradj = float(kwargs.get('gradJ', None))

    @property
    def j(self):
        """The cost function value (usually referred as J)."""
        return self._j

    @property
    def jo(self):
        """The observations term of the cost function (usually referred as Jo)."""
        return self._jo

    @property
    def jb(self):
        """The background term of the cost function (usually referred as Jo)."""
        return self._jb

    @property
    def jc(self):
        """The fast oscillations filtering term of the cost function (usually referred as Jc)."""
        return self._jc

    @property
    def jq(self):
        """The relaxation term of the cost function (usually referred as Jq, LAM systems only)."""
        return self._jq

    @property
    def jp(self):
        """The VarBC term of the cost function (usually referred as Jp)."""
        return self._jp

    @property
    def gradj(self):
        """The cost function gradient norm."""
        return self._gradj


class CostFunctions:
    """Object enclosing one or more cost function data.

    It behaves mostly like a dictionary:

        * keys are of type :class:`CostFunctionKey`
        * values are of type :class:`CostFunctionData`

    For example, to access the cost function data at the end of a minimisation::

        cf = CostFunctions('path_to_the_listing')
        print(cf[(999, 999)].jo)

    This class also provide a nice __str__ method. Check out the result of::

        print(cf)

    """

    # GREPCOST - ITER,SIM,JO,JB,JC,JQ,JP    1   1   1608090.76067       41397.7651306
    # 42.5912100509       0.00000000000       468.896418521
    _re_cost = re.compile(r'\s+GREPCOST\s+-\s+ITER,SIM,JO,JB,JC,JQ,JP\s+' +
                          r'(?P<iter>\d+)\s+' +
                          r'(?P<sim>\d+)\s+' +
                          r'(?P<Jo>[\.\+\-Ee\d]+)\s+' +
                          r'(?P<Jb>[\.\+\-Ee\d]+)\s+' +
                          r'(?P<Jc>[\.\+\-Ee\d]+)\s+' +
                          r'(?P<Jq>[\.\+\-Ee\d]+)\s+' +
                          r'(?P<Jp>[\.\+\-Ee\d]+)')
    # GREPGRAD - LSIMPLE,ITER,SIM,GRAD,J      0   0 0.4786631893713723E+04 0.1644649969450126E+07
    _re_grad = re.compile(r'\s+GREPGRAD\s+-\s+LSIMPLE,ITER,SIM,GRAD,J\s+' +
                          r'(?P<iter>\d+)\s+' +
                          r'(?P<sim>\d+)\s+' +
                          r'(?P<gradJ>[\.\+\-Ee\d]+)\s+' +
                          r'(?P<J>[\.\+\-Ee\d]+)')

    def __init__(self, filename, fcontent=None):
        """The constructor call triggers the reading of the file.

        :param filename: Name of the file where the cost function data are read
        :param fcontent: Array of listing lines (if not provided, **filename** is
            opened and read it.
        """
        self.filename = filename
        self._content = OrderedDict()

        if fcontent is None:
            lines = read_listing(self.filename)
        else:
            lines = fcontent

        for line in lines:
            self._parse_line(line)

    def _get_kv(self, matchobj):
        k = CostFunctionKey(matchobj.group('iter'), matchobj.group('sim'))
        if k in self:
            v = self[k]
        else:
            v = CostFunctionData()
        return k, v

    def _parse_line(self, line):
        # print(line)
        cmatch = self._re_cost.match(line)
        if cmatch:
            k, v = self._get_kv(cmatch)
            v.init_cost(** cmatch.groupdict())
            self._content[k] = v
        gmatch = self._re_grad.match(line)
        if gmatch:
            k, v = self._get_kv(gmatch)
            v.init_grad(** gmatch.groupdict())
            self._content[k] = v

    def __len__(self):
        return len(self._content)

    def __getitem__(self, item):
        if isinstance(item, (tuple, list)):
            item = CostFunctionKey(* item)
        return self._content[item]

    def __contains__(self, item):
        if isinstance(item, (tuple, list)):
            item = CostFunctionKey(* item)
        return item in self._content

    def __iter__(self):
        return iter(self._content)

    def keys(self):
        """Return the list of keys of all elements contained in this object."""
        return self._content.keys()

    def values(self):
        """Return the list of elements contained in this object."""
        return self._content.values()

    def items(self):
        """Return the list of elements contained in this object."""
        return self._content.items()

    def __str__(self):
        ret = 'Cost function informations read from file: %s\n' % self.filename
        ret += '\nIter  Sim\n'
        sio = StringIO()
        print_tablelike('{:4d} {:4d} J={:s} Jo={:s} Jb={:s} Jc={:s} Jq={:s} Jp={:s} gradJ={:s}\n',
                        * zip(* [[k.iter, k.sim,
                                  str(v.j), str(v.jo), str(v.jb), str(v.jc), str(v.jq), str(v.jp), str(v.gradj)]
                                 for k, v in self.items()]),
                        output_callback=sio.write)
        sio.seek(0)
        return ret + sio.read()

    def __eq__(self, other):
        assert isinstance(other, self.__class__)
        return (set(self.keys()) == set(other.keys()) and
                all([self[k] == other[k] for k in self.keys()]))
