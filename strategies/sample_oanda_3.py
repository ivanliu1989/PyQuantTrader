#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Created on Sun Jul 23 14:31:51 2017
Multiple series (portfolio)
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

class MyStrategy(bt.Strategy):  
    params = (  
        ('ssa_window', 15),  
        ('maperiod', 15),  
    )  
  
    def log(self, txt, dt=None):  
        ''''' Logging function fot this strategy'''  
        dt = dt or self.datas[0].datetime.date(0)  
        print('%s, %s' % (dt.isoformat(), txt))  
  
    def __init__(self):  
        # Keep a reference to the "close" line in the data[0] dataseries  
        self.dataclose = self.datas[0].close  
  
        # To keep track of pending orders and buy price/commission  
        self.order = None  
        self.buyprice = None  
        self.buycomm = None  
  
        # Add a MovingAverageSimple indicator  
        self.ssa = ind.ssa_index.ssa_index_ind(ssa_window=self.params.ssa_window, subplot=False)  
        # bt.indicator.LinePlotterIndicator(self.ssa, name='ssa')  
        self.sma = bt.indicators.SimpleMovingAverage(period=self.params.maperiod)  
    def start(self):  
        print("the world call me!")  
  
    def prenext(self):  
        print("not mature")  
  
    def notify_order(self, order):  
        if order.status in [order.Submitted, order.Accepted]:  
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do  
            return  
  
        # Check if an order has been completed  
        # Attention: broker could reject order if not enougth cash  
        if order.status in [order.Completed]:  
            if order.isbuy():  
                self.log(  
                    'BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %  
                    (order.executed.price,  
                     order.executed.value,  
                     order.executed.comm))  
  
                self.buyprice = order.executed.price  
                self.buycomm = order.executed.comm  
            else:  # Sell  
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %  
                         (order.executed.price,  
                          order.executed.value,  
                          order.executed.comm))  
  
            self.bar_executed = len(self)  
  
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:  
            self.log('Order Canceled/Margin/Rejected')  
  
        self.order = None  
  
    def notify_trade(self, trade):  
        if not trade.isclosed:  
            return  
  
        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %  
                 (trade.pnl, trade.pnlcomm))  
  
    def next(self):  
        # Simply log the closing price of the series from the reference  
        self.log('Close, %.2f' % self.dataclose[0])  
  
        # Check if an order is pending ... if yes, we cannot send a 2nd one  
        if self.order:  
            return  
  
        # Check if we are in the market  
        if not self.position:  
  
            # Not yet ... we MIGHT BUY if ...  
            if self.dataclose[0] > self.ssa[0]:  
  
                # BUY, BUY, BUY!!! (with all possible default parameters)  
                self.log('BUY CREATE, %.2f' % self.dataclose[0])  
  
                # Keep track of the created order to avoid a 2nd order  
                self.order = self.buy()  
  
        else:  
  
            if self.dataclose[0] < self.ssa[0]:  
                # SELL, SELL, SELL!!! (with all possible default parameters)  
                self.log('SELL CREATE, %.2f' % self.dataclose[0])  
  
                # Keep track of the created order to avoid a 2nd order  
                self.order = self.sell()  
    def stop(self):  
        print("death")  
  
    

if __name__ == '__main__':  
    # Oanda data
    account = ""
    access_token=""
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
    itrs = 40
    
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
     
    cerebro_wf.addanalyzer(bt.analyzers.PyFolio)
    cerebro_wf.addwriter(bt.WriterFile, csv=True, out='D:/Projects/PyQuantTrader/strategies/output.csv')
    strats = cerebro_wf.run()
    
    cerebro_wf.plot(iplot=True, volume=True)
    cerebro_wf.broker.get_value()

    strat0 = strats[0]
    pyfolio = strat0.analyzers.getbyname('pyfolio')
    returns, positions, transactions, gross_lev = pyfolio.get_pf_items()
    returns.to_csv('D:/Projects/PyQuantTrader/strategies/returns.csv')
    positions.to_csv('D:/Projects/PyQuantTrader/strategies/positions.csv')
    transactions.to_csv('D:/Projects/PyQuantTrader/strategies/transactions.csv')
    gross_lev.to_csv('D:/Projects/PyQuantTrader/strategies/gross_lev.csv')
  
    print('-- RETURNS')
    print(returns)
    print('-- POSITIONS')
    print(positions)
    print('-- TRANSACTIONS')
    print(transactions)
    print('-- GROSS LEVERAGE')
    print(gross_lev)

    import pyfolio as pf
    # PyFolio and backtrader
    pf.create_round_trip_tear_sheet(returns, positions, transactions)
	 
    len(returns.index)
    benchmark_rets = pd.Series([0.00004] * len(returns.index), index=returns.index)   
    pf.create_full_tear_sheet(returns, positions, transactions, benchmark_rets=benchmark_rets,
                              live_start_date='2017-07-10')

