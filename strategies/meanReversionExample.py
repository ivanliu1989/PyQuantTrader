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
    uses any external package it relies on ``OLS_SlopeInterceptN`` which uses
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
    """Proportion sizer"""
    params = {"prop": 0.1}
 
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
            hold = [8,8],
            lookback = 60,
            zs_thres = 2
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
        #self.sma1 = bt.indicators.SMA(self.data1.close, period=15)
        
        self.o = dict() # orders per data (main, stop, limit, manual-close)
        self.holding = dict() # holding periods per data
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
                    self.sell(data=d)
                elif i == 1:
                    self.buy(data=d)
                    
            elif self.zscore[0] <= -self.p.zs_thres:
                # go Long
                if i == 0:
                    self.buy(data=d)
                elif i == 1:
                    self.sell(data=d)
                    
                    
            # elif pos and self.zscore[0] <= -self.p.zs_thres:
            
            
#            if not pos and not self.o.get(d, None):  # no market / no orders
#                self.o[d] = [self.buy(data=d)]
#                print('{} {} Buy {}'.format(dt, dn, self.o[d][0].ref))
#                self.holding[d] = 0
#                
#            elif pos:
#                self.holding[d] += 1
#                if self.holding[d] >= self.p.hold[i]:
#                    o = self.close(data=d)
#                    self.o[d].append(o)  # manual order to list of orders
#                    print('{} {} Manual Close {}'.format(dt, dn, o.ref))


# Run Strategy
def runstrat(args=None):
    
    # Oanda data
    account = "101-011-6029361-001"
    access_token="8153764443276ed6230c2d8a95dac609-e9e68019e7c1c51e6f99a755007914f7"
    account_type = "practice"
    # Register APIs
    oanda = oandapy.API(environment=account_type, access_token=access_token)
    # Get historical prices
    hist = oanda.get_history(instrument = "AUD_USD", granularity = "H1", count = 5000, candleFormat = "midpoint")
    dataframe = pd.DataFrame(hist['candles'])
    dataframe['openinterest'] = 0 
    dataframe = dataframe[['time', 'openMid', 'highMid', 'lowMid', 'closeMid', 'volume', 'openinterest']]
    dataframe['time'] = pd.to_datetime(dataframe['time'])
    dataframe = dataframe.set_index('time')
    dataframe = dataframe.rename(columns={'openMid': 'open', 'highMid': 'high', 'lowMid': 'low', 'closeMid': 'close'})
    AUDUSD = bt.feeds.PandasData(dataname=dataframe)  
    
    hist = oanda.get_history(instrument = "USD_CAD", granularity = "H1", count = 5000, candleFormat = "midpoint")
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
    
    # Observer
    
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
    print(gross_lev)

    import pyfolio as pf
    # PyFolio and backtrader
    pf.create_round_trip_tear_sheet(returns, positions, transactions)
    benchmark_rets = pd.Series([0.00004] * len(returns.index), index=returns.index)   
    pf.create_full_tear_sheet(returns, positions, transactions, benchmark_rets=benchmark_rets,
                              live_start_date='2017-07-10')

    
    
if __name__ == '__main__':  
    runstrat()
    