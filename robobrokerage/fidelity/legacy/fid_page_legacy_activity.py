from selenium.common.exceptions import NoSuchElementException
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait

from ..crawler_util import *
# from .fid_common import *

import pandas as pd
import numpy as np
import argparse
import datetime
import getpass
import hashlib
import pickle
import os
import sys
import tempfile
import time
import locale
locale.setlocale(locale.LC_ALL, 'en_US.UTF8')

# --
# --
# --
URL_PAGE = "https://oltx.fidelity.com/ftgw/fbc/oftop/portfolio#activity"
# --
XPATH_PROGRESS_POPUP = '/html/body/div[@class="progress-bar bordered"][@style="display: none;"]'
XP_ORDER_TAB = '//span[text()="Orders"]'
XP_HISTORY_TAB = '//span[text()="History"]'
XP_DATE_OPTIONS = '//*[@id="activity--history-range-dropdown"]//option'
XP_EXPAND_ALL_BTN = '//*[@id="tabContentActivity"]//a'
XP_VIEW_ALL_TXN_BTN = '//a[text()="View All Transactions"]'
XP_HISTORY_CONTENT = '//*[@id="historyExpanderContent"]//img[@alt="Close Popup"]/../../../../../../tr/td'
XP_ORDERS_BODY = '//div[@orders="orders"]//tbody/tr'
# --
PAGE_STATUS_UNKNOWN = "__PAGE_STATUS_UNKNOWN__"
PAGE_STATUS_OK = "__PAGE_STATUS_OK__"

# --
# --
# --
def goto_page(driver):
	goto_url(driver,URL_PAGE,force=True)

def wait_page_loaded(driver,timeout=10):
	expected_cond = EC.presence_of_element_located((
		By.XPATH,
		XPATH_PROGRESS_POPUP
	))
	block_popup = WebDriverWait(driver, timeout).until(expected_cond)
	time.sleep(5)
	return block_popup

def page_status(driver):
	cur_tab_ele = driver.find_elements(By.XPATH,XP_DATE_OPTIONS)
	if(len(cur_tab_ele)>0):
		return PAGE_STATUS_OK
	else:
		return PAGE_STATUS_UNKNOWN

# --
# -- actions
# --
def select_orders_tab(driver):
	orders_tab = driver.find_element(By.XPATH,XP_ORDER_TAB)
	orders_tab.click()

def select_history_tab(driver):
	history_tab = driver.find_element(By.XPATH,XP_HISTORY_TAB)
	history_tab.click()

def select_date_filter(driver,days_opt):
	click_partial_match(driver,XP_DATE_OPTIONS,days_opt)

def expand_all(driver):
	click(driver,XP_EXPAND_ALL_BTN,"Expand all")

def collapse_all(driver):
	click(driver,XP_EXPAND_ALL_BTN,"Collapse all")

def view_all_txns(driver):
	click(driver,XP_VIEW_ALL_TXN_BTN,"View All Transactions")

def get_transactions(driver):
	all_lines = [ ele.text for ele in driver.find_elements_by_xpath(XP_HISTORY_CONTENT)]
	return all_lines

def raw_transactions(driver):
	view_all_txns(driver)
	wait_page_loaded(driver)
	expand_all(driver)
	wait_page_loaded(driver)
	# --
	all_lines = get_transactions(driver)
	raw_txn = pd.DataFrame(
		np.array(all_lines).reshape((-1,5)), 
		columns=['Date','Description','Amount','Cash Balance', 'Details'] 
	)
	return raw_txn

def raw_orders(driver):
	collapse_all(driver)
	orders = []
	for order in driver.find_elements(By.XPATH, XP_ORDERS_BODY):
		if(len(order.text)>=10):
			order1 = []
			for cell in order.find_elements(By.XPATH, "./td"):
				order1.append(cell.text)
			orders.append(order1)
	return pd.DataFrame(orders,columns=["Date","Account","Description","Status","Amount"])

def raw_orders_with_details(driver):
	# --
	def try_break_field_with_key(field,key):
		if(field.startswith(key)):
			key_len = len(key)
			return field[key_len:].strip()
		return None
	# --
	def process_order(order):
		data = {}
		lines = order.split("\n")
		if(len(lines)<=2):
			return None
		for line in lines:
			for key in ("Order Number","Status","Symbol","Quantity","Order Type","Order Date","Cancel Date"):
				field = try_break_field_with_key(line,key)
				if(field is None):
					continue
				data[key] = field
				break
		if("Order Number" in data and "Symbol" in data):
			return data
		else:
			return None
	# --
	expand_all(driver)
	orders = []
	for order in driver.find_elements(By.XPATH, XP_ORDERS_BODY):
		order_text = order.text
		data = process_order(order_text)
		if(data is not None):
			orders.append(data)
	return pd.DataFrame(orders)

# --
# -- methods
# --
def formatted_transactions(raw_txns):
	# --
	# --
	# --
	def line_processor(line):
		fields = line.split('\n')
		# --
		# -- normalize all row return the same fields (error prevention)
		# --
		r_map = { 'Symbol':None, 'Shares':None, 'Price':None, 'Amount':None, 'Settlement':None }
		for f in fields[1:]:
			ww = f.split()
			if(ww[0] in r_map):
				r_map[ww[0]] = ww[-1]
		r_map['Description'] = fields[0]
		return r_map
	# --
	# --
	# --
	def categorize_transaction(df0):
		category = pd.Series(index=df0.index,dtype=str)
		category.loc[:] = 'UNK'
		category.loc[history['Description'].str.contains('DIVIDEND')] = "DIVIDEND"
		category.loc[history['Description'].str.contains('TRANSFER')] = "TRANSFER"
		category.loc[history['Description'].str.contains('REINVEST')] = "SWEEP"
		category.loc[history['Description'].str.contains('BOUGHT')] = "BUY"
		category.loc[history['Description'].str.contains('SOLD')] = "SELL"
		category.loc[history['Description'].str.contains('ASSIGNED')] = "ASSIGNMENT"
		category.loc[history['Description'].str.contains('EXPIRED')] = "EXPIRED"
		category.loc[history['Description'].str.contains('INTEREST')] = "INTEREST"
		category.loc[history['Description'].str.contains('REDEMPTION')] = "REDEMPTION"
		return category
	# --
	# -- code not optimize for speed, just simplicity
	# --
	details = map(line_processor, raw_txns['Details'].to_list() )
	details = pd.DataFrame(details).drop(columns=['Description','Amount'])
	history = pd.concat([raw_txns,details],axis=1).drop(columns="Details")
	# --
	history['Amount'] = history['Amount'].replace("--", "0").replace("[$,]","",regex=True).astype(float)
	history['Shares'] = history['Shares'].replace("[$,]","",regex=True).astype(float)
	history['Price'] = history['Price'].replace("[$,]","",regex=True).astype(float)
	history['Date'] = history['Date'].astype('datetime64[ns]')
	history['Settlement'] = history['Settlement'].astype('datetime64[ns]')
	# --
	history['Type'] = categorize_transaction(history)
	history = history['Type,Date,Symbol,Shares,Price,Amount,Settlement,Description'.split(',')]
	# --
	return history

