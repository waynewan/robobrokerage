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
import re
import os
import sys
import tempfile
import time
import locale
locale.setlocale(locale.LC_ALL, 'en_US.UTF8')

# --
# --
# --
URL_PAGE = "https://digital.fidelity.com/ftgw/digital/trade-equity/index/orderEntry"
URL_PAGE_PARAM = 'https://brokerage.fidelity.com/ftgw/brkg/equityticket/index?SECURITY_ID={}&WSATTR=cssnapshot'
# --
XP_REFRESH_BTN = '//pvd3-button[@id="eq-ticket__balance-refresh-icon-a"]'
XP_PREVIEW_BTN = "//div/order-entry-base//*[@id='previewOrderBtn']"
XP_PLACE_ORDER_BTN = '//*[@id="placeOrderBtn"]'
XP_NEW_ORDER_BTN = '//*[@id="Enter_order_button"]'
XP_PREVIEW_ORDER = '//preview//div[@id]/../../..'
XP_RECEIVED_ORDER = '//order-received'
XP_PREVIEW_EST_COST = '//div/order-entry-base//commission'
XP_PREVIEW_WARNING = '//warning-messages'
XP_PREVIEW_ERROR = '//*[text()[contains(.,"Error")]]/../../../..'
XP_VALID_SYMBOL_CHECK = "//*[@id='quote-panel']"
# --
PAGE_STATUS_UNKNOWN = "__PAGE_STATUS_UNKNOWN__"
PAGE_STATUS_NEW = "__PAGE_STATUS_NEW__"
PAGE_STATUS_PREVIEW = "__PAGE_STATUS_PREVIEW__"
PAGE_STATUS_SENT = "__PAGE_STATUS_SENT__"

# --
# --
# --
def goto_page(driver):
	goto_url(driver,URL_PAGE,force=True)

def goto_page_with_symbol(driver,symbol):
	goto_url(driver,URL_PAGE_PARAM.format(symbol),force=True)

def raise_if_symbol_not_found(driver, timeout=1):
	try:
		ele = wait_for_xpath(driver,XP_VALID_SYMBOL_CHECK)
		if(ele.is_displayed() and ele.is_enabled()):
			return
	except:
		pass
	raise Exception("Symbol not found")

def wait_page_loaded(driver,timeout=10):
	wait_for_xpath(driver,XP_REFRESH_BTN,timeout=timeout)

def wait_page_preview_btn(driver,timeout=10):
	wait_for_xpath(driver,XP_PREVIEW_BTN,timeout=timeout)

# def wait_page_place_order_btn(driver,timeout=10):
# 	wait_for_xpath(driver,XP_PLACE_ORDER_BTN,timeout=timeout)

def wait_page_new_order_btn(driver,timeout=10):
	wait_for_xpath(driver,XP_NEW_ORDER_BTN,timeout=timeout)

def wait_for_preview_accepted_or_error(driver,timeout=60):
	total_time = timeout
	while(total_time>0):
		total_time -= 1
		time.sleep(1)
		try:
			return get_preview(driver)
		except:
			pass
		elements = driver.find_elements(By.XPATH,XP_PREVIEW_ERROR)
		if(len(elements)>0 and len(elements[0].text)>0):
			print(f"ERROR:'{elements[0].text}'")
			return elements[0]
	raise BaseException("timeout")

def page_status(driver):
	preview_btn = driver.find_elements(By.XPATH,XP_PREVIEW_BTN)
	if(len(preview_btn)>0):
		return PAGE_STATUS_NEW
	# --
	place_order_btn = driver.find_elements(By.XPATH,XP_PLACE_ORDER_BTN)
	if(len(place_order_btn)>0):
		return PAGE_STATUS_PREVIEW
	# --
	new_order_btn = driver.find_elements(By.XPATH,XP_NEW_ORDER_BTN)
	if(len(new_order_btn)>0):
		return PAGE_STATUS_SENT
	# --
	return PAGE_STATUS_UNKNOWN

# --
# -- helper
# --
def click_btn(driver, btn_xpath):
	btn_ele = driver.find_element(By.XPATH,btn_xpath)
	btn_ele.click()

XPATH_STR_FORM_BTN = "//div[@class='eq-ticket__ticket-container']//button"
def fid_new_order_select_option(driver, list_name, option_name):
	# --
	# -- find the dropbox, and click it to show the option list
	# --
	drop_list_btn = None
	for ele in driver.find_elements(By.XPATH,XPATH_STR_FORM_BTN):
		lines = ele.text.splitlines()
		if(len(lines)==0):
			continue
		if(lines[0].upper().startswith('WARNING:')):
			popped = lines.pop(0)
		button_name = lines[0]
		if(list_name.lower() in button_name.lower()):
			drop_list_btn = ele
			ele.click()
			break
	if(drop_list_btn is None):
		raise BaseException("Cannot find dropbox name:" + list_name)
	# --
	# -- drop list loading 
	# -- !! could take time if connection is slow !!
	# --
	drop_list = None
	for sltime in (0.3, 0.5, 1.0, 2.0):
		time.sleep(sltime)
		drop_list = driver.find_elements(By.XPATH,"//div[@role='option']")
		if(len(drop_list)>0):
			break
		drop_list = driver.find_elements(By.XPATH,"//li[@role='presentation']")
		if(len(drop_list)>0):
			break
		drop_list = driver.find_elements(By.XPATH,"//div[@role='listbox']/*/*[@role='option']")
		if(len(drop_list)>0):
			break
	if(len(drop_list)==0):
		raise BaseException("Cannot load dropbox name:" + list_name)
	# --
	# -- find the right option
	# --
	option_selected_text = None
	for ele in drop_list:
		lines = ele.text.splitlines()
		if(len(lines)!=1):
			continue
		button_name = lines[0]
		if(option_name.lower() in button_name.lower()):
			option_selected_text = ele.text
			ele.click()
			break
	if(option_selected_text is None):
		raise BaseException("Cannot find option name:" + option_name)
	return option_selected_text

XPATH_STR_FORM_INP = "//order-entry-base//input/.."
def fid_new_order_enter_text(driver, box_label, inp_text):
	req = {"id":[str.startswith,"eqt-"]}
	inp_box_ele = None
	for ele in driver.find_elements(By.XPATH,XPATH_STR_FORM_INP):
		if(box_label.lower() in ele.text.lower()):
			inp_box_ele = ele.find_element(By.XPATH,"input")
			if(not match_element(driver, inp_box_ele, req)):
				continue
			inp_box_ele.clear()
			inp_box_ele.send_keys(inp_text)
			break
	if(inp_box_ele is None):
		raise BaseException("Cannot find input with label:" + box_label)

def extract(driver, ele, t1="a", k1=None):
	if(t1=="a"):
		return ele.get_attribute(k1)
	if(t1=="x"):
		return ele.text

def match_element(driver, ele, attrs=None):
	if(attrs is None):
		return True
	for attr in attrs.items():
		attr_str = extract(driver, ele, t1="a", k1=attr[0])
		if( not attr[1][0](attr_str,attr[1][1])):
			return False
	return True

# --
# -- actions
# --
def select_stock(driver):
	return retry(
		lambda : fid_new_order_select_option(driver, "trade", "stocks"),
		exceptTypes=(StaleElementReferenceException,BaseException),
		retry=10,
		rtnEx=False,
		silent=True
	)

def select_account(driver,account):
	return retry(
		lambda : fid_new_order_select_option(driver, "account", account),
		exceptTypes=(StaleElementReferenceException,BaseException),
		retry=10,
		rtnEx=False,
		silent=True
	)

def select_action(driver,action):
	return retry(
		lambda : fid_new_order_select_option(driver, "action", action),
		exceptTypes=(StaleElementReferenceException,BaseException),
		retry=10,
		rtnEx=False,
		silent=True
	)

def preview_order(driver):
	return retry(
		lambda : click_btn(driver, XP_PREVIEW_BTN),
		exceptTypes=(NoSuchElementException,BaseException),
		retry=10,
		rtnEx=False,
		silent=True
	)
	# -- rm -- preview_btn = driver.find_element(By.XPATH,XP_PREVIEW_BTN)
	# -- rm -- preview_btn.click()

def send_order(driver):
	return retry(
		lambda : click_btn(driver, XP_PLACE_ORDER_BTN),
		exceptTypes=(NoSuchElementException,BaseException),
		retry=10,
		rtnEx=False,
		silent=True
	)
	# -- rm -- place_order_btn = driver.find_element(By.XPATH,XP_PLACE_ORDER_BTN)
	# -- rm -- place_order_btn.click()

def set_quantity(driver,quantity):
	fid_new_order_enter_text(driver, "Quantity", "{}".format(quantity))

def set_limit_price(driver,price):
	fid_new_order_select_option(driver, "Order Type", "limit")
	fid_new_order_enter_text(driver, "Limit Price", "{0:0.2f}".format(price))
	
def set_day_order(driver):
	fid_new_order_select_option(driver, "time in force", "day")

def set_condition_none(driver):
	fid_new_order_select_option(driver, "conditions", "None")

def refresh_current_market(driver):
	ele = wait_for_xpath(driver,"//pvd3-button[@id='eq-ticket__quote-refresh-icon-a']")
	ele.click()

def get_current_market(driver,timeout=10):
	XPATH_STR_FULL_ORD_QUOTE_PANEL = '//*[@id="quote-panel"]'
	XPATH_STR_FULL_ORD_BID_ASK_ELE = '//div[@class="block-price-layout"]//span[@class="number"]'
	quote_panel = WebDriverWait(driver, timeout).until(EC.visibility_of_element_located((By.XPATH,XPATH_STR_FULL_ORD_QUOTE_PANEL)))
	bid_ask_eles = quote_panel.find_elements(By.XPATH,XPATH_STR_FULL_ORD_BID_ASK_ELE)
	bid_price,ask_price = float(bid_ask_eles[0].text),float(bid_ask_eles[1].text)
	return { "bid_price":bid_price,"ask_price":ask_price }

def get_preview(driver):
	all_ele = driver.find_elements(By.XPATH,XP_PREVIEW_ORDER)
	lines = list(all_ele[0].text.split("\n"))
	lines = iter( lines[lines.index("Account"):-1] )
	items = { kk:vv for kk,vv in zip(lines,lines) }
	items['Action'] = items['Action'].upper()
	items['Quantity'] = locale.atof(items['Quantity'].strip("$"))
	# --
	warning_msg = []
	warnings = driver.find_elements(By.XPATH,XP_PREVIEW_WARNING)
	for warning in warnings:
		warning_msg.append(warning.text)
	items['Warning'] = warning_msg
	# --
	est_cost_ele = driver.find_element(By.XPATH,XP_PREVIEW_EST_COST)
	est_cost = locale.atof(est_cost_ele.text.split("\n")[1].strip("$"))
	items['Cost'] = est_cost
	return items

def get_sent_order(driver):
	received_order_div = driver.find_element(By.XPATH,XP_RECEIVED_ORDER)
	received_order_lines = received_order_div.text.split("\n")
	return {
		"Desc" : received_order_lines[1],
		"Order#" : received_order_lines[2][1:]
	}

