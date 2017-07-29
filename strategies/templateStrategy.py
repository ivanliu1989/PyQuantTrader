# -*- coding: utf-8 -*-
"""
Created on Wed Jul 26 21:13:26 2017

@author: Ivan Liu
"""

import pandas as pd
from pandas import DataFrame
import random
from copy import deepcopy
import math

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


# Strategy
class MyStrategy(bt.Strategy):  
    
    params = dict(
            hold = [8,8],
            )
    
    def notify_order(self, order):
        if order.status == order.Submitted:
            return

        dt, dn = self.datetime.datetime(), order.data._name
        print('{} {} Order {} Status {}'.format(
            dt, dn, order.ref, order.getstatusname())
        )

        whichord = ['main', 'stop', 'limit', 'close']
        
        if not order.alive():  # not alive - nullify
            dorders = self.o[order.data]
            idx = dorders.index(order)
            dorders[idx] = None
            print('-- No longer alive {} Ref'.format(whichord[idx]))

            if all(x is None for x in dorders):
                dorders[:] = []  # empty list - New orders allowed


    def log(self, txt, dt=None):  
        ''''' Logging function fot this strategy'''  
        dt = dt or self.datas[0].datetime.datetime(0)  
        print('%s, %s' % (dt.isoformat(), txt))  

    def __init__(self):  
        #self.AUDUSDclose = self.datas[0].close
        #self.USDCADclose = self.datas[1].close
        # self.dataclose = self.datas[0].close
        #self.sma1 = bt.indicators.SMA(self.data1.close, period=15)
        
        self.Spreads = Spreads(self.datas[0], self.datas[1])
        self.o = dict() # orders per data (main, stop, limit, manual-close)
        self.holding = dict() # holding periods per data
        
    def start(self):  
        print("the world call me!")  
  
    def prenext(self):  
        print("not mature")  
  
    def next(self):  
        self.log('Spreads, %.10f' % self.Spreads[0]) 
        
        for i, d in enumerate(self.datas):
            dt, dn = self.datetime.datetime(), d._name
            pos = self.getposition(d).size
            print('{} {} Position {}'.format(dt, dn, pos))
            
            if not pos and not self.o.get(d, None):  # no market / no orders
                self.o[d] = [self.buy(data=d)]
                print('{} {} Buy {}'.format(dt, dn, self.o[d][0].ref))
                self.holding[d] = 0
                
            elif pos:
                self.holding[d] += 1
                if self.holding[d] >= self.p.hold[i]:
                    o = self.close(data=d)
                    self.o[d].append(o)  # manual order to list of orders
                    print('{} {} Manual Close {}'.format(dt, dn, o.ref))


# Sizer


# Indicators
class Spreads(bt.Indicator):
    _mindatas = 1
    
    packages = ('math',)
    lines = ('Spreads',)
    
    def __init__(self):
        self.AUDUSDclose = self.data0.close
        self.USDCADclose = self.data1.close
    
    def next(self):
        self.lines.Spreads[0] = math.log10(self.AUDUSDclose[0] / self.USDCADclose[0])
        

# Run Strategy
def runstrat(args=None):
    
    # Oanda data
    account = "101-011-6029361-001"
    access_token="8153764443276ed6230c2d8a95dac609-e9e68019e7c1c51e6f99a755007914f7"
    account_type = "practice"
    # Register APIs
    oanda = oandapy.API(environment=account_type, access_token=access_token)
    # Get historical prices
    hist = oanda.get_history(instrument = "AUD_USD", granularity = "M15", count = 5000, candleFormat = "midpoint")
    dataframe = pd.DataFrame(hist['candles'])
    dataframe['openinterest'] = 0 
    dataframe = dataframe[['time', 'openMid', 'highMid', 'lowMid', 'closeMid', 'volume', 'openinterest']]
    dataframe['time'] = pd.to_datetime(dataframe['time'])
    dataframe = dataframe.set_index('time')
    dataframe = dataframe.rename(columns={'openMid': 'open', 'highMid': 'high', 'lowMid': 'low', 'closeMid': 'close'})
    AUDUSD = bt.feeds.PandasData(dataname=dataframe)  
    
    hist = oanda.get_history(instrument = "USD_CAD", granularity = "M15", count = 5000, candleFormat = "midpoint")
    dataframe = pd.DataFrame(hist['candles'])
    dataframe['openinterest'] = 0 
    dataframe = dataframe[['time', 'openMid', 'highMid', 'lowMid', 'closeMid', 'volume', 'openinterest']]
    dataframe['time'] = pd.to_datetime(dataframe['time'])
    dataframe = dataframe.set_index('time')
    dataframe = dataframe.rename(columns={'openMid': 'open', 'highMid': 'high', 'lowMid': 'low', 'closeMid': 'close'})
    USDCAD = bt.feeds.PandasData(dataname=dataframe)  
    
    n_cores = 4
    cash = 10000
    leverage = 20
    init_assets = cash * leverage
    positions = init_assets * 0.02
    
    # Initialize
    cerebro = bt.Cerebro(maxcpus=n_cores)
    
    # Data feed
    cerebro.adddata(AUDUSD, name ="AUDUSD")
    cerebro.adddata(USDCAD, name ="USDCAD")
    
    # Broker
    cerebro.broker.set_cash(init_assets)
    cerebro.broker.setcommission(0.0002)
        
    # Sizer
    
    # Observer
    
    # Analyzer
    cerebro.addanalyzer(bt.analyzers.PyFolio)
    
    # Strategy
    cerebro.addstrategy(MyStrategy)
    
    # Execute
    strats = cerebro.run()
    
    # Report
    cerebro.plot()  
    
    strat0 = strats[0]
    pyfolio = strat0.analyzers.getbyname('pyfolio')
    returns, positions, transactions, gross_lev = pyfolio.get_pf_items()
    # returns.to_csv('D:/Projects/PyQuantTrader/strategies/returns.csv')
    # positions.to_csv('D:/Projects/PyQuantTrader/strategies/positions.csv')
    # transactions.to_csv('D:/Projects/PyQuantTrader/strategies/transactions.csv')
    # gross_lev.to_csv('D:/Projects/PyQuantTrader/strategies/gross_lev.csv')
  
    # print('-- RETURNS')
    # print(returns)
    # print('-- POSITIONS')
    # print(positions)
    # print('-- TRANSACTIONS')
    # print(transactions)
    # print('-- GROSS LEVERAGE')
    print(gross_lev)

    import pyfolio as pf
    # PyFolio and backtrader
    pf.create_round_trip_tear_sheet(returns, positions, transactions)
    benchmark_rets = pd.Series([0.00004] * len(returns.index), index=returns.index)   
    pf.create_full_tear_sheet(returns, positions, transactions, benchmark_rets=benchmark_rets,
                              live_start_date='2017-07-10')

    
    
if __name__ == '__main__':  
    runstrat()
    