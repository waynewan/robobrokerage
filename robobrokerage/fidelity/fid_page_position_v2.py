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
# -- rm -- XP_OVERVIEW_TAB = '//div[@id="posweb-grid_top"]//*[text()="Overview"]'
XP_OVERVIEW_TAB = '//option[text()="Overview"]'
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
	return "Last Price Change" not in h0

def expand_position_table(df0):
	dfs = []
	dfs = [
		process_simple_col(df0['Symbol'], header='Symbol,Desc,__IGNORE__'),
		process_simple_col(df0['Last Price'], header='Last Price,Price Change'),
		process_simple_col(df0['Today\'s Gain/Loss'], header='$ Gain/Loss,% Gain/Loss'),
		process_simple_col(df0['Total Gain/Loss'], header='$ Total Gain/Loss,% Total Gain/Loss'),
		process_simple_col(df0['Current Value'], header='Current Value'),
		process_simple_col(df0['% of Account'], header='% of Account'),
		process_simple_col(df0['Quantity'], header='Quantity'),
		process_cost_basis_col(df0['Cost Basis']),
		process_simple_col(df0['52-Week Range'], header='52w lo,52w hi'),
	]
	df1 = pd.concat(dfs,axis=1)
	df1.drop(columns=['__IGNORE__'],inplace=True)
	return df1

def process_simple_col(series,header=None):
	df0 = pd.DataFrame(series.str.split('\n').tolist())
	if(header is not None):
		if(type(header)==type('')):
			header = header.split(',')
		df0.columns = header
	return df0

def process_cost_basis_col(series):
	df0 = pd.DataFrame(series.str.split('\n').tolist())
	if(len(df0.columns)>=3):
		df0.iloc[df0[2].isnull(),2] = df0[df0[2].isnull()][1]
		df0.drop(columns=[1],inplace=True)
	df0.columns = ['Total Cost','Per Share']
	return df0
	
# --
# -- REMOVE
# --
def expand_header(h0):
	# ['Symbol', 'Last Price', 'Last Price Change', "$ Today's Gain/Loss", "% Today's Gain/Loss", '$ Total Gain/Loss', '% Total Gain/Loss', 'Current Value', '% of Account', 'Quantity', 'Average Cost Basis', 'Cost Basis Total', '52-Week Range']
	# ['Symbol', 'Desc', 'Last Price', 'Last Price Change', 'Today P&L', 'Today P&L%', 'Total P&L', 'Total P&L%', 'Current Value', '% of Account', 'Quantity', 'Total Cost', 'Per Share', '52w Lo', '52w Hi']
	header_expand_map = {
		'Symbol' : ['Symbol','Desc','Desc_ex'],
		"$ Today's Gain/Loss" : ['Today P&L'],
		"% Today's Gain/Loss" : ['Today %Chg'],
		"$ Total Gain/Loss" : ['Total P&L'],
		"% Total Gain/Loss" : ['Total %Chg'],
		'Average Cost Basis' : ['Per Share'],
		'Cost Basis Total' : ['Total Cost'],
		'52-Week Range' : ['52w Lo','52w Hi'],
	}
	h1 = []
	for header in h0:
		new_header = header_expand_map.get(header,[header])
		h1 = [ *h1, *new_header ]
	return h1

def format_col_with_regex(col_regex,defVal=np.nan):
	def ff(col):
		if(col is None):
			return defVal
		matches = col_regex.match(col)
		if(matches is None):
			return defVal
		else:
			return matches[1]
	return ff

def format_col_remove_char(rm_regex,defVal=np.nan):
	def ff(colval):
		if(colval is None):
			return defVal
		return rm_regex.sub('',colval)
	return ff

def format_col_norm_numeric(colval,rm_fn=format_col_remove_char(re.compile('[$,%]'))):
	if(colval is None):
		return np.nan
	if('--' in colval):
		return np.nan
	return float( rm_fn(colval) )

def formatted_position_table(header,data,parse_col=True):
	expanded_header = expand_header(header)
	# --
	# -- combine expand tab separated data into one DataFrame
	# --
	df0 = pd.DataFrame(data)
	df1 = pd.concat([
		pd.DataFrame(df0[1].str.split('\n').tolist()), #.iloc[:,:-1],
		pd.DataFrame(df0[3].str.split('\n').tolist()), #.iloc[:,:-1],
	],axis=1)
	if(len(expanded_header)==len(df1.columns)):
		df1.columns = expanded_header
	else:
		return (expanded_header,df1)
	# --
	# -- 52wk range is not necessary, and difficult to process, drop it
	# --
	df1.drop(columns=['52w Lo','52w Hi'],inplace=True)
	# --
	# -- remove non position artifact
	# --
	df1 = df1[~df1['% of Account'].isna()]
	df1.replace("n/a",None,inplace=True)
	col_lst_1 = ['Last Price','Last Price Change','Current Value','% of Account','Quantity']
	col_lst_2 = ['Today P&L','Today %Chg','Total P&L','Total %Chg','Total Cost','Per Share']
	if(parse_col):
		for colname in [ *col_lst_1, *col_lst_2 ]:
			df1[colname] = df1[colname].apply(format_col_norm_numeric)
	# --
	# --
	# --
	return df1

