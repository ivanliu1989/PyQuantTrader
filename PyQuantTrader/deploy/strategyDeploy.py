# -*- coding: utf-8 -*-
"""
Created on Mon Aug 21 22:23:06 2017

@author: sky_x
"""

import os

def deployStrategy(file_path = "./strategies/testStrategy/"):
	
	directory = os.path.dirname(file_path)

	try:
		os.stat(directory)
	except:
		os.mkdir(directory)
		os.mkdir(directory + '/data/')
		os.mkdir(directory + '/performance/')
		os.mkdir(directory + '/strategy/')  
		os.mkdir(directory + '/meta/')    
