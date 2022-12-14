kucoin-lending
==============
.. image:: https://img.shields.io/badge/python-3.6%2B-green
    :target: https://pypi.org/project/python-kucoin

Overview
--------

This bot automates your asset lending on kucoin.com, it improves on the
auto-lend feature by cancelling orders that have been sitting around for
a given number of hours

It than goes and re-lends these assets

Ideally to be run as a cron job

It only deals with 7 day lending

All dates are DD/MM/YYYY

An overview of the program https://youtu.be/nXDBVaByEZU

Features
--------

-  Cancel loan orders that are more than certain number of hours old

-  Submit lend orders, splitting them into (and up to) 3 lowest lending
   rates

-  Generate transaction report

-  add to 'unlendable' assets file, (assets with no landing rates
   available)

-  add to 'lending precision' file, if an asset already does not exist
   in it, precision = decimal place accuracy for lend orders, ie USDT is
   1, AVAX is 0.1 etc

-  Implementation of REST endpoints

Setup
-----

-  Generate a 'Trade' API in Kucoin

-  Kucoin Sandbox doesn't really work with lending at the time of
   writing

-  Store generated keys in your env under

   -  API_NAME,

   -  API_KEY,

   -  API_PASSPHRASE,

   -  API_SECRET

-  set delete_orders_older_than_hours to how long you want orders to
   persist

-  no need to switch off auto-lend, old orders will get cancelled and
   resubmitted before auto-lend wakes up, however, I recommend to switch
   off auto-lend anyway

-  assets that you do not want processed add to unlendable.csv

-  run program, trans_log.txt will report of cancellations and new lend
   orders

Going forward
-------------

-  generate profit report for last 7 days?

-  check which way an asset is trending, if it's going up use slightly
   higher interest rates

-  add order one level below the current lowest rate?

Change Log
----------
+-------+-------------------------------------------------------------+
| 1.1.0 | -  added amount multiple func, in the case of ADA you can   |
|       |    lend at least 10 ADA, however it has to be multiples     |
|       |    of 10, ie. 20, 90, 190 etc. Error msg from KC is not     |
|       |    specific enough, therefore, one has to mark assets like  |
|       |    these in the min_lend_amount.json file with a preceding  |
|       |    asterix, "ADA": "*10"                                    |
+-------+-------------------------------------------------------------+
| 1.0.0 | -  clean up code, first prod version                        |
+-------+-------------------------------------------------------------+
| 0.1.3 | -  keep orders that are already sitting at lowest rate      |
|       |                                                             |
|       | -  fix spread of assets to be lent out, use rates from      |
|       |    min_lend_amount.json                                     |
+-------+-------------------------------------------------------------+
| 0.1.2 | -  lending rates step up at 0.0001 from lowest available,   |
|       |    therefore if current rates from Kucoin are 0.00001 and   |
|       |    00003, our lending rates will fill in the 0.00002 gap    |
|       |                                                             |
|       | -  production (True/False) flag taken out                   |
|       |                                                             |
|       | -  if after rounding lend amount is 0.00, no lending,       |
|       |    especially true for ETH                                  |
|       |                                                             |
|       | -  improved rounding of amount to be lent out               |
+-------+-------------------------------------------------------------+
| 0.1.1 | fix up some assets amount format issues in trans_log.txt    |
+-------+-------------------------------------------------------------+
| 0.1.0 | initial Alpha                                               |
+-------+-------------------------------------------------------------+

| 

| 

| 
