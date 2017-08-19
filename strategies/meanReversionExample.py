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
import statsmodels.formula.api as sm
import statsmodels.tsa.stattools as coint

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


# Indicators
class OLS_HedgeRatio(bt.ind.PeriodN):
    '''
    Calculates a linear regression using ``statsmodel.OLS`` (Ordinary least
    squares) of data1 on data0
    Uses ``pandas`` and ``statsmodels``
    '''
    _mindatas = 2  # ensure at least 2 data feeds are passed

    packages = (
        ('pandas', 'pd'),
        ('statsmodels.api', 'sm'),
    )
    lines = ('slope', 'intercept',)
    params = (('period', 10),)

    def next(self):
        p0 = pd.Series(self.data0.get(size=self.p.period))
        p1 = pd.Series(self.data1.get(size=self.p.period))
        p1 = sm.add_constant(p1, prepend=True)
        slope, intercept = sm.OLS(p0, p1).fit().params

        self.lines.slope[0] = slope
        self.lines.intercept[0] = intercept

class OLS_Zscore(bt.ind.PeriodN):
    '''
    Calculates the ``zscore`` for data0 and data1. Although it doesn't directly
    uses any external package it relies on ``OLS_HedgeRatio`` which uses
    ``pandas`` and ``statsmodels``
    '''
    _mindatas = 2  # ensure at least 2 data feeds are passed
    lines = ('spread', 'spread_mean', 'spread_std', 'zscore',)
    params = (('period', 10),)

    def __init__(self):
        slint = OLS_HedgeRatio(*self.datas)

        spread = self.data0 - (slint.slope * self.data1 + slint.intercept)
        self.l.spread = spread

        self.l.spread_mean = bt.ind.SMA(spread, period=self.p.period)
        self.l.spread_std = bt.ind.StdDev(spread, period=self.p.period)
        self.l.zscore = (spread - self.l.spread_mean) / self.l.spread_std

   
# Sizer
class MeanReversionSizer(bt.Sizer):
    '''
    Proportion sizer
    '''
    params = {"prop": 0.05}
 
    def _getsizing(self, comminfo, cash, data, isbuy):
        """Returns the proper sizing"""
        target = self.broker.getvalue() * self.params.prop    # Ideal total value of the position
        price = data.close[0]
        qty = int(target / price)    # The actual number of shares bought
        if qty * price > cash:
            return 0    # Not enough money for this trade
        else:
            return qty
        # return self.broker.getposition(data).size    # Clear the position
        
# Strategy
class MeanReversionSt(bt.Strategy):  
    
    params = dict(
            hold = [120,120],
            lookback = 120,
            zs_thres = 2
            )

    def log(self, txt, dt=None):  
        ''''' Logging function fot this strategy'''  
        dt = dt or self.datas[0].datetime.datetime(0)  
        print('%s, %s' % (dt.isoformat(), txt))  

    def __init__(self):  
        #self.sma1 = bt.indicators.SMA(self.data1.close, period=15)
        
        self.o = dict() # orders per data (main, stop, limit, manual-close)
        self.holding = dict() # holding periods per data
        self.qty = dict() # qty taken per data
        ols_hedge = OLS_HedgeRatio()
        ols_zscore = OLS_Zscore()
        self.hedgeRatio = ols_hedge.lines.slope
        self.zscore = ols_zscore.lines.zscore
        
    def start(self):  
        print("the world call me!")  
  
    def prenext(self):  
        print("not mature")  
  
    def next(self):  
        
        self.log('OLS Hedge Ratio: %.4f | ZScore: %.4f' % (self.hedgeRatio[0], self.zscore[0]))

        for i, d in enumerate(self.datas):
            dt, dn = self.datetime.datetime(), d._name
            pos = self.getposition(d).size
            print('{} {} Position {}'.format(dt, dn, pos))
            
            if self.zscore[0] >= self.p.zs_thres:
                # go Short
                if i == 0:
                    o1 = self.sell(data=d)
                    self.qty[0] = o1.size
                elif i == 1:
                    self.buy(data=d, size=int(self.qty[0]*self.hedgeRatio[0]))
                
            elif self.zscore[0] <= -self.p.zs_thres:
                # go Long
                if i == 0:
                    o1 = self.buy(data=d)
                    self.qty[0] = o1.size
                elif i == 1:
                    self.sell(data=d, size=int(self.qty[0]*self.hedgeRatio[0]))
                self.holding[d] = 0
            elif pos:
                # close postions
                self.holding[d] += 1
                if self.holding[d] >= self.p.hold[i]:
                    self.close(data=d)
                    

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
    cerebro.addsizer(MeanReversionSizer)
    
    # Analyzer
    cerebro.addanalyzer(bt.analyzers.PyFolio)
    
    # Strategy
    cerebro.addstrategy(MeanReversionSt)
    
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
    # print(gross_lev)

    import pyfolio as pf
    # PyFolio and backtrader
    # pf.create_round_trip_tear_sheet(returns, positions, transactions)
    benchmark_rets = pd.Series([0.0004] * len(returns.index), index=returns.index)   
    pf.create_full_tear_sheet(returns, positions, transactions, benchmark_rets=benchmark_rets,
                              live_start_date='2017-07-10')

    
    
if __name__ == '__main__':  
    runstrat()
    