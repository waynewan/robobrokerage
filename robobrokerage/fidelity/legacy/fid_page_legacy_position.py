from selenium.common.exceptions import NoSuchElementException
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait

from ..crawler_util import *

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
URL_PAGE = "https://oltx.fidelity.com/ftgw/fbc/oftop/portfolio#positions"
# --
XPATH_PROGRESS_POPUP = '/html/body/div[@class="progress-bar bordered"][@style="display: none;"]'
XP_OVERVIEW_TAB = '//div[@id="posweb-grid_top"]//*[text()="Overview"]'
XP_DIVIDEND_VIEW_TAB = '//div[@id="posweb-grid_top"]//*[text()="Dividend View"]'
XP_REFRESH = '//div[@id="posweb-grid_top"]//button[@aria-label="Refresh Positions"]'
XP_REFRESH_SPINNER = '//*[@id="posweb-spinner"]'
XP_POSITION_TABLE_HEADER = '//div[@id="posweb-grid"]//*[@role="columnheader"]'
XP_POSITION_TABLE_DATA = '//div[@id="posweb-grid"]//*[@role="rowgroup"]/*[@role="row"][@row-index]'




XP_ORDER_TAB = '//span[text()="Orders"]'
XP_HISTORY_TAB = '//span[text()="History"]'
XP_DATE_OPTIONS = '//*[@id="activity--history-range-dropdown"]//option'
XP_EXPAND_ALL_BTN = '//*[@id="historyExpanderContent"]//a'
XP_VIEW_ALL_TXN_BTN = '//a[text()="View All Transactions"]'
XPATH_HISTORY_CONTENT = '//*[@id="historyExpanderContent"]//img[@alt="Close Popup"]/../../../../../../tr/td'
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
	return block_popup

def wait_page_view_change(driver,timeout=3):
	time.sleep(timeout)

# --
# -- actions
# --
def select_overview_tab(driver):
	orders_tab = driver.find_element(By.XPATH,XP_OVERVIEW_TAB)
	orders_tab.click()

def select_dividend_view_tab(driver):
	orders_tab = driver.find_element(By.XPATH,XP_DIVIDEND_VIEW_TAB)
	orders_tab.click()

def select_refresh(driver):
	orders_tab = driver.find_element(By.XPATH,XP_REFRESH)
	orders_tab.click()

def raw_header(driver):
	headers = []
	for ele in driver.find_elements(By.XPATH,XP_POSITION_TABLE_HEADER):
		headers.append(ele.text)
	return headers

def raw_data(driver):
	data_eles = driver.find_elements(By.XPATH,XP_POSITION_TABLE_DATA)
	rows = []
	for ele in data_eles:
		rowindex = int(ele.get_attribute("row-index"))
		if(rowindex>=len(rows)):
			row = []
			rows.append(row)
			row.append(rowindex)
			row.append(ele.text)
		else:
			row = rows[rowindex]
			row.append("##")
			row.append(ele.text)
	# rows = rows[1:]	
	return rows

def formatted_position_table(header,data):
	df = pd.DataFrame(data=data)[1:]
	desc = pd.DataFrame(data=df[1].str.split("\n").tolist())
	desc.columns = ['Symbol','Desc1','Desc2']
	data = pd.DataFrame(data=df[3].str.split("\n").tolist()).iloc[:,0:11]
	data.columns = header[1:-1]
	data.replace("n/a", np.nan, inplace=True)
	data.replace("--", np.nan, inplace=True)
	pos_table = pd.concat([desc,data],axis=1)
	pos_table = pos_table[0:-2]
	# --
	pos_table['Last Price'] = pos_table['Last Price'].replace("[$,]","",regex=True).astype(float)
	pos_table['Last Price Change'] = pos_table['Last Price Change'].replace("[$,]","",regex=True).astype(float)
	pos_table['Quantity'] = pos_table['Quantity'].replace("[$,]","",regex=True).astype(float)
	pos_table['Cost Basis Total'] = pos_table['Cost Basis Total'].replace("[$,]","",regex=True).astype(float)
	pos_table['Average Cost Basis'] = pos_table['Average Cost Basis'].replace("[$,]","",regex=True).astype(float)
	pos_table['Current Value'] = pos_table['Current Value'].replace("[$,]","",regex=True).astype(float)
	pos_table["$ Today's Gain/Loss"] = pos_table["$ Today's Gain/Loss"].replace("[$,]","",regex=True).astype(float)
	pos_table['$ Total Gain/Loss'] = pos_table['$ Total Gain/Loss'].replace("[$,]","",regex=True).astype(float)
	return pos_table

