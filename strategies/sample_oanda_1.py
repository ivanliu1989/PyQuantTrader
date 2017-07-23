#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Created on Sun Jul 23 14:31:51 2017

@author: Ivan Liu
"""
import pandas as pd
from pandas import DataFrame
import random
from copy import deepcopy

# Backtrader
import backtrader as bt

# PyQuantTrader
from PyQuantTrader import strategy as pqt_strategy
from PyQuantTrader import validation as pqt_val
from PyQuantTrader import analyzers as pqt_ana
from PyQuantTrader import indicators as pqt_ind
from PyQuantTrader import observers as pqt_obs
from PyQuantTrader import sizers as pqt_sizers

# OandaAPI
import oandapy

if __name__ == '__main__':  
    # Oanda data
    account = "101-011-6029361-001"
    access_token="8153764443276ed6230c2d8a95dac609-e9e68019e7c1c51e6f99a755007914f7"
    account_type = "practice"
    # Register APIs
    oanda = oandapy.API(environment=account_type, access_token=access_token)
    # Get historical prices
    hist = oanda.get_history(instrument = "AUD_CAD", granularity = "M15", count = 5000, candleFormat = "midpoint")
    dataframe = pd.DataFrame(hist['candles'])
    dataframe['openinterest'] = 0 
    dataframe = dataframe[['time', 'openMid', 'highMid', 'lowMid', 'closeMid', 'volume', 'openinterest']]
    dataframe['time'] = pd.to_datetime(dataframe['time'])
    dataframe = dataframe.set_index('time')
    dataframe = dataframe.rename(columns={'openMid': 'open', 'highMid': 'high', 'lowMid': 'low', 'closeMid': 'close'})
    data = bt.feeds.PandasData(dataname=dataframe)  
    
    n_cores = 4
    cash = 10000
    leverage = 20
    init_assets = cash * leverage
    positions = init_assets * 0.02
    itrs = 100
    
    # Walk forward
    tscv = pqt_val.TimeSeriesSplitImproved(5)
    split = tscv.split(dataframe, fixed_length=True, train_splits=2)
    walk_forward_results = list()
    # Be prepared: this will take a while
    for train, test in split:
        # TRAINING
     
        # Generate random combinations of fast and slow window lengths to test
        windowset = set()    # Use a set to avoid duplicates
        while len(windowset) < itrs:
            f = random.randint(1, 10) * 5
            s = random.randint(1, 10) * 10
            if f > s:    # Cannot have the fast moving average have a longer window than the slow, so swap
                f, s = s, f
            elif f == s:    # Cannot be equal, so do nothing, discarding results
                continue
            windowset.add((f, s))
     
        windows = list(windowset)
     
        trainer = bt.Cerebro(stdstats=False, maxcpus=n_cores)
        trainer.broker.set_cash(init_assets)
        trainer.broker.setcommission(0.0002)
        trainer.addanalyzer(pqt_ana.AcctStats)
        trainer.addsizer(bt.sizers.SizerFix, stake=positions)
        # trainer.addsizer(pqt_sizers.PropSizer)
        tester = deepcopy(trainer)
     
        trainer.optstrategy(pqt_strategy.SMAC, optim=True,    # Optimize the strategy (use optim variant of SMAC)...
                              optim_fs=windows)    # ... over all possible combinations of windows
        data_tmp = bt.feeds.PandasData(dataname=dataframe.iloc[train]) 
        print(dataframe.iloc[train].index.values[1])
        trainer.adddata(data_tmp)
        res = trainer.run()
        # Get optimal combination
        opt_res = DataFrame({r[0].params.optim_fs: r[0].analyzers.acctstats.get_analysis() for r in res}
                           ).T.loc[:, "return"].sort_values(ascending=False).index[0]
     
        # TESTING
        tester.addstrategy(pqt_strategy.SMAC, optim=True, optim_fs=opt_res)    # Test with optimal combination
        data_tmp = bt.feeds.PandasData(dataname=dataframe.iloc[test])          # corresponds to testing
        tester.adddata(data_tmp)
     
        res = tester.run()
        res_dict = res[0].analyzers.acctstats.get_analysis()
        res_dict["fast"], res_dict["slow"] = opt_res
        res_dict["start_date"] = dataframe.iloc[test[0]].name
        res_dict["end_date"] = dataframe.iloc[test[-1]].name
        walk_forward_results.append(res_dict)
    
    wfdf = DataFrame(walk_forward_results)
    wfdf


    # Walkforward results
    cerebro_wf = bt.Cerebro(stdstats=False)
    cerebro_wf.adddata(data)    # Give the data to cerebro
    cerebro_wf.broker.setcash(init_assets)
    cerebro_wf.broker.setcommission(0.0002)
    cerebro_wf.addstrategy(pqt_strategy.SMACWalkForward,
                           # Give the results of the above optimization to SMACWalkForward (NOT OPTIONAL)
                           fast=[int(f) for f in wfdf.fast],
                           slow=[int(s) for s in wfdf.slow],
                           start_dates=[sd.date() for sd in wfdf.start_date],
                           end_dates=[ed.date() for ed in wfdf.end_date])
    cerebro_wf.addobserver(pqt_obs.AcctValue)
    cerebro_wf.addobservermulti(bt.observers.BuySell)    # Plots up/down arrows
    #cerebro_wf.addsizer(pqt_sizers.PropSizer)
    cerebro_wf.addsizer(bt.sizers.SizerFix, stake=positions)
    cerebro_wf.addanalyzer(pqt_ana.AcctStats)
     
    cerebro_wf.run()
    
    cerebro_wf.plot(iplot=True, volume=True)
    cerebro_wf.broker.get_value()