#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Created on Sun Jul 23 09:35:03 2017

@author: Ivan Liu
"""

import oandapy

class OandaStreamer(oandapy.Streamer):
    def __init__(self, count=10, *args, **kwargs):
        super(OandaStreamer, self).__init__(*args, **kwargs)
        self.count = count
        self.reccnt = 0

    def on_success(self, data):
        print(data, "\n")
        self.reccnt += 1
        if self.reccnt == self.count:
            self.disconnect()

    def on_error(self, data):
        self.disconnect()
        
        
"""  
import pandas as pd

# Setup account details      
account = "101-011-6029361-001"
access_token="8153764443276ed6230c2d8a95dac609-e9e68019e7c1c51e6f99a755007914f7"
account_type = "practice"

# Register APIs
oanda = oandapy.API(environment=account_type, access_token=access_token)

# Get prices
response = oanda.get_prices(instruments="EUR_USD")
prices = response.get("prices")
asking_price = prices[0].get("ask")

# Get historical prices
hist = oanda.get_history(instrument = "AUD_CAD", granularity = "M5", count = 5000, price = "MBA")
pd.DataFrame(hist['candles']).head()

# Streaming 
stream = OandaStreamer(environment=account_type, access_token=access_token)
stream.rates(account, instruments="EUR_USD,EUR_JPY,US30_USD,DE30_EUR")

"""