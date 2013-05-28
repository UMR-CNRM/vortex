#!/bin/env python
# -*- coding:Utf-8 -*-

"""
Date interface.

Formats hypothesis:

1. the arguments representing a date must follow the following convention
   yyyymmdd[hh[mn[ss]]] with yyyy as the year in 4 numbers, mm as the month
   in 2 numbers, dd as the day in 2 numbers, hh as the hours (0-24), mn as the
   minutes and ss as the seconds.

2. so as to add or substract a duration to a date expressed in the preceding
   format(yyyymmdd[hh[mn[ss]]])the arguments must follow:

      * P starts an ISO 8601 Period definition
      * nY, the number of years (n positive integer),
      * nM, the number of months (n positive integer),
      * nD, the number of days (n positive integer),
      * T as a time separator,
      * nH, the number of hours (n positive integer),
      * nM, the number of minutes (n positive integer),
      * nS, the number of secondes (n positive integer)

   Example::

      P1Y <=> is a 1 year period
      M20D <=> is a 20 days period
      PT15H10M55S <=> is a 15 hours, 10 minutes and 55 secondes period

The available methods in the Date class are:

   * create a date in regard to the desired format (yyyymmddhhmnss,...,yyyy)
   * convert from usual date to julian date
   * deliver the minutes of a date if available
   * add/substract a duration to a date (y, m, d, h, mn, s)
   * deliver the number of days of a month
   * determine if a year is a leap year
   * deliver the time gap between two dates and the result is expressed in hours, minutes and secondes.

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
    if len(l) > 10 and len(l) <= 13:
        l.extend(['0', '0'])
    if len(l) > 13 and l[13] != ':':
        l[13:13] = [ ':' ]
    if len(l) > 16 and l[16] != ':':
        l[16:16] = [ ':' ]
    if len(l) > 13 and l[-1] != 'Z':
        l.append('Z')
    return ''.join(l)
    
def today():
    """Return current date, hours, minutes."""
    td = datetime.datetime.today()
    return Date(datetime.datetime(td.year, td.month, td.day, 0, 0))

def now():
    """Return current date, hours, minutes and seconds."""
    td = datetime.datetime.now()
    return Date(td.year, td.month, td.day, td.hour, td.minute, td.second, td.microsecond)

def lastround(rh=1, delta=0, base=None):
    """Return last date with a plain hour multiple of ``rh``."""
    if not base:
        base = now()
    if delta:
        base += Period(delta)
    return Date(base.year, base.month, base.day, base.hour - base.hour % rh, 0)

def synop(delta=0, base=None):
    """Return the date associated to the last synoptic hour."""
    return lastround(6, delta, base)

def guess(*args):
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

    if end == None:
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

    _period_regex = staticmethod(
            lambda s: re.compile(
        r'(?P<X>[+-]?P)(?P<Y>[0-9]+([,.][0-9]+)?Y)?'
        r'(?P<M>[0-9]+([,.][0-9]+)?M)?'
        r'(?P<W>[0-9]+([,.][0-9]+)?W)?'
        r'(?P<D>[0-9]+([,.][0-9]+)?D)?'
        r'((?P<T>T)(?P<h>[0-9]+([,.][0-9]+)?H)?'
        r'(?P<m>[0-9]+([,.][0-9]+)?M)?'
        r'(?P<s>[0-9]+([,.][0-9]+)?S)?)?$').match(s))

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
        if not isinstance(string, basestring):
            raise TypeError, "Expected string input"
        if len(string) < 2:
            raise ValueError, "Badly formed short string %s" % string

        match = Period._period_regex(string)
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
        elif isinstance(top, int) and len(args) < 2:
            ld = [ 0, top ]
        elif isinstance(top, int) and len(args) == 2:
            ld = list(args)
        elif isinstance(top, str):
            ld = [ 0, Period.parse(top) ]
        if not ld:
            raise ValueError("Initial Period value unknown")
        return datetime.timedelta.__new__(cls, *ld)

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
        if kw:
            args = (datetime.datetime(**kw),)
        if not args:
            raise ValueError("No initial value provided for Date")
        top = args[0]
        delta = ''
        ld = list()
        if isinstance(top, datetime.datetime):
            ld = [ top.year, top.month, top.day, top.hour, top.minute, top.second ]
        elif isinstance(top, float):
            top = Date._origin + datetime.timedelta(0, top)
            ld = [ top.year, top.month, top.day, top.hour, top.minute, top.second ]
        elif isinstance(top, str):
            (top, sep, delta) = top.partition('/')
            ld = [ int(x) for x in re.split('[-:HTZ]+', mkisodate(top)) if re.match('\d+$', x) ]
        else:
            ld = [ int(x) for x in args if type(x) in (int, float) or (isinstance(x, str) and re.match('\d+$', x)) ]
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
        return self.iso8601()

    def get_nbdays_month(self):
        """Returns the number of days of a month."""
        return nbdays_month(self.get_date())

    def is_leap_year(self):
        """Returns True in case of a leap year, False elsewhere"""
        return leap_year(self.get_date())

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

    def compact(self):
        return self.strftime('%Y%m%d%H%M%S')

    def vortex(self, cutoff='P'):
        return self.strftime('%Y%m%dT%H%M') + str(cutoff)[0].upper()

    def reallynice(self):
        return self.strftime("%A %d. %B %Y, at %H:%M:%S")

    def shellexport(self):
        return self.ymdhm

    def __add__(self, delta):
        """
        Add to a Date object the specified ``delta`` which could be either
        a string or a :class:`datetime.timedelta` or an ISO 6801 Period.
        """
        if not isinstance(delta, datetime.timedelta):
            delta = Period(delta)
        return Date(super(Date, self).__add__(datetime.timedelta(delta.days, delta.seconds)))

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
        if jdays == None:
            jdays = self.toordinal() - self.cnes_origin
        return Date(self.fromordinal(jdays + self.cnes_origin))

    def isleap(self, year=None):
        """Return either the current of specified year is a leap year."""
        if year==None:
            year = self.year 
        return calendar.isleap(year)

    def monthrange(self, year=None, month=None):
        """Return the number of days in the current of specified year-month couple."""
        if not year:
            year = self.year
        if not month:
            month = self.month
        return calendar.monthrange(year, month)[1]


class Time(object):

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
            ld = [ int(x) for x in re.split('[-:HTZ]+', top) if re.match('\d+$', x) ]
        else:
            ld = [ int(x) for x in args if type(x) in (int, float) or (isinstance(x, str) and re.match('\d+$', x)) ]
        if ld:
            if len(ld) < 2:
                ld.append(0)
            self._hour, self._minute = ld[0], ld[1]
        if self._hour == None or self._minute == None:
            raise ValueError("No way to build a Time value")

    @property
    def hour(self):
        return self._hour

    @property
    def minute(self):
        return self._minute

    def __deepcopy__(self, memo):
        """No deepcopy expected, so ``self`` is returned."""
        return self

    def __repr__(self):
        """Standard hour-minute representation."""
        return 'Time({0:d}, {1:d})'.format(self.hour, self.minute)
        
    def __str__(self):
        """Standard hour-minute string."""
        return '{0:02d}:{1:02d}'.format(self.hour, self.minute)

    def __int__(self):
        """Convert to `int`, ie: returns hours."""
        return self._hour

    def __cmp__(self, other):
        """Compare two Time values or a Time and an int value."""
        try:
            other = Time(other)
        except:
            rc = -1
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

    def __sub__(self, delta):
        """
        Add to a Date object the specified ``delta`` which could be either
        a string or a :class:`datetime.timedelta` or an ISO 6801 Period.
        """
        delta = Time(delta)
        hour, minute = self.hour - delta.hour, self.minute - delta.minute
        if minute < 0:
            minute = minute + 60
            hour = hour - 1
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

    def __init__(self, *args, **kw):
        if kw:
            args = (datetime.datetime(**kw),)
        if not args:
            raise ValueError("No initial value provided for Month")
        top = args[0]
        self._month = None
        self._year = today().year
        if isinstance(top, datetime.datetime):
            self._month, self._year = top.month, top.year
        elif isinstance(top, int) and top > 0 and top < 13:
            self._month = top
        else:
            try:
                tmpdate = Date(*args)
            except (ValueError, TypeError):
                raise ValueError("Could not create a Month from values provided %s", str(args))
            else:
                self._month, self._year = tmpdate.month, tmpdate.year

    @property
    def year(self):
        return self._year

    @property
    def month(self):
        return self._month

    def __str__(self):
        """Return a two digit value of the current month int value."""
        return '{0:02d}'.format(self._month)

    def __repr__(self):
        """Return a formated id of the current month."""
        return '<{0:s} object = {1:02d} in year {2:d}>'.format(self.__class__.__name__, self._month, self._year)

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
            return Month(Date(year, month, 1))
        elif not isinstance(delta, datetime.timedelta):
            delta = Period(delta)
        return Month(Date(self._year, self._month, 14) + delta)

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
        """
        Compare two month values.
        """
        try:
            rc = cmp(self._month, int(other))
        except:
            rc = -1
        finally:
            return rc


if __name__ == '__main__':
    import doctest
    doctest.testmod()
