#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
This example aims at dealing with dates and terms

Ok 20180731 - GR
"""

# Load useful packages for the examples
from __future__ import print_function, division, unicode_literals, absolute_import

from bronx.stdtypes import date
from footprints.util import rangex

print("\n-- Dealing with dates --\n")

# Create a first date
print("\nCreate a first date")
my_date_1 = date.Date("201801010000")
print(my_date_1)

# Create a second date from the first one
print("\nCreate a second date")
my_date_2 = my_date_1 - date.Period("P5D")
print(my_date_2)

# List all dates between those two ones
print("\nCreate the date range between those two dates")
my_date_range_1 = date.daterange(my_date_1, my_date_2)
for my_date in my_date_range_1:
    print(my_date)

# List one date in two between those two dates
print("\nCreate the date range between those two dates")
my_date_range_2 = date.daterange(my_date_1, my_date_2, date.Period("P2D"))
for my_date in my_date_range_2:
    print(my_date)

# Print some date's formats
print("\nSome formats for the dates")
print(my_date_1.ymd)
print(my_date_1.ymdhms)

# Get the current date
print("\nToday, we are the:")
print(date.today())

# Create a range of terms
print("\n-- Dealing with terms --\n")

print("\nA range from 0 to 10")
my_terms_1 = rangex(0, 10)
print(my_terms_1)

print("\nA range from 0 to 10 by step of 2")
my_terms_2 = rangex(0, 10, 2)
print(my_terms_2)

print("\nA range from 0 to 10 shifted by 25")
my_terms_3 = rangex("0-10", shift=25)
print(my_terms_3)
