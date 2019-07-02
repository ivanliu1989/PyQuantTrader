# -*- coding: utf-8 -*-
"""
Created on Wed Aug 23 22:30:31 2017

@author: sky_x
"""
import argparse
import datetime

# The above could be sent to an independent module
import backtrader as bt
from backtrader.utils import flushfile  # win32 quick stdout flushing

StoreCls = bt.stores.OandaStore
DataCls = bt.feeds.OandaData
BrokerCls = bt.brokers.OandaBroker

exactbars = 1
stopafter = 0
token = ""
account = ""
account_type = "practice"
live = False
qcheck=0.5
data0= 'AUD_USD'
data1= 'USD_CAD'
bidask= True
historical = True
fromdate = '2016-12-01T12:00:00'
smaperiod = 5


# Create a cerebro
cerebro = bt.Cerebro()

storekwargs = dict(
    token=token,
    account=account,
    practice=True
)

broker = BrokerCls(**storekwargs)
cerebro.setbroker(broker)

#if not args.no_store:
#    store = StoreCls(**storekwargs)
#
#if args.broker:
#    if args.no_store:
#        broker = BrokerCls(**storekwargs)
#    else:
#        broker = store.getbroker()
#
#    cerebro.setbroker(broker)

compression=1
timeframe = bt.TimeFrame.TFrame(bt.TimeFrame.Names[5])
# Manage data1 parameters
tf1 = bt.TimeFrame.Names[5]
tf1 = bt.TimeFrame.TFrame(tf1) if tf1 is not None else timeframe
cp1 = None
cp1 = cp1 if cp1 is not None else compression

#if args.resample or args.replay:
#    datatf = datatf1 = bt.TimeFrame.Ticks
#    datacomp = datacomp1 = 1
#else:
#    datatf = timeframe
#    datacomp = args.compression
#    datatf1 = tf1
#    datacomp1 = cp1
datatf = timeframe
datacomp = compression
datatf1 = tf1
datacomp1 = cp1

dtformat = '%Y-%m-%d' + ('T%H:%M:%S' * ('T' in fromdate))
fromdate = datetime.datetime.strptime(fromdate, dtformat)

DataFactory = DataCls

datakwargs = dict(
    timeframe=datatf, compression=datacomp,
    qcheck=qcheck,
    historical=historical,
    fromdate=fromdate,
    bidask=bidask,
    useask=False,
    backfill_start=False,
    backfill=False,
    tz=None
)

data0 = DataFactory(dataname=data0, **datakwargs)

data1 = 'USD_CAD'
data1 = DataFactory(dataname=data1, **datakwargs)

rekwargs = dict(
    timeframe=timeframe, compression=compression,
    bar2edge=False,
    adjbartime=False,
    rightedge=False,
    takelate=False,
)

cerebro.adddata(data0)
cerebro.adddata(data1)

valid = None

# Add the strategy
cerebro.addstrategy(TestStrategy)
                    #smaperiod=args.smaperiod,
                    #trade=trade,
#                    exectype=bt.Order.ExecType(args.exectype),
#                    stake=args.stake,
#                    stopafter=args.stopafter,
#                    valid=valid,
#                    cancel=args.cancel,
#                    donotcounter=args.donotcounter,
#                    sell=args.sell,
#                    usebracket=args.usebracket)

# Live data ... avoid long data accumulation by switching to "exactbars"
cerebro.run(exactbars=12)
if args.exactbars < 1:  # plotting is possible
    if args.plot:
        pkwargs = dict(style='line')
        if args.plot is not True:  # evals to True but is not True
            npkwargs = eval('dict(' + args.plot + ')')  # args were passed
            pkwargs.update(npkwargs)

        cerebro.plot(**pkwargs)
