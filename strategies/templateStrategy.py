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
    
    def log(self, txt, dt=None):  
        ''''' Logging function fot this strategy'''  
        dt = dt or self.datas[0].datetime.date(0)  
        print('%s, %s' % (dt.isoformat(), txt))  

    def __init__(self):  
        #self.AUDUSDclose = self.datas[0].close
        #self.USDCADclose = self.datas[1].close
        self.Spreads = Spreads(self.datas[0], self.datas[1])
        # self.dataclose = self.datas[0].close
        #self.sma1 = bt.indicators.SMA(self.data1.close, period=15)
        
    def start(self):  
        print("the world call me!")  
  
    def prenext(self):  
        print("not mature")  
  
    def next(self):  
        self.log('Spreads, %.10f' % self.Spreads[0])  
        #self.log('BUY CREATE, %.2f' % self.sma1[0])  
    
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
    
    
    # Strategy
    cerebro.addstrategy(MyStrategy)
    
    # Execute
    cerebro.run()
    
    
    
    
if __name__ == '__main__':  
    runstrat()
    