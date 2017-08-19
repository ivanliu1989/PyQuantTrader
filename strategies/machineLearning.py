# -*- coding: utf-8 -*-
"""
Created on Sat Aug 19 11:06:44 2017

@author: Ivan Liu
"""


import pandas as pd
from pandas import DataFrame
import random
from copy import deepcopy
import math
import numpy as np

# Backtrader
import backtrader as bt
from backtrader.indicators import EMA

# PyQuantTrader
from PyQuantTrader import strategy as pqt_strategy
from PyQuantTrader import validation as pqt_val
from PyQuantTrader import analyzers as pqt_ana
from PyQuantTrader import indicators as pqt_ind
from PyQuantTrader import observers as pqt_obs
from PyQuantTrader import sizers as pqt_sizers

# OandaAPI
import oandapy

# Keras
from keras.layers.core import Dense, Activation, Dropout
from keras.layers.recurrent import LSTM
from keras.models import Sequential

def load_data(data, seq_len, normalise_window):
    
    sequence_length = seq_len + 1
    result = []
    for index in range(len(data) - sequence_length):
        result.append(data[index: index + sequence_length])
    
    if normalise_window:
        result = normalise_windows(result)

    result = np.array(result)

    row = round(0.9 * result.shape[0])
    train = result[:int(row), :]
    np.random.shuffle(train)
    x_train = train[:, :-1]
    y_train = train[:, -1]
    x_test = result[int(row):, :-1]
    y_test = result[int(row):, -1]

    x_train = np.reshape(x_train, (x_train.shape[0], x_train.shape[1], 1))
    x_test = np.reshape(x_test, (x_test.shape[0], x_test.shape[1], 1))  

    return [x_train, y_train, x_test, y_test]

def normalise_windows(window_data):
    normalised_data = []
    for window in window_data:
        normalised_window = [((float(p) / float(window[0])) - 1) for p in window]
        normalised_data.append(normalised_window)
    return normalised_data

def build_model(layers, dropout):
    model = Sequential()

    model.add(LSTM(
        input_dim=layers[0],
        output_dim=layers[1],
        return_sequences=True))
    model.add(Dropout(dropout))

    model.add(LSTM(
        layers[2],
        return_sequences=False))
    model.add(Dropout(dropout))

    model.add(Dense(
        output_dim=layers[3]))
    model.add(Activation("linear"))

    model.compile(loss="mse", optimizer="rmsprop")
    return model

def predict_point_by_point(model, data):
    #Predict each timestep given the last sequence of true data, in effect only predicting 1 step ahead each time
    predicted = model.predict(data)
    predicted = np.reshape(predicted, (predicted.size,))
    return predicted


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

    def log(self, txt, dt=None):  
        ''''' Logging function fot this strategy'''  
        dt = dt or self.datas[0].datetime.datetime(0)  
        print('%s, %s' % (dt.isoformat(), txt))  

    def __init__(self):  
        lstmInd = MachineLearningInd()
        self.lstmPred = lstmInd.lines.lstmPred
        
    def start(self):  
        print("the world call me!")  
  
    def prenext(self):  
        print("not mature")  
  
    def next(self):  
        
        for i, d in enumerate(self.datas):
            
            if self.lstmPred[0] > 0:
                # go Short
                if i == 0:
                    self.buy(data=d)
                elif i == 1:
                    self.sell(data=d)
                
            elif self.lstmPred[0] < 0:
                # go Long
                if i == 0:
                    self.sell(data=d)
                elif i == 1:
                    self.buy(data=d)
                    
        self.log('LSTM: %.4f' % (self.lstmPred[0]))


class MachineLearningInd(bt.ind.PeriodN):
    
    _mindatas = 2
    
    packages = (('pandas','pd'),
                ('numpy','np'),
                ('sklearn', 'sk'),
                ('statsmodels.api', 'sm'),
                )
    lines = ('lstmPred',)
    
    params = dict(
            lookbacks = 4800,
            seq_len = 50,
            normalise_window = True,
            batch_size = 64,
            epochs = 2,
            validation_split = 0.25,
            dropout = 0.1,
            nodes = 25,
            )
    def __init__(self):
        self.addminperiod(self.params.lookbacks)
        
    def next(self):
        p0 = np.array(self.data0.get(size=self.p.lookbacks))
        p1 = np.array(self.data1.get(size=self.p.lookbacks))
        
        data = p0-p1

        X_train, y_train, X_test, y_test = load_data(data, self.p.seq_len, self.p.normalise_window)
        
        model = build_model([1, self.p.nodes, self.p.nodes, 1], self.p.dropout)
        model.fit(
                 X_train,
                 y_train,
                 batch_size=self.p.batch_size,
                 nb_epoch=self.p.epochs,
                 validation_split=self.p.validation_split)
        predictions = predict_point_by_point(model, X_test)        

        self.lines.lstmPred[0] = predictions[-1]

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
    
    n_cores = 6
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
    # cerebro.addsizer(KalmanFilterSizer)
    
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
    