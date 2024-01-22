from selenium.common.exceptions import NoSuchElementException
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait

from .crawler_util import *

import pandas as pd
import numpy as np
import argparse
import datetime
import getpass
import hashlib
import pickle
import os
import re
import sys
import tempfile
import time
import locale
locale.setlocale(locale.LC_ALL, 'en_US.UTF8')

# --
# --
# --
URL_PAGE = "https://digital.fidelity.com/ftgw/digital/portfolio/positions"
# --
XP_OVERVIEW_TAB = '//div[@id="posweb-grid_top"]//*[text()="Overview"]'
XP_DIVIDEND_VIEW_TAB = '//div[@id="posweb-grid_top"]//*[text()="Dividend View"]'
XP_REFRESH = '//div[@id="posweb-grid_top"]//button[@aria-label="Refresh Positions"]'
XP_POSITION_TABLE_HEADER = '//div[@id="posweb-grid"]//*[@role="columnheader"]'
XP_POSITION_TABLE_DATA = '//div[@id="posweb-grid"]//*[@role="rowgroup"]/*[@role="row"][@row-index]'
# --
PAGE_STATUS_UNKNOWN = "__PAGE_STATUS_UNKNOWN__"
PAGE_STATUS_OK = "__PAGE_STATUS_OK__"

# --
# --
# --
def goto_page(driver):
	goto_url(driver,URL_PAGE,force=True)

def wait_page_loaded(driver,timeout=10):
	wait_for_clickable_xpath(driver,XP_OVERVIEW_TAB,timeout=timeout)
	wait_for_xpath(driver,XP_POSITION_TABLE_DATA,timeout=timeout)

def page_status(driver):
	cur_tab_ele = driver.find_elements(By.XPATH,XP_OVERVIEW_TAB)
	if(len(cur_tab_ele)>0):
		return PAGE_STATUS_OK
	else:
		return PAGE_STATUS_UNKNOWN

# --
# -- actions
# --
def select_overview_tab(driver):
	orders_tab = driver.find_element(By.XPATH,XP_OVERVIEW_TAB)
	orders_tab.click()

def select_dividend_view_tab(driver):
	orders_tab = driver.find_element(By.XPATH,XP_DIVIDEND_VIEW_TAB)
	orders_tab.click()

def select_refresh_positions(driver):
	orders_tab = driver.find_element(By.XPATH,XP_REFRESH)
	orders_tab.click()

def raw_header(driver):
	headers = []
	for ele in driver.find_elements(By.XPATH,XP_POSITION_TABLE_HEADER):
		headers.append(ele.text)
	return headers

def raw_data(driver,header=None):
	data_eles = driver.find_elements(By.XPATH,XP_POSITION_TABLE_DATA)
	rows = []
	for ele in data_eles:
		rowindex = int(ele.get_attribute("row-index"))
		row = []
		for cell in ele.find_elements(By.XPATH,".//*[@comp-id]"):
			row.append(cell.text)
		if(rowindex>=len(rows)):
			rows.append(row)
		else:
			rows[rowindex] = [ *rows[rowindex], *row ]
	if(header is None):
		return rows
	else:
		df0 = pd.DataFrame(rows)
		df0.columns = header
		return df0

# --
# -- mode dependent
# --
def verify_header_version(h0):
	header_expected = [
		'Symbol', 'Last Price', 'Last Price Change', 
		"$ Today's Gain/Loss", "% Today's Gain/Loss", 
		'$ Total Gain/Loss', '% Total Gain/Loss', 
		'Current Value', '% of Account', 'Quantity', 
		'Average Cost Basis', 'Cost Basis Total', 
		'52-Week Range'
	]
	return h0==header_expected

def expand_position_table(df0):
	dfs = []
	dfs = [
		process_simple_col(df0['Symbol'], header='Symbol,Desc,__IGNORE__'),
		process_simple_col(df0['Last Price'], header='Last Price'),
		process_simple_col(df0['Last Price Change'], header='Price Change'),
		process_simple_col(df0['$ Today\'s Gain/Loss'], header='$ Gain/Loss'),
		process_simple_col(df0['% Today\'s Gain/Loss'], header='% Gain/Loss'),
		process_simple_col(df0['$ Total Gain/Loss'], header='$ Total Gain/Loss'),
		process_simple_col(df0['% Total Gain/Loss'], header='% Total Gain/Loss'),
		process_simple_col(df0['Current Value'], header='Current Value'),
		process_simple_col(df0['% of Account'], header='% of Account'),
		process_simple_col(df0['Quantity'], header='Quantity'),
		process_simple_col(df0['Average Cost Basis'], header='Per Share'),
		process_simple_col(df0['Cost Basis Total'], header='Total Cost,__IGNORE__'),
		process_simple_col(df0['52-Week Range'], header='52w lo,52w hi'),
	]
	df1 = pd.concat(dfs,axis=1)
	df1 = df1[position_row_only(df1)]
	return df1

def position_row_only(df0):
	return df0['% of Account'] !=''

def process_simple_col(series,header=None):
	df0 = pd.DataFrame(series.str.split('\n').tolist())
	if(header is not None):
		if(type(header)==type('')):
			header = header.split(',')
		if(len(header)<len(df0.columns)):
			for nn in range(len(header),len(df0.columns)):
				header.append(f"__UNK_COL__{nn}__")
		elif(len(header)>len(df0.columns)):
			for nn in range(len(df0.columns),len(header)):
				df0[f"nn"] = None
		df0.columns = header
		df0.drop(columns=filter(lambda h: '__' in h, header),inplace=True)
	return df0

# def format_col_with_regex(col_regex,defVal=np.nan):
# 	def ff(col):
# 		if(col is None):
# 			return defVal
# 		matches = col_regex.match(col)
# 		if(matches is None):
# 			return defVal
# 		else:
# 			return matches[1]
# 	return ff

def format_val_remove_char(rm_regex,defVal=np.nan):
	def ff(colval):
		if(colval is None):
			return defVal
		return rm_regex.sub('',colval)
	return ff

def format_col_to_numeric(colval,rm_fn=format_val_remove_char(re.compile('[$,%]'))):
	if(colval is None):
		return np.nan
	if(type(colval)==type(np.nan)):
		return colval
	if('--' in colval):
		return np.nan
	return float( rm_fn(colval) )

def format_position_table(data):
	data = data.copy()
	data.fillna(np.nan,inplace=True)
	data.replace("n/a",np.nan,inplace=True)
	data.replace("--",np.nan,inplace=True)
	data.replace("",np.nan,inplace=True)
	# --
	# !! not using list and loop, because this is easier for debugging !!
	# --
	data['Last Price'] = data['Last Price'].apply(format_col_to_numeric)
	data['Price Change'] = data['Price Change'].apply(format_col_to_numeric)
	data['$ Gain/Loss'] = data['$ Gain/Loss'].apply(format_col_to_numeric)
	data['% Gain/Loss'] = data['% Gain/Loss'].apply(format_col_to_numeric)
	data['$ Total Gain/Loss'] = data['$ Total Gain/Loss'].apply(format_col_to_numeric)
	data['% Total Gain/Loss'] = data['% Total Gain/Loss'].apply(format_col_to_numeric)
	data['Current Value'] = data['Current Value'].apply(format_col_to_numeric)
	data['% of Account'] = data['% of Account'].apply(format_col_to_numeric)
	data['Quantity'] = data['Quantity'].apply(format_col_to_numeric)
	data['Per Share'] = data['Per Share'].apply(format_col_to_numeric)
	data['Total Cost'] = data['Total Cost'].apply(format_col_to_numeric)
	data['52w lo'] = data['52w lo'].apply(format_col_to_numeric)
	data['52w hi'] = data['52w hi'].apply(format_col_to_numeric)
	return data

