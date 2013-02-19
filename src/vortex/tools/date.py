#!/bin/env python
# -*- coding:Utf-8 -*-

"""
Date interface

Formats hypothesis:

1. the arguments representing a date must follow the following convention
   yyyymmdd[hh[mn[ss]]] with yyyy as the year in 4 numbers, mm as the month
   in 2 numbers, dd as the day in 2 numbers, hh as the hours (0-24), mn as the
   minutes and ss as the seconds.

2. so as to add or substract a duration to a date expressed in the preceding
   format(yyyymmdd[hh[mn[ss]]])the arguments must follow:

      * P/M respectively Plus or Minus
      * nY, the number of years (n positive integer),
      * nM, the number of months (n positive integer),
      * nD, the number of days (n positive integer),
      * nH, the number of hours (n positive integer),
      * nm, the number of minutes (n positive integer),
      * ns, the number of secondes (n positive integer)

   Example::

      P1Y <=> retrieve 1 year
      M20D <=> retrieve 20 days
      P15H10m55s <=> add 15 hours, 10 minutes and 55 secondes
      M250D <=> retrieve 250 days

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
from exceptions import Exception 
from datetime import timedelta, datetime


def today():
    return Date(datetime.today())

def synop(d=None):
    if not d:
        d=today()
    return Date(d.year, d.month, d.day, int(d.hour/6)*6)

class NewVDError(Exception): pass

class VDMethodError(Exception): pass

class IDate(object):
    
    def get_nbdays_month(self):
        pass

    def is_leap_year(self):
        pass

    def get_fmt_date(self, fmt):
        pass

    def get_julian_day(self):
        pass

    def get_mn_from_date(self):
        pass

    def add_delta_to_date(self, delta, fmt):
        pass

    def sub_delta_to_date(self, delta, fmt):
        pass

    def diff_btw_dates(self, date_str2):
        pass


class Date(IDate, datetime):
# ------------------------------------------------------------------------------
#                   === Constants ===
# ------------------------------------------------------------------------------
    FMT_KEYS = [
        "yyyy",
        "yyyymm",
        "yyyymmdd",
        "yyyymmddhh",
        "yyyymmddhhmn",
        "yyyymmddhhmnss",
        "mn",
        "mm",
        "dd",
        "hh",
        "ss",
    ]
    FMT = [
        "%Y",
        "%Y%m",
        "%Y%m%d",
        "%Y%m%d%H",
        "%Y%m%d%H%M",
        "%Y%m%d%H%M%S",
        "%M",
        "%m",
        "%d",
        "%H",
        "%S",
    ]

    MAP_FMT = dict(zip(FMT_KEYS, FMT))

# ------------------------------------------------------------------------------
#                   ===  Construction - Initialization ===
# ------------------------------------------------------------------------------
    def __new__(cls, *args):
        """
        call to the constructor so as to create the part inheritated from
        datetime. This constructor also allows to deal with the different ways
        of creating a pure datetime object:
            - from a datetime object,
            - from a tuple containing Y, M, D (fromordinal method)
            - from a tuple containing Y, M, D, H, mn, s (today, now)
            - from a chain of characters following the format defined in 1)

        """
        #creation from a datetime object
        if isinstance(args[0], datetime):
            tt_1 = args[0].timetuple()
            args_init = (tt_1.tm_year, tt_1.tm_mon, tt_1.tm_mday, tt_1.tm_hour,
                         tt_1.tm_min, tt_1.tm_sec)
            cls = datetime.__new__(cls, *args_init)
        elif len(args) >= 3 and len(args) <= 8:
            #creation from a tuple
            #hypothesis: it's a tuple containing integers 
            #(y, m, d, [h, [mn, [s, [ms, [tzinfo]]]]])
            cls = datetime.__new__(cls, *args)
        elif isinstance(args[0], str):
            #creation from a chain of characters
            date_str = StrDate(args[0])
            args = tuple([int(elmt) for elmt in date_str.gen_date_str()])
            cls = datetime.__new__(cls, *args)
        else:
            raise NewVDError("Build Error")
        return cls

    def __init__(self, *args):
        super(Date, self).__init__()

    def __deepcopy__(self, memo):
        r"""
        We don't allow other copies of the current object to be made. So when a
        deepcopy is requested, self is returned. We assume that there isn't any
        concurrency access problem during the session.
        """
        return self

# ------------------------------------------------------------------------------
#                        === Caracteristics ===
# ------------------------------------------------------------------------------
    def get_nbdays_month(self):
        """Returns the number of days of a month."""
        return nbdays_month(self.get_date())

    def is_leap_year(self):
        """Returns True in case of a leap year, False elsewhere"""
        return leap_year(self.get_date())

    def get_julian_day(self):
        """Returns Julian day."""
        return self.strftime("%j")

    def get_mn_from_date(self):
        """Returns minutes of the date ('0' by default)."""
        return self.get_fmt_date('mn')

    def get_date(self, fmt=FMT_KEYS[5]):
        return self.get_fmt_date(fmt)

    def shellexport(self):
        return self.get_date()

# ------------------------------------------------------------------------------
#                          === Format ===
# ------------------------------------------------------------------------------

    @property
    def ymd(self):
        return self.strftime('%Y%m%d')
    
    @property
    def ymdh(self):
        return self.strftime('%Y%m%d%H')
    
    def get_fmt_date(self, fmt):
        """Returns the date in regard to the desired format in argument."""
        return self.strftime(self.MAP_FMT[fmt])

# ------------------------------------------------------------------------------
#                     === Operations with strings (+, -, diff) ===
# ------------------------------------------------------------------------------
    def add_delta(self, delta, fmt):
        """
        Adds a delta to a date and returns the result following the format.
        """
        return self.modif_date(delta, fmt, "add")

    def sub_delta(self, delta, fmt):
        """
        Substract a delta to a date and returns the result following the format.
        """
        return self.modif_date(delta, fmt, "sub")

    def diff_dates(self, date_str):
        """
        Calculate the diffence between the current date (the object itself) and
        the date passed in argument. Returns the result expressed in hours and
        minutes.
        """
        return self.diff_btw_dates(date_str)

    def _change_dhms_to_date(self, str_date_tmp, args):
        """
        Add a delta expressed in hours, minutes and seconds to the current date.
        """
        days, hours, mins, sec = args
        delta = timedelta(days=days, seconds=sec, minutes=mins, hours=hours)
        nv_date = Date(str_date_tmp) + delta
        return nv_date
# ------------------------------------------------------------------------------
#                     === Operations (+, -, diff) ===
# ------------------------------------------------------------------------------
    def __add__(self, delta):
        """
        Add directly a Date object and a delta. The delta can be a timdedelta
        object or a str object (following the correct format).
        """
        if isinstance(delta, timedelta):
            dt_date = super(Date, self).__add__(delta)
            v_date = Date(dt_date)
        elif isinstance(delta, str):
            v_date = Date(self.modif_date_td(delta, "add"))
        return v_date

    def __sub__(self, delta):
        """
        Substract directly a Date object and a delta. The delta can be a timdedelta
        ojbject or a str object (following the correct format).
        """
        if isinstance(delta, timedelta):
            dt_date = super(Date, self).__sub__(delta)
            v_date = Date(dt_date)
        elif isinstance(delta, str):
            v_date = Date(self.modif_date_td(delta, "sub"))
        elif isinstance(delta, Date):
            v_date = super(Date, self).__sub__(delta)
        else:
            print "Error", type(delta), delta
            v_date = None
        return v_date
# ------------------------------------------------------------------------------
#                     === Low-level Operations (+, -, diff) ===
# ------------------------------------------------------------------------------
    def modif_date(self, delta, fmt, type_modif):
        """
        Returns the modified date in regard to the operation (add or sub)
        following the format argument.
        """
        date_str = StrDate(self.get_date())
        dico_modif = {
            "add": date_str._add_ym_to_date,
            "sub": date_str._sub_ym_to_date
        }
        #obtains delta arguments
        parse_args_delta = _parse_delta_date(delta)
        args_delta = _creer_args_delta_date(*parse_args_delta)
        #adds/substracts years and months first
        str_date_tmp = dico_modif[type_modif](args_delta[0:2])
        #then the days, hours, minutes and secondes
        dt1 = self._change_dhms_to_date(str_date_tmp, args_delta[2:])
        #return the formatted chain
        return self._fmt_date(fmt, dt1)

    def modif_date_td(self, delta, type_modif):
        """
        Returns the modified date in regard to the operation (add or sub)
        """
        date_str = StrDate(self.get_date())
        dico_modif = {
            "add": date_str._add_ym_to_date,
            "sub": date_str._sub_ym_to_date
        }
        #obtains delta arguments
        parse_args_delta = _parse_delta_date(delta)
        args_delta = _creer_args_delta_date(*parse_args_delta)
        #adds/substracts years and months first
        str_date_tmp = dico_modif[type_modif](args_delta[0:2])
        #then the days, hours, minutes and secondes
        dt1 = self._change_dhms_to_date(str_date_tmp, args_delta[2:])
        return dt1

    def diff_btw_dates(self, date_str):
        """
        Returns the time difference between the current date and the date passed
        in argument. The result is expressed in hours and minutes.
        """
        date1 = Date(date_str)
        delta = self - date1
        days = delta.days
        sec = delta.seconds
        return hours_circle(days, sec)
#------------------------------------------------------------------------------
#                    === Format (datetime to string) ===
# ------------------------------------------------------------------------------
    def _fmt_date(self, fmt, arg_date=None):
        """
        Returns a chain of characters following the fmt format arg_dateument from a
        datetime object or a Date object. The arg_date can have different type of format:
            "yyyy"
            "yyyymm"
            "yyyymmdd"
            "yyyymmddhh"
            "yyyymmddhhmn"
            "yyyymmddhhmnss"
        """
        if arg_date:
            try:
                return arg_date.strftime(self.MAP_FMT[fmt])
            except ValueError:
                return self._fmt_old_date(fmt, arg_date)
        else:
            try:
                return self.get_date(fmt)
            except ValueError:
                return self._fmt_old_date(fmt)

    def _fmt_old_date(self, fmt, arg_date=None):
        """
        Allow us to simulate the strftime function for dates before 1900 so as
        to assure compatibility with gregorian dates. Returns a chain of
        characters following the fmt format arg_dateument from a
        datetime object or a Date object. The arg_dateument can have different type
        of format:
            "yyyy"
            "yyyymm"
            "yyyymmdd"
            "yyyymmddhh"
            "yyyymmddhhmn"
            "yyyymmddhhmnss"
        """
        if arg_date:
            #keep only year, day and month from the date
            iso_date = arg_date.isoformat().split("T")[0]
            # eliminate the iso-format
            iso_date = ''.join(iso_date.split("-"))
        else:
            #keep only year, day and month from the date
            iso_date =  self.isoformat().split("T")[0]
            # eliminate the iso-format
            iso_date = ''.join(iso_date.split("-"))
        if fmt == self.FMT_KEYS[0]:
            date_str = iso_date[0:4]
        elif fmt == self.FMT_KEYS[1]:
            date_str = iso_date[0:6]
        elif fmt == self.FMT_KEYS[2]:
            date_str = iso_date[0:8]
        elif fmt == self.FMT_KEYS[3]:
            date_str = iso_date[0:8] + "00"
        elif fmt == self.FMT_KEYS[4]:
            date_str = iso_date[0:8] + "00" + "00"
        elif fmt == self.FMT_KEYS[5]:
            date_str = iso_date[0:8] + "00" + "00" + "00"
        else:
            raise ValueError
        return date_str
# ------------------------------------------------------------------------------
#                        === datetime functions overloading  ===
# ------------------------------------------------------------------------------
    def replace(self, **kwargs):
        """
        Possible:arguments
        [year[,month[,day[,hour[,minute[,second[,microsecond[,tzinfo]]]]]]]]
        """
        attr_list = ['year', 'month', 'day', 'hour', 'minute', 'second' ]
        values_list = [self.year, self.month, self.day, self.hour,
                       self.minute, self.second]
        vdico = dict(zip(attr_list, values_list))
        vdico.update(kwargs)
        str_new_vdate = ''
        for elmt in attr_list:
            if elmt != 'year' and vdico[elmt] < 10:
                str_new_vdate += "0" + str(vdico[elmt])
            else:
                str_new_vdate +=  str(vdico[elmt])
        new_strvdate = StrDate(str_new_vdate)
        if str_new_vdate == new_strvdate.get_date():
            return Date(new_strvdate.get_date())
        else:
            raise VDMethodError("Obtained Date is not valid")

# ------------------------------------------------------------------------------
#                          === CNES Julian calendar ===
# ------------------------------------------------------------------------------
    @property
    def _cnesjulianorigin(self):
        return datetime(1950, 1, 1).toordinal()

    def to_cnesjulian(self, date=[]):
        """
        convert current Date() object, or arbitrary date, to CNES julian calendar 
        >>> d = Date('20111026')
        >>> d.to_cnesjulian()
        22578
        >>> d.to_cnesjulian(date=[2011,10, 27])
        22579
        """
        if not date:
            date = [ int(x) for x in self.strftime("%Y %m %d").split() ]

        return datetime(date[0], date[1], date[2]).toordinal() - self._cnesjulianorigin
    
    def from_cnesjulian(self, *args):
        """
        >>> d = Date('20111025')
        >>> d.from_cnesjulian()
        '20111025000000'
        >>> d.from_cnesjulian(22578)
        '20111026000000'
        """
        if args:
            date_str = StrDate(self._fmt_date(
                self.FMT_KEYS[5], 
                arg_date=datetime.fromordinal(args[0] + self._cnesjulianorigin)
            ))
            return date_str._vxdate
        return self.get_date()   

################################################################################
"""
The StrDate considers the date as being a chain of character following
the format convention:
    yyyymmdd[hh[mn[ss]]] with yyyy as the year in 4 numbers, mm as the month 
    in 2 numbers, dd as the day in 2 numbers, hh as the hours (0-24), mn as the
    minutes and ss as the seconds.

This class is used by the date class so as to allow it to deal with this
kind of representation of a date.

"""

class StrDate(object):

    def __init__(self, date):
        args = self._get_tuple_ym_other(date)
        self._vxdate = ''.join(self._verify_date(args))

# ------------------------------------------------------------------------------
#                         === Change of format ===
# ------------------------------------------------------------------------------
    def gen_date_str(self):
        """
        Returns a tuple containing the year, the month, the day, the hour, the
        minutes and the seconds from a chain of characters.
        The authorized formats for the chain are:
            - AAAAMMJJ (year, month, day),
            - AAAAMMJJHH (hours included),
            - AAAAMMJJHHMM (minutes included),
            - AAAAMMJJHHMMSS (seconds included).
        as the hours, minutes and seconds parameters are optional, they are set
        to 0 by default.
        """
        dico_format = {
            #AAAAMMJJ
            8: [[ 0, 4, 6, 8 ], self._date_type_1],
            #AAAAMMJJHH
            10: [[ 0, 4, 6, 8, 10 ], self._date_type_2],
            #AAAAMMJJHHMM
            12: [[ 0, 4, 6, 8, 10, 12 ], self._date_type_3],
            #AAAAMMJJHHMMSS
            14: [[ 0, 4, 6, 8, 10, 12, 14 ], self._date_type_4]
        }
        chosen_fct = dico_format[len(self._vxdate)][1]
        fmt = dico_format[len(self._vxdate)][0]
        year, month, day, hour, minute, second = chosen_fct(fmt)
        return year, month, day, hour, minute, second

    def _date_type_1(self, liste_format):
        """ 
        Used to return a tuple containing the element of the current object.
        The hours, minutes and seconds parameters are missing, so set to "0".
        """
        year = self._vxdate[liste_format[0]:liste_format[1]]
        month = self._vxdate[liste_format[1]:liste_format[2]]
        day = self._vxdate[liste_format[2]:liste_format[3]]
        hour = "0"
        minute = "0"
        second = "0"
        return year, month, day, hour, minute, second

    def _date_type_2(self, liste_format):
        """
        Used to return a tuple containing the element of the current object.
        The minutes and seconds parameters are missing, so set to "0".
        """

        year, month, day, u_hour, minute, second = self._date_type_1(
                                            liste_format[0:4])
        hour = self._vxdate[liste_format[3]:liste_format[4]]
        return year, month, day, hour, minute, second

    def _date_type_3(self, liste_format):
        """
        Used to return a tuple containing the element of the current object.
        The seconds parameter is missing, so set to "0".
        """
        year, month, day, hour, u_minute, second = self._date_type_2(
                                            liste_format[0:5])
        minute = self._vxdate[liste_format[4]:liste_format[5]]
        return year, month, day, hour, minute, second

    def _date_type_4(self, liste_format):
        """
        Used to return a tuple containing the element of the current object.
        """

        year, month, day, hour, minute, u_second = self._date_type_3(
                                            liste_format[0:6])
        second = self._vxdate[liste_format[5]:liste_format[6]]
        return year, month, day, hour, minute, second

# ------------------------------------------------------------------------------
#                             === Extraction ===
# ------------------------------------------------------------------------------
    def _get_tuple_ym_other(self, date):
        year = date[0:4]
        month = date[4:6]
        other = date[6:]
        return year, month, other

    def _gen_date_fmt(self, fmt):
        """
        Returns a part of the date according to the expressed format fmt.
        """
        dico_fmt = {
            "yyyy" : self.gen_date_str()[0:1],
            "yyyymm" : self.gen_date_str()[0:2],
            "yyyymmdd" : self.gen_date_str()[0:3],
            "yyyymmddhh" : self.gen_date_str()[0:4],
            "yyyymmddhhmn" : self.gen_date_str()[0:5],
            "yyyymmddhhmnss" : self.gen_date_str()[0:6],
            "mn" : self.gen_date_str()[4:5]
        }
        str_res = ''.join(dico_fmt[fmt])
        return str_res

# ------------------------------------------------------------------------------
#                             === Verification ===
# ------------------------------------------------------------------------------
    def _verify_date(self, args):
        """
        Allows us to verify the correctness of the day, the month and the year
        of the date passed in argument (args). If necessary, the elements are
        changed.
        """
        dico_nbdays_month = {
            "01": 31, "02": 28, "03": 31, "04": 30, "05": 31, "06": 30,
            "07": 31, "08": 31, "09": 30, "10": 31, "11": 30, "12": 31
        }
        feb_leap = { "02": 29 }
        year, month, other = args
        day = other[0:2]
        other = other[2:len(other)]
        if len(month) < 2:
            month = "0" + month
        if len(day) < 2:
            month = "0" + day
        #if a construction of a datetime object is possible then it's ok
        try:
            int_args = [int(year), int(month), int(day)]
            datetime(*int_args)
            return args
        except ValueError:
            #incoherence between days and month
            #construction of a date to find the number of days of the month
            leapyear = self.leap_year(year)
            if leapyear and month == "02":
                days_nb = feb_leap[month]
            else:
                days_nb = dico_nbdays_month[month]
            if days_nb < int(day):
                day = str(days_nb)
                other = day + other
                return (year, month, other)
            else:
                print args
                raise
# ------------------------------------------------------------------------------
#                             === Caracteristics ===
# ------------------------------------------------------------------------------
    def nbdays_month(self):
        return nbdays_month(self._vxdate)

    def leap_year(self, year=None):
        """
        Determine if it's a leap year.
        """
        try:
            return leap_year(self.get_date(), year)
        except AttributeError:
            return leap_year(year)
# ------------------------------------------------------------------------------
#                             === Representation ===
# ------------------------------------------------------------------------------
    def get_date(self):
        """Returns the date."""
        return self._vxdate
# ------------------------------------------------------------------------------
#                          === Operations (+, -, diff) ===
# ------------------------------------------------------------------------------
    def _sub_ym_to_date(self, args):
        """
        Substract to a date a duration expressed in terms of years and months.
        """
        year, month = args
        y_1 = int(self._vxdate[0:4])
        m_1 = int(self._vxdate[4:6])
        other = self._vxdate[6:]
        #so as to take into account month < -12
        month, year = global_month_circle(month, year, False)
        #consequently year modification
        y_1 += year
        #consequently month modification
        m_1 += month
        #so as to take into account m < 1
        m_1, y_1 = month_circle_1(m_1, y_1)
        #modification of the lenght of m
        if m_1 < 10:
            m_1 = '0' + str(m_1)
        else:
            m_1 = str(m_1)
        y_1 = str(y_1)
        #the consistency of year, month and day must be verified
        y_1, m_1, other = self._verify_date((y_1, m_1, other))
        return ''.join((y_1, m_1, other))

    def _add_ym_to_date(self, args):
        """
        Add to a date a duration expressed in terms of years and months.
        """
        year, month = args
        y_1 = int(self._vxdate[0:4])
        m_1 = int(self._vxdate[4:6])
        other = self._vxdate[6:]
        #so as to take into account month > 12
        month, y_1 = global_month_circle(month, y_1)
        #consequently year modification
        y_1 += year
        #consequently month modification
        m_1 += month
        #so as to take into account m > 12
        m_1, y_1 =  month_circle_2(m_1, y_1)
        #modification of the lenght of m
        if m_1 < 10:
            m_1 = '0' + str(m_1)
        else:
            m_1 = str(m_1)
        y_1 = str(y_1)
        #the consistency of year, month and day must be verified
        y_1, m_1, other = self._verify_date((y_1, m_1, other))
        return ''.join((y_1, m_1, other))
# ------------------------------------------------------------------------------
"""
Utilities functions so as to perform some operations on date objetc.

Formats hypothesis:
    1) the arguments representing a date must follow the following convention
    yyyymmdd[hh[mn[ss]]] with yyyy as the year in 4 numbers, mm as the month
    in 2 numbers, dd as the day in 2 numbers, hh as the hours (0-24), mn as the
    minutes and ss as the seconds

    2) so as to add or substract a duration to a date expressed in the preceding
    format(yyyymmdd[hh[mn[ss]]])the arguments must follow:
        - P/M respectively Plus or Minus
        - nY, the number of years (n positive integer),
        - nM, the number of months (n positive integer),
        - nD, the number of days (n positive integer),
        - nH, the number of hours (n positive integer),
        - nm, the number of minutes (n positive integer),
        - ns, the number of secondes (n positive integer)
    Ex: P1Y <=> retrieve 1 year
        M20D <=> retrieve 20 days
        P15H10m55s <=> add 15 hours, 10 minutes and 55 secondes
        M250D <=> retrieve 250 days

"""

FIND_REGEX_DELTADATE = \
r"^(P|M)([\d]{0,3}Y)*([\d]{0,3}M)*([\d]{0,4}D)*([\d]{0,5}H)*([\d]{0,6}m)*([\d]{0,6}s)*"


# ------------------------------------------------------------------------------
#                       === Common utilities  ===
# ------------------------------------------------------------------------------

def gmc_core(sign, threshold, nb_month, year):
    rem = (sign * nb_month) % threshold
    nb_month = (sign * nb_month) / threshold
    year += sign * nb_month
    nb_month = sign * rem
    return nb_month, year

def global_month_circle(nb_month, year, pos=True):
    """
    >>> global_month_circle(48,0)
    (0, 4)
    >>> global_month_circle(13,10)
    (1, 11)
    >>> global_month_circle(-48,0,False)
    (0, -4)
    >>> global_month_circle(-13,-10,False)
    (-1, -11)

    """
    threshold = 12
    if pos:
        sign = 1
    else:
        sign = -1
    if pos:
        if nb_month > sign * threshold:
            nb_month, year = gmc_core(sign, threshold, nb_month, year)
        elif nb_month == sign * threshold:
            year += sign
            nb_month = 0
        else:
            pass
        return nb_month, year
    else:
        if nb_month < sign * threshold:
            nb_month, year = gmc_core(sign, threshold, nb_month, year)
        elif nb_month == sign * threshold:
            year += sign
            nb_month = 0
        else:
            pass
        return nb_month, year
   
def month_circle_1(nb_month, year):
    """
    The nb_month variable is by hypothesis between -11 and +12. So this function
    allow us to change the number representing the year according to the
    negative value representing the month.
    >>> month_circle_1(-5,1)
    (7, 0)
    >>> month_circle_1(3,10)
    (3, 10)
    >>> month_circle_1(-3,10)
    (9, 9)
    """
    if nb_month < 1:
        nb_month = 12 + nb_month
        year -= 1
    else:
        pass
    return nb_month, year

def month_circle_2(nb_month, year):
    """
    Allow to deal with the different cases where the number representing the
    month of the year became greater than 12 due to some operations.
    It concerns only the positive cases.
    >>> month_circle_2(48,0)
    (0, 4)
    >>> month_circle_2(13,10)
    (1, 11)
    """
    threshold = 12
    sign = 1
    if nb_month > threshold:
        return gmc_core(sign, threshold, nb_month, year)
    else:
        return nb_month, year

def hours_circle(days, seconds):
    #conversion from days to hours
    hours = days * 24
    #conversion from minutes to secondes
    minutes = seconds / 60
    if minutes > 60:
        rem = minutes % 60
        nb_hours = minutes / 60
        hours += nb_hours
        minutes = rem
    if minutes < 10:
        str_res = str(hours) + 'h0' + str(minutes) + 'mn'
        return str_res
    else:
        return "%sh%smn" % (hours, minutes)

# ------------------------------------------------------------------------------
#                             === Expressions Filtering ===
# ------------------------------------------------------------------------------
def _verif_delta(delta):
    """
    >>> _verif_delta("P100Y25M2D")
    True
    >>> _verif_delta("P1Y1s")
    True
    >>> _verif_delta("P1Y10A")
    False
    >>> _verif_delta("1Y1s")
    False
    """
    BEGIN = r"(^[P|M])"
    INNER = r"([A-CE-GI-LN-XZa-ln-rt-z])"
    patc = re.compile(BEGIN)
    match = patc.search(delta)
    if not match:
        return False
    else:
        #print "debut", match.groups()
        patc = re.compile(INNER)
        match = patc.search(delta[1:])
        if not match:
            return True
        else:
            #print "inner", match.groups()
            return False

def _parse_delta_2(delta):
    """
    >>> _parse_delta_2("P100Y25M2D")
    ('P', '100Y', '25M', '2D', None, None, None)
    >>> _parse_delta_2("P1Y1s")
    ('P', '1Y', None, None, None, None, '1s')
    >>> _parse_delta_2("P100Y25M2D250s")
    ('P', '100Y', '25M', '2D', None, None, '250s')
    """
    FD = [
        r"(^[P|M])",
        r"(\d+Y)",
        r"(\d+M)",
        r"(\d+D)",
        r"(\d+H)",
        r"(\d+m)",
        r"(\d+s)"
    ]
    res = list()
    for reg in FD:
        patc = re.compile(reg)
        match = patc.search(delta)
        if not match:
            res.append(None)
        else:
            res.append(match.group(0))
    return tuple(res)

def _parse_delta_date(delta):
    """
    Returns a chain containing the elements so as to create a timedelta object.
    The chain delta must follow one of the following formats:
    suivant:
        P ou M (Plus or Minus),
        [0-999] Y (number of years)
        [0-999] M (number of months)
        [0-999] D (number of days)
        [0-999] H (number of hours)
        [0-999] m (number of minutes)
        [0-999] s (number of seconds)

    >>> _parse_delta_date("P100Y25M2D")
    ('P', '100Y', '25M', '2D', None, None, None)
    >>> _parse_delta_date("P1Y1s")
    ('P', '1Y', None, None, None, None, '1s')
    """
    if _verif_delta(delta):
        patc = re.compile(FIND_REGEX_DELTADATE)
        match = patc.match(delta)
        return match.groups()
    else:
        return None

class mycontext(object):

    def __init__(self):
        self._innner = 0

    def execute(self, sign, var):
        try:
            return sign * int(var[:-1])
        except TypeError:
            return 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return True


def _creer_args_delta_date(*args):
    """
    Returns a tuple containing integers (negative or postive) from a tuple 
    obtained by a call to parse_delta_date.
    >>> _creer_args_delta_date(*('P', '100Y', '25M', '2D', None, None, None))
    (100, 25, 2, 0, 0, 0)
    >>> _creer_args_delta_date(*('P', '100Y', '25M', '2D', None, None, '10s'))
    (100, 25, 2, 0, 0, 10)
    """
    sign, y_1, m_1, d_1, h_1, mn_1, s_1 = args
    if sign == "M":
        sign = -1
    elif sign == "P":
        sign = 1
    else:
        print "Erreur"
    myctxt = mycontext()
    with myctxt as tmp:
        y_1 = tmp.execute(sign, y_1)
    with myctxt as tmp:
        m_1 = tmp.execute(sign, m_1)
    with myctxt as tmp:
        d_1 = tmp.execute(sign, d_1)
    with myctxt as tmp:
        h_1 = tmp.execute(sign, h_1)
    with myctxt as tmp:
        mn_1 = tmp.execute(sign, mn_1)
    with myctxt as tmp:
        s_1 = tmp.execute(sign, s_1)
    return (y_1, m_1, d_1, h_1, mn_1, s_1)

# ------------------------------------------------------------------------------
#                             ===  Caracteristics ===
# ------------------------------------------------------------------------------

def nbdays_month(date_str):
    """
    From a date returns the number of days of the month. 
    >>> nbdays_month("20110112")
    31
    >>> nbdays_month("20110715")
    31
    >>> nbdays_month("20110901")
    30
    """
    #first construction of a datetime object
    y_1 = int(date_str[0:4])
    m_1 = int(date_str[4:6])
    dt_1 = datetime(y_1, m_1, 1)
    m_1, y_1 = global_month_circle(m_1 + 1, y_1) 
    #then add one month to the datetime object
    #to create a second datetime object
    dt_2 = datetime(y_1, m_1, 1)
    return (dt_2 - dt_1).days

def leap_year(date_str, year=None):
    """
    Determine if it's a leap year.
    """
    if year:
        an1 = int(year)
    else:
        an1 = int(date_str[0:4])
    if (an1 % 4 == 0):
        if (an1 % 100 == 0):
            if (an1 % 400 == 0):
                return True
            else:
                return False
        else:
            return True
    else:
        return False


if __name__ == '__main__':
    import doctest
    doctest.testmod()

