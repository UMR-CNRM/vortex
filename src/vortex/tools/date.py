#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
Date interface.

Formats hypothesis:

1. the arguments representing a date must follow the following convention
   yyyymmdd[hh[mn[ss]]] with yyyy as the year in 4 numbers, mm as the month
   in 2 numbers, dd as the day in 2 numbers, hh as the hours (0-24), mn as the
   minutes and ss as the seconds.

2. so as to add or substract a duration to a date expressed in the preceding
   format (yyyymmdd[hh[mn[ss]]]) the arguments must follow:

      * P starts an ISO 8601 Period definition
      * nY, the number of years (n positive integer),
      * nM, the number of months (n positive integer),
      * nD, the number of days (n positive integer),
      * T as a time separator,
      * nH, the number of hours (n positive integer),
      * nM, the number of minutes (n positive integer),
      * nS, the number of seconds (n positive integer)

   Example::

      P1Y <=> is a 1 year period
      P20D <=> is a 20 days period
      PT15H10M55S <=> is a 15 hours, 10 minutes and 55 seconds period

The available methods in the Date class are:

   * create a date in regard to the desired format (yyyymmddhhmnss,...,yyyy)
   * convert from usual date to julian date
   * deliver the minutes of a date if available
   * add/substract a duration to a date (y, m, d, h, mn, s)
   * deliver the number of days of a month
   * determine if a year is a leap year
   * deliver the time gap between two dates and the result is expressed
     in hours, minutes and seconds.

"""

__all__ = []

import re
import datetime
import calendar


def mkisodate(datestr):
    """A crude attempt to reshape the iso8601 format."""
    l = list(datestr)
    if len(l) > 4 and l[4] != '-':
        l[4:4] = [ '-' ]
    if len(l) > 7 and l[7] != '-':
        l[7:7] = [ '-' ]
    if len(l) > 10 and l[10] != 'T':
        l[10:10] = [ 'T' ]
    if 10 < len(l) <= 13:
        l.extend(['0', '0'])
    if len(l) > 13 and l[13] != ':':
        l[13:13] = [ ':' ]
    if len(l) > 16 and l[16] != ':':
        l[16:16] = [ ':' ]
    if len(l) > 13 and l[-1] != 'Z':
        l.append('Z')
    return ''.join(l)


def today():
    """Return date of the day, at 0 hour, 0 minute."""
    td = datetime.datetime.today()
    return Date(td.year, td.month, td.day, 0, 0)


def yesterday(base=None):
    """Return date of yesterday (relative to today or specified ``base`` date)."""
    if not base:
        base = today()
    return base - Period(days=1)


def tomorrow(base=None):
    """Return date of tomorrow (relative to today or specified ``base`` date)."""
    if not base:
        base = today()
    return base + Period(days=1)


def now():
    """Return date just now, with hours, minutes, seconds and microseconds."""
    td = datetime.datetime.now()
    return Date(td.year, td.month, td.day, td.hour, td.minute, td.second, td.microsecond)


def at_second():
    """Return date just now, with only hours, minutes and seconds."""
    td = datetime.datetime.now()
    return Date(td.year, td.month, td.day, td.hour, td.minute, td.second, 0)


def at_hour():
    """Return date just now, with only hours."""
    td = datetime.datetime.now()
    return Date(td.year, td.month, td.day, td.hour, 0, 0, 0)


def lastround(rh=1, delta=0, base=None):
    """Return date just before ``base`` with a plain hour multiple of ``rh``."""
    if not base:
        base = now()
    if delta:
        base += Period(delta)
    return Date(base.year, base.month, base.day, base.hour - base.hour % rh, 0)


def synop(delta=0, base=None, time=None, step=6):
    """Return date associated to the last synoptic hour."""
    synopdate = lastround(step, delta, base)
    if time is not None:
        time = Time(time)
        if time in [ Time(x) for x in range(0, 24, step) ]:
            dt = Period('PT' + str(step) + 'H')
            while synopdate.time() != time:
                synopdate = synopdate - dt
        else:
            raise ValueError('Not a synoptic hour: ' + str(time))
    return synopdate

def stamp():
    """Return date up to microseconds as a tuple."""
    td = datetime.datetime.now()
    return (td.year, td.month, td.day, td.hour, td.minute, td.second, td.microsecond)

def easter(year=None):
    """Return date for easter of the given year
    >>> dates = [2013, 2014, 2015, 2016, 2017, 2018]
    >>> [easter(d).ymd for d in dates]
    ['20130331', '20140420', '20150405', '20160327', '20170416', '20180401']
    """
    if not year:
        year = today().year
    G = year % 19
    C = year / 100
    H = (C - C / 4 - (8 * C + 13) / 25 + 19 * G + 15) % 30
    I = H - (H / 28) * (1 - (29 / (H + 1)) * ((21 - G) / 11))
    J = (year + year / 4 + I + 2 - C + C / 4) % 7
    L = I - J
    month = 3 + (L + 40) / 44
    day = L + 28 - 31 * (month / 4)
    return Date(year, month, day)

local_date_functions = dict([
    (x.__name__, x)
        for x in locals().values()
            if hasattr(x, 'func_name') and x.__doc__.startswith('Return date')
])

del x

def stardates():
    """Nice dump of predefined dates functions."""
    for k, v in sorted(local_date_functions.items()):
        print k.ljust(12), v()


def guess(*args):
    """Do our best to find a :class:`Date` or :class:`Period` object compatible with ``args``."""
    for isoclass in (Date, Period):
        try:
            return isoclass(*args)
        except (ValueError, TypeError):
            continue
    else:
        raise ValueError, "Cannot guess what Period or Date could be %s" % str(args)


def daterange(start, end=None, step='P1D'):
    """Date generator."""

    if not isinstance(start, Date):
        start = Date(start)

    if end is None:
        end = start + Period('P10D')
    else:
        if not isinstance(end, Date):
            end = Date(end)

    if not isinstance(step, Period):
        step = Period(step)

    rollingdate = start
    while rollingdate <= end:
        yield rollingdate
        rollingdate += step


class Period(datetime.timedelta):
    """Standard period objects, extending :class:`datetime.timedelta` features with iso8601 facilities."""

    _my_re  = re.compile(
        r'(?P<X>[+-]?P)(?P<Y>[0-9]+([,.][0-9]+)?Y)?'
        r'(?P<M>[0-9]+([,.][0-9]+)?M)?'
        r'(?P<W>[0-9]+([,.][0-9]+)?W)?'
        r'(?P<D>[0-9]+([,.][0-9]+)?D)?'
        r'((?P<T>T)(?P<h>[0-9]+([,.][0-9]+)?H)?'
        r'(?P<m>[0-9]+([,.][0-9]+)?M)?'
        r'(?P<s>[0-9]+([,.][0-9]+)?S)?)?$'
    )

    @staticmethod
    def period_regex(s):
        return Period._my_re.match(s)

    _const_times = [
        # in a [0], there are [1] [2]
        ('m',  60, 's'),
        ('h',  60, 'm'),
        ('D',  24, 'h'),
        ('W',   7, 'D'),
        ('M',  31, 'D'),
        ('Y', 365, 'D'),
    ]

    @staticmethod
    def _adder(key, value):
        if key == 's':
            return value
        else:
            for key1, factor, key2 in Period._const_times:
                if key == key1:
                    return Period._adder(key2, factor * value)
            else:
                raise KeyError, "Unknown key in Period string: %s" % key

    @staticmethod
    def parse(string):
        """Find out time duration that could be extracted from string argument."""
        if not isinstance(string, basestring):
            raise TypeError, "Expected string input"
        if len(string) < 2:
            raise ValueError, "Badly formed short string %s" % string

        match = Period.period_regex(string)
        if not match:
            raise ValueError, "Badly formed string %s" % string

        values = match.groupdict()
        values.pop('T')
        sign = values.pop('X')
        if sign.startswith('-'):
            sign = -1
        else:
            sign = 1

        for k, v in values.iteritems():
            if not v:
                values[k] = 0
            else:
                values[k] = int(v[:-1])

        secs = 0
        for k, v in values.iteritems():
            secs += Period._adder(k, v)

        return sign * secs

    def __new__(cls, *args, **kw):
        """
        Initial values include:
            * a datetime object;
            * a tuple containing at least (year, month, day) values;
            * a dictionary with this named values ;
            * a string that could be reshaped as an ISO 8601 date string.
        """
        if kw:
            args = (datetime.timedelta(**kw),)
        if not args:
            raise ValueError("No initial value provided for Period")
        top = args[0]
        ld = list()
        if isinstance(top, datetime.timedelta):
            ld = [ top.days, top.seconds, top.microseconds ]
        elif isinstance(top, Time):
            ld = [ 0, top.hour * 3600 + top.minute * 60 ]
        elif len(args) < 2 and ( isinstance(top, int) or isinstance(top, float) ):
            ld = [ 0, top ]
        elif isinstance(top, int) and len(args) == 2:
            ld = list(args)
        elif isinstance(top, str):
            ld = [ 0, Period.parse(top) ]
        if not ld:
            raise ValueError("Initial Period value unknown")
        return datetime.timedelta.__new__(cls, *ld)

    def __deepcopy__(self, memo):
        """No deepcopy expected, so ``self`` is returned."""
        return self

    def __len__(self):
        return self.days * 86400 + self.seconds

    def __add__(self, delta):
        """
        Add to a Period object the specified ``delta`` which could be either
        a string or a :class:`datetime.timedelta` or an ISO 6801 Period.
        """
        if not isinstance(delta, datetime.timedelta):
            delta = Period(delta)
        return Period(super(Period, self).__add__(datetime.timedelta(delta.days, delta.seconds)))

    def __sub__(self, delta):
        """
        Substract to a Period object the specified ``delta`` which could be either
        a string or a :class:`datetime.timedelta` or an ISO 6801 Period.
        """
        if not isinstance(delta, datetime.timedelta):
            delta = Period(delta)
        return Period(super(Period, self).__sub__(datetime.timedelta(delta.days, delta.seconds)))

    def __mul__(self, factor):
        """
        Add to a Period object the specified ``delta`` which could be either
        a string or a :class:`datetime.timedelta` or an ISO 6801 Period.
        """
        if not isinstance(factor, int):
            factor = int(factor)
        return Period(super(Period, self).__mul__(factor))

    def iso8601(self):
        """Plain ISO 8601 representation."""
        iso = 'P'
        sign, days, seconds = '', self.days, self.seconds
        if days < 0:
            sign = '-'
            days += 1
            seconds = 86400 - seconds
        if days:
            iso += str(abs(days)) + 'D'
        return sign + iso + 'T' + str(seconds) + 'S'

    def isoformat(self):
        """Return default ISO representation."""
        return self.iso8601()

    @property
    def length(self):
        """Absolute length in seconds."""
        return abs(int(self.total_seconds()))

    def time(self):
        """Return a :class:`Time` object."""
        return Time(0, self.length / 60) + 0


class Date(datetime.datetime):
    """Standard date objects, extending :class:`datetime.datetime` features with iso8601 facilities."""

    _origin = datetime.datetime(1970, 1, 1, 0, 0, 0)

    def __new__(cls, *args, **kw):
        """
        Initial values include:
            * a datetime object;
            * a tuple containing at least (year, month, day) values;
            * a dictionary with this named values ;
            * a string that could be reshaped as an ISO 8601 date string.
        """
        if kw and not args:
            args = (datetime.datetime(**kw),)
        if not args:
            raise ValueError("No initial value provided for Date")
        top = args[0]
        delta = ''
        ld = list()
        if isinstance(top, str) and top in local_date_functions:
            try:
                top = local_date_functions[top](**kw)
                kw = dict()
            except StandardError:
                pass
        if isinstance(top, datetime.datetime):
            ld = [ top.year, top.month, top.day, top.hour, top.minute, top.second ]
        elif isinstance(top, tuple) or isinstance(top, list):
            ld = list(top)
        elif isinstance(top, float):
            top = Date._origin + datetime.timedelta(0, top)
            ld = [ top.year, top.month, top.day, top.hour, top.minute, top.second ]
        elif isinstance(top, str):
            (top, u_sep, delta) = top.partition('/')
            ld = [ int(x) for x in re.split('[-:HTZ]+', mkisodate(top)) if re.match(r'\d+$', x) ]
        else:
            ld = [ int(x) for x in args if type(x) in (int, float) or (isinstance(x, str) and
                                                                       re.match(r'\d+$', x)) ]
        if not ld:
            raise ValueError("Initial Date value unknown")
        newdate = datetime.datetime.__new__(cls, *ld)
        if delta:
            newdate = newdate.__add__(delta)
        return newdate

    def __init__(self, *args, **kw):
        super(Date, self).__init__()
        delta_o = self - Date._origin
        self._epoch = delta_o.days * 86400 + delta_o.seconds

    def __reduce__(self):
        """Return a compatible args sequence for the Date constructor (used by :mod:`pickle`)."""
        return (self.__class__, (self.iso8601(),))

    def __deepcopy__(self, memo):
        """No deepcopy expected, so ``self`` is returned."""
        return self

    @property
    def origin(self):
        """Origin date... far far ago at the very beginning of the 70's."""
        return Date(Date._origin)

    @property
    def epoch(self):
        """Seconds since the beginning of epoch... the first of january, 1970."""
        return self._epoch

    def iso8601(self):
        """Plain ISO 8601 representation."""
        return self.isoformat() + 'Z'

    def __str__(self):
        """Default string representation is iso8601."""
        return self.iso8601()

    def as_dump(self):
        """Nicely formatted representation in dumper."""
        return self.__repr__()

    def is_synoptic(self):
        """True if the current hour is a synoptic one."""
        return self.hour in (0, 6, 12, 18)

    @property
    def julian(self):
        """Returns Julian day."""
        return self.strftime('%j')

    @property
    def ymd(self):
        return self.strftime('%Y%m%d')

    @property
    def ymdh(self):
        return self.strftime('%Y%m%d%H')

    @property
    def ymdhm(self):
        return self.strftime('%Y%m%d%H%M')

    @property
    def ymdhms(self):
        return self.strftime('%Y%m%d%H%M%S')

    @property
    def hm(self):
        return self.strftime('%H%M')

    @property
    def hh(self):
        return self.strftime('%H')

    def compact(self):
        """Compact concatenation of date values, up to the second."""
        return self.ymdhms

    def vortex(self, cutoff='P'):
        """Semi-compact representation for vortex paths."""
        return self.strftime('%Y%m%dT%H%M') + str(cutoff)[0].upper()

    def reallynice(self):
        """Nice and verbose string representation."""
        return self.strftime("%A %d. %B %Y, at %H:%M:%S")

    def export_dict(self):
        """String representation for dict or shell variable."""
        return self.ymdhm

    def __add__(self, delta):
        """
        Add to a Date object the specified ``delta`` which could be either
        a string or a :class:`datetime.timedelta` or an ISO 6801 Period.
        """
        if not isinstance(delta, datetime.timedelta):
            delta = Period(delta)
        return Date(super(Date, self).__add__(datetime.timedelta(delta.days, delta.seconds)))

    def __radd__(self, delta):
        """Commutative add."""
        return self.__add__(delta)

    def __sub__(self, delta):
        """
        Substract to a Date object the specified ``delta`` which could be either
        a string or a :class:`datetime.timedelta` or an ISO 6801 Period.
        """

        if not isinstance(delta, datetime.datetime) and not isinstance(delta, datetime.timedelta):
            delta = guess(delta)
        substract = super(Date, self).__sub__(delta)
        if isinstance(delta, datetime.datetime):
            return Period(substract)
        else:
            return Date(substract)

    def replace(self, **kw):
        """Possible arguments: year, month, day, hour, minute."""
        for datekey in ('year', 'month', 'day', 'hour', 'minute'):
            kw.setdefault(datekey, getattr(self, datekey))
        return Date(datetime.datetime(**kw))

    @property
    def cnes_origin(self):
        return datetime.datetime(1950, 1, 1).toordinal()

    def to_cnesjulian(self, date=None):
        """
        Convert current Date() object, or arbitrary date, to CNES julian calendar
        >>> d = Date('20111026')
        >>> d.to_cnesjulian()
        22578
        >>> d.to_cnesjulian(date=[2011, 10, 27])
        22579
        """
        if not date:
            date = datetime.datetime(self.year, self.month, self.day)
        if isinstance(date, list):
            date = datetime.datetime(*date)
        return date.toordinal() - self.cnes_origin

    def from_cnesjulian(self, jdays=None):
        """
        >>> d = Date('20111025')
        >>> d.from_cnesjulian()
        Date(2011, 10, 25, 0, 0)
        >>> d.from_cnesjulian(22578)
        Date(2011, 10, 26, 0, 0)
        """
        if jdays is None:
            jdays = self.toordinal() - self.cnes_origin
        return Date(self.fromordinal(jdays + self.cnes_origin))

    def isleap(self, year=None):
        """Return whether the current of specified year is a leap year."""
        if year is None:
            year = self.year
        return calendar.isleap(year)

    def monthrange(self, year=None, month=None):
        """Return the number of days in the current of specified year-month couple."""
        if year is None:
            year = self.year
        if month is None:
            month = self.month
        return calendar.monthrange(year, month)[1]

    def time(self):
        """Return a :class:`Time` object."""
        return Time(self.hour, self.minute)

    def bounds(self):
        """Return first and last day of the current month."""
        return (
            self.replace(day=1, hour=0, minute=0),
            self.replace(day=self.monthrange(), hour=23, minute=59)
        )

    @property
    def outbound(self):
        """Return the closest day out of this month."""
        a, b = self.bounds()
        if self - a > b - self:
            out = b + 'P1D'
        else:
            out = a - 'P1D'
        return out.ymd

    @property
    def midcross(self):
        """Return the closest day out of this month."""
        a, b = self.bounds()
        if self.day > 15:
            out = b + 'P1D'
        else:
            out = a - 'P1D'
        return out.ymd

class Time(object):
    """
    Basic object to handle hh:mm information.
    Extended arithmetic is supported.
    """

    def __init__(self, *args, **kw):
        """
        Initial values include:
            * a datetime.time object;
            * a tuple containing at least (hour, minute) values;
            * a dictionary with this named values ;
            * a string that could be reshaped as an ISO 8601 date string.
        """
        if kw:
            kw.setdefault('hour', 0)
            kw.setdefault('minute', 0)
            args = (datetime.time(**kw),)
        if not args:
            raise ValueError("No initial value provided for Time")
        top = args[0]
        ld = list()
        self._hour, self._minute = None, None
        if isinstance(top, tuple) or isinstance(top, list):
            zz = Time(*top)
            self._hour, self._minute = zz.hour, zz.minute
        elif isinstance(top, datetime.time) or isinstance(top, Time):
            self._hour, self._minute = top.hour, top.minute
        elif isinstance(top, float):
            self._hour, self._minute = int(top), int((top-int(top))*60)
        elif isinstance(top, str):
            ld = [ int(x) for x in re.split('[-:hHTZ]+', top) if re.match(r'\d+$', x) ]
        else:
            ld = [ int(x) for x in args
                   if type(x) in (int, float)
                   or (isinstance(x, str) and re.match(r'\d+$', x)) ]
        if ld:
            if len(ld) < 2:
                ld.append(0)
            self._hour, self._minute = ld[0], ld[1]
        if self._hour is None or self._minute is None:
            raise ValueError("No way to build a Time value")

    @property
    def hour(self):
        return self._hour

    @property
    def minute(self):
        return self._minute

    def __deepcopy__(self, memo):
        """Clone the current Time object."""
        return Time(self.hour, self.minute)

    def __repr__(self):
        """Standard hour-minute representation."""
        return 'Time({0:d}, {1:d})'.format(self.hour, self.minute)

    def as_dump(self):
        """Nicely formatted representation in dumper."""
        return self.__repr__()

    def export_dict(self):
        """String representation for dict or shell variable."""
        return self.__str__()

    def __str__(self):
        """Standard hour-minute string."""
        return '{0:02d}:{1:02d}'.format(self.hour, self.minute)

    def __int__(self):
        """Convert to `int`, ie: returns hours * 60 + minutes."""
        return self._hour * 60 + self._minute

    def __cmp__(self, other):
        """Compare two Time values or a Time and an int value."""
        try:
            other = self.__class__(other)
        except StandardError:
            pass
        finally:
            return cmp(str(self), str(other))

    def __add__(self, delta):
        """
        Add to a Date object the specified ``delta`` which could be either
        a string or a :class:`datetime.timedelta` or an ISO 6801 Period.
        """
        delta = Time(delta)
        hour, minute = self.hour + delta.hour, self.minute + delta.minute
        hour, minute = hour + int(minute/60), minute % 60
        return Time(hour, minute)

    def __radd__(self, delta):
        """Commutative add."""
        return self.__add__(delta)

    def __sub__(self, delta):
        """
        Add to a Date object the specified ``delta`` which could be either
        a string or a :class:`datetime.timedelta` or an ISO 6801 Period.
        """
        delta = Time(delta)
        hour, minute = self.hour - delta.hour, self.minute - delta.minute
        if minute < 0:
            minute += 60
            hour   -= 1
        return Time(hour, minute)

    @property
    def fmth(self):
        return '{0:04d}'.format(self.hour)

    @property
    def fmthour(self):
        return self.fmth

    @property
    def fmthm(self):
        return '{0:04d}:{1:02d}'.format(self.hour, self.minute)

    @property
    def fmthhmm(self):
        return '{0:02d}{1:02d}'.format(self.hour, self.minute)

    @property
    def fmtraw(self):
        return '{0:04d}{1:02d}'.format(self.hour, self.minute)

    def isoformat(self):
        """Almost ISO representation."""
        return str(self)

    def iso8601(self):
        """Plain ISO 8601 representation."""
        return 'T' + self.isoformat() + 'Z'

    def nice(self, t):
        """Return the specified value formatted as self should be."""
        return '{0:04d}'.format(t)


class Month(object):
    """Basic class for handling a month number, according to an explicit or implicit year."""

    def __init__(self, *args, **kw):
        delta = kw.pop('delta', 0)
        try:
            args = (datetime.datetime(**kw),)
        except StandardError:
            pass
        if not args:
            raise ValueError("No initial value provided for Month")
        args = list(args)
        top = args[0]
        self._month = None
        self._year = max(0, int(kw.pop('year', today().year)))
        if isinstance(top, datetime.datetime) or isinstance(top, Month):
            self._month, self._year = top.month, top.year
        elif isinstance(top, int) and 0 < top < 13:
            self._month = top
            if len(args) == 2:
                self._year = int(args[1])
        else:
            if isinstance(top, str):
                mmod = re.search(':(next|prev)$', top)
                if mmod:
                    args[0] = re.sub(':(?:next|prev)$', '', top)
                    if mmod.group(1) == 'next':
                        delta = 1
                    else:
                        delta = -1
            if len(args) == 2:
                delta = args.pop()
            try:
                tmpdate = Date(*args)
            except (ValueError, TypeError):
                raise ValueError('Could not create a Month from values provided %s', str(args))
            else:
                self._month, self._year = tmpdate.month, tmpdate.year
        if delta:
            mtmp = self + delta
            self._month, self._year = mtmp.month, mtmp.year

    @property
    def year(self):
        return self._year

    @property
    def month(self):
        return self._month

    @property
    def fmtym(self):
        return '{0:04d}-{1:02d}'.format(self._year, self._month)

    @property
    def fmtraw(self):
        return '{0:04d}{1:02d}'.format(self._year, self._month)

    def export_dict(self):
        """Return the month and year as a tuple."""
        return (self.month, self.year)

    def nextmonth(self):
        """Return the month after the current one."""
        return self + 1

    def prevmonth(self):
        """Return the month before the current one."""
        return self - 1

    def __str__(self):
        """Return a two digit value of the current month int value."""
        return '{0:02d}'.format(self._month)

    def __repr__(self):
        """Return a formated id of the current month."""
        return '{0:s}({1:02d}, year={2:d})'.format(self.__class__.__name__, self._month, self._year)

    def as_dump(self):
        """Nicely formatted representation in dumper."""
        return self.__repr__()

    def __add__(self, delta):
        """
        Add to a Date object the specified ``delta`` which could be either
        a string or a :class:`datetime.timedelta` or an ISO 6801 Period.
        """
        if isinstance(delta, int):
            if delta < 0:
                incr = -1
                delta = abs(delta)
            else:
                incr = 1
            year, month = self._year, self._month
            while delta:
                month += incr
                if month > 12:
                    year += 1
                    month = 1
                if month < 1:
                    year -= 1
                    month = 12
                delta -= 1
            if self._year == 0:
                year = 0
            return Month(month, year)
        elif not isinstance(delta, datetime.timedelta):
            delta = Period(delta)
        return Month(Date(self._year, self._month, 14) + delta)

    def __radd__(self, delta):
        """Commutative add."""
        return self.__add__(delta)

    def __sub__(self, delta):
        """
        Substract to a Date object the specified ``delta`` which could be either
        a string or a :class:`datetime.timedelta` or an ISO 6801 Period.
        """

        if isinstance(delta, int):
            return self.__add__(-1 * delta)
        elif not isinstance(delta, datetime.timedelta):
            delta = Period(delta)
        return Month(Date(self._year, self._month, 1) - delta)

    def __int__(self):
        return self._month

    def __cmp__(self, other):
        """Compare two month values."""
        rc = 1
        try:
            if isinstance(other, int) or ( isinstance(other, str) and len(other.lstrip('0')) < 3 ):
                rc = cmp(self.month, Month(int(other), self.year).month)
            else:
                if isinstance(other, tuple) or isinstance(other, list):
                    mtest = Month(*other)
                else:
                    mtest = Month(other)
                if self.year * mtest.year == 0:
                    rc = cmp(self.month, mtest.month)
                else:
                    rc = cmp(self.fmtym, mtest.fmtym)
        except StandardError:
            rc = 1
        finally:
            return rc


if __name__ == '__main__':
    import doctest
    doctest.testmod()
