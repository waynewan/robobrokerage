from selenium.common.exceptions import NoSuchElementException
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import StaleElementReferenceException

from .crawler_util import *
from jackutil.microfunc import retry

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
import re
from tqdm.auto import tqdm
import locale
locale.setlocale(locale.LC_ALL, 'en_US.UTF8')

# --
# --
# --
URL_PAGE = "https://digital.fidelity.com/ftgw/digital/portfolio/activity"
# --
# -- rm on 20240307 -- XP_REFRESH_BTN = '//pvd3-link[@pvd-aria-label="Refresh"]'
# -- rm on 20240424 -- XP_REFRESH_BTN = '//button[@aria-label="Refresh"]'
# -- rm on 20250930 -- XP_DATE_SELECTOR_DD = "//button[@id='timeperiod-select-button']"
XP_DATE_SELECTOR_DD = "//timeperiod-filter//button"
XP_DATE_SELECTOR_OPT = "//div[@id='timeperiod-select-container']//input/.."
XP_DATE_SELECTOR_APPLY = "//div[@id='timeperiod-select-container']//*[normalize-space(text())='Apply']"
XP_LEGACY_PAGE_BTN = "//a[text()='legacy portfolio activity page']"
# -- rm on 20250930 -- XP_FILTER_OPTIONS = '//core-filter-button//button'
XP_FILTER_OPTIONS = '//div[@class="activity-order-menu-area"]//activity-order-filter-button//button'
XP_FILTER_OPT_BTN = './s-root/div/label'
XP_BTN = '//button'
XP_ACTIVITY_ROW = '//activity-list//div[@role="row"][1]'
XP_ACTIVITY_ROW_2 = '//activity-list//div[@role="row"][2]'
XP_ACTIVITY_DETAILS = '//activity-order-detail-panel'
XP_ACT_EXPANDED = ".//div[@aria-label='show info'][@aria-expanded='true']"
XP_ACT_COLLAPSED = ".//div[@role='button'][@aria-expanded='false']"
XP_INPUT_FROM_DATE = "//input[@label='From Date']"
XP_INPUT__TO__DATE = "//input[@label='To Date']"
# --
PAGE_STATUS_UNKNOWN = "__PAGE_STATUS_UNKNOWN__"
PAGE_STATUS_OK = "__PAGE_STATUS_OK__"

# --
# --
# --
def goto_page(driver):
	goto_url(driver,URL_PAGE,force=True)

def wait_page_loaded(driver,timeout=10):
	wait_for_clickable_xpath(driver,XP_DATE_SELECTOR_DD,timeout=timeout)

def page_status(driver):
	cur_tab_ele = driver.find_elements(By.XPATH,XP_DATE_SELECTOR_DD)
	if(len(cur_tab_ele)>0):
		return PAGE_STATUS_OK
	else:
		return PAGE_STATUS_UNKNOWN

# --
# -- actions
# --
def select_date_filter_custom(driver,fromdate,todate):
	inp_from_date = driver.find_element(By.XPATH,XP_INPUT_FROM_DATE)
	inp_from_date.clear()
	inp_from_date.send_keys(fromdate)
	# --
	inp__to__date = driver.find_element(By.XPATH,XP_INPUT__TO__DATE)
	inp__to__date.clear()
	inp__to__date.send_keys(todate)
#	# --
#	apply_btn = driver.find_element(By.XPATH,XP_DATE_SELECTOR_APPLY)
#	apply_btn.click()
#	return True

# --
# -- fromdate,todate: mm/dd/yyyy
# --
def select_date_filter(driver,days_opt):
	fromdate,todate = ( None,None )
	if(days_opt.startswith("Custom")):
		days_opt,fromdate,todate = days_opt.split(",")
	# --
	# -- click date filter to show options
	# --
	date_filter_dd = wait_for_clickable_xpath(driver,XP_DATE_SELECTOR_DD,timeout=10)
	date_filter_dd.click()
	# --
	# -- select the option that match the partial text days_opt
	# --
	options = date_filter_dd.find_elements(By.XPATH,XP_DATE_SELECTOR_OPT)
	for option in options:
		option_text = option.text
		if(days_opt.upper() in option_text.upper()):
			option.click()
			# --
			if(days_opt=="Custom"):
				select_date_filter_custom(driver,fromdate,todate)
			# --
			# -- click APPLY to activate the filtering
			# --
			apply_btn = driver.find_element(By.XPATH,XP_DATE_SELECTOR_APPLY)
			apply_btn.click()
			# --
			return option_text
	# --
	# -- nothing match, close the drop-down
	# --
	date_filter_dd = driver.find_element(By.XPATH,XP_DATE_SELECTOR_DD)
	date_filter_dd.click()
	return False

def goto_legacy(driver):
	try:
		legacy_btn = driver.find_element(By.XPATH,XP_LEGACY_PAGE_BTN)
		legacy_btn.click()
		return True
	except:
		return False

# --
# -- utility
# --
def __ut_switch_option_to(ele,new_state):
	pressed_state = ele.get_attribute("aria-pressed")
	if(pressed_state is None):
		return None
	pressed = pressed_state.upper()=="TRUE"
	want_on = new_state.upper()=="ON"
	if(want_on != pressed):
		ele.click()
		return True
	return False

def ut_switch_option_to(ele,new_state):
	for ii in range(0,15):
		pressed = __ut_switch_option_to(ele,new_state)
		if(not pressed):
			break
		time.sleep(1.0)
	return ele.get_attribute("aria-pressed")

def ut_is_stale(ele):
	try:
		return ele.text
	except (StaleElementReferenceException,NoSuchElementException) as ex:
		return None

txn_type_map = {
	'DIVIDEND' : 'DIV',
	'FOREIGN TAX' : 'F_TAX',
	'FEE CHARGED' : 'FEE',
}
def txn_category(desc):
	if(desc.find('DIVIDEND')>=0):
		if(desc.find('XX)')>=0):
			return "INTEREST"
		else:
			return txn_type_map["DIVIDEND"]
	if(desc.find('FEE CHARGED')>=0):
		return txn_type_map["FEE CHARGED"]
	if(desc.find('FOREIGN TAX')>=0):
		return txn_type_map["FOREIGN TAX"]
	if(desc.find('TRANSFER')>=0):
		return "TRANSFER"
	if(desc.find('REINVEST')>=0):
		return "SWEEP"
	if(desc.find('BOUGHT')>=0):
		return "BUY"
	if(desc.find('SOLD')>=0):
		return "SELL"
	if(desc.find('ASSIGNED')>=0):
		return "ASSIGNMENT"
	if(desc.find('EXPIRED')>=0):
		return "EXPIRED"
	if(desc.find('INTEREST')>=0):
		return "INTEREST"
	if(desc.find('REDEMPTION')>=0):
		return "REDEMPTION"
	return 'UNK'

def txn_symbol(desc):
	symbol_capturer = re.compile(".* +(.*) +\(Cash\)")
	matches = symbol_capturer.match(desc)
	if(matches is None):
		return f'NO_MATCH_ERR:{desc}'
	symbol = matches[1]
	symbol = symbol.replace('(','').replace(')','')
	return symbol

# --
# -- actions
# --
def select_history_only(driver):
	eles = driver.find_elements(By.XPATH,XP_FILTER_OPTIONS)
	for ele in eles:
		ele_txt = ut_is_stale(ele)
		if(ele_txt is None):
			continue
		if(ele_txt.find("History")>=0):
			new_state = ut_switch_option_to(ele, "on")
		else:
			new_state = ut_switch_option_to(ele, "off")

def select_orders_only(driver):
	eles = driver.find_elements(By.XPATH,XP_FILTER_OPTIONS)
	for ele in eles:
		ele_txt = ut_is_stale(ele)
		if(ele_txt is None):
			continue
		if(ele_txt.find("Orders")>=0):
			new_state = ut_switch_option_to(ele, "on")
		else:
			new_state = ut_switch_option_to(ele, "off")

def view_all_txns(driver):
	err_msg = "No 'Load more results' button"
	def ftr():
		result = click(driver,XP_BTN,"Load more results")
		if(result is None):
			raise ValueError(err_msg)
	_,errors = retry(ftr,retry=10,exceptTypes=(ValueError,StaleElementReferenceException),rtnEx=True,silent=True)
	err = errors[-1]
	if(type(err)==type(ValueError()) and str(err)==err_msg):
		return
	else:
		raise err

def expand_all(driver):
	eles = driver.find_elements(By.XPATH,XP_ACTIVITY_ROW)
	eles.reverse()
	for ele in eles:
		try:
			# subele = ele.find_elements(By.XPATH,".//div[@aria-label='show info'][@aria-expanded='false']")
			subele = ele.find_elements(By.XPATH,XP_ACT_COLLAPSED)
			if(len(subele)>0):
				ele.click()
		except:
			pass

def collapse_all(driver):
	eles = driver.find_elements(By.XPATH,XP_ACTIVITY_ROW)
	for ele in eles:
		try:
			# subele = ele.find_elements(By.XPATH,".//div[@aria-label='show info'][@aria-expanded='true']")
			subele = ele.find_elements(By.XPATH,XP_ACT_EXPANDED)
			if(len(subele)>0):
				ele.click()
		except:
			pass

def raw_transactions(driver,incl_details=True):
	def ftr():
		return __impl_raw_transactions(driver,incl_details=incl_details)
	return retry(ftr,retry=10,exceptTypes=(StaleElementReferenceException),rtnEx=False,silent=True)

def __impl_raw_transactions(driver,incl_details=True):
	# --
	# -- expand the list if "Load more results" is found
	# --
	view_all_txns(driver)
	# --
	if(incl_details):
		expand_all(driver)
	# --
	def process_order(order):
		data = {}
		lines = order.split("\n")
		if(len(lines)<=2):
			return None
		keys = lines[0::2]
		values = lines[1::2]
		for key,val in zip(keys,values):
			if(key=='Symbol Desc.'):
				continue
			data[key] = val
		if("Date" in data):
			return data
		else:
			return None
		# --
		# -- data from details panels
		# --
	def find_detail_panel(order):
		# print("trying before 20250321 version")
		details = order.find_elements(By.XPATH, "..//activity-order-detail-panel")
		if(len(details)==1):
			return details
		# --
		# print("trying @ 20250321 version")
		details = order.find_elements(By.XPATH, "..//activity-order-detail-panel-ui")
		if(len(details)==1):
			return details
		# --
		return []
	# --
	screen_row = driver.find_elements(By.XPATH, XP_ACTIVITY_ROW)
	# --
	orders = []
	for order in tqdm(screen_row,leave=None,desc="txns"):
		order1 = {}
		# --
		# -- data from single line entry
		# --
		# -- rm -- cells = order.find_elements(By.XPATH, "./div[@role='cell']")
		cells = order.find_elements(By.XPATH, "./div[@role='cell' or @role='rowheader']")
		if(len(cells)<=3):
			# -- DEBUG --
			# header = "^".join([ cc.text for cc in cells if(cc is not None) ])
			# print("header:",header)
			continue
		order1['Date'] = cells[1].text
		order1['Description'] = cells[2].text
		order1['Symbol'] = None
		if(order1['Description'] is not None):
			order1['Type'] = txn_category(order1['Description'])
			order1['Symbol'] = txn_symbol(order1['Description'])
		order1['Amount'] = cells[3].text
		order1['Balance'] = cells[4].text
		order1['Details'] = ""
		order1['Price'] = ""
		order1['Shares'] = ""
		order1['Settlement Date'] = ""
		# --
		# --
		# --
		if(incl_details):
			details = find_detail_panel(order)
			if(len(details) !=1):
				continue
			details_text = details[0].text
			details_data = process_order(details_text)
			order1.update(details_data)
		orders.append(order1)
	df0 = pd.DataFrame(orders)
	# --
	# -- cleanup and sort
	# --
	df0 = df0.replace("",None)
	non_empty_row = ~df0.isnull().all(axis=1)
	return df0[non_empty_row].sort_values(by=["Date","Symbol"],ascending=[True,True]).reset_index(drop=True)

def formatted_transactions(raw_txns):
	# --
	# -- code not optimize for speed, just simplicity
	# --
	formatted = raw_txns.copy()
	formatted.rename(columns = { 'Settlement Date':'Settlement' },inplace=True)
	formatted['Type'] = raw_txns['Description'].apply(txn_category)
	# --
	formatted['Amount'] = formatted['Amount'].replace("--", "0").replace("[$,]","",regex=True).astype(float)
	formatted['Shares'] = formatted['Shares'].replace("[$,]","",regex=True).astype(float)
	formatted['Price'] = formatted['Price'].replace("[$,]","",regex=True).astype(float)
	formatted['Date'] = formatted['Date'].astype('datetime64[ns]')
	formatted['Settlement'] = formatted['Settlement'].astype('datetime64[ns]')
	# --
	formatted = formatted['Type,Date,Symbol,Shares,Price,Amount,Settlement,Description'.split(',')]
	# --
	return formatted 

