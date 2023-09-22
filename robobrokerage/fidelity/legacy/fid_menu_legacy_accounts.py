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
URL_PAGE = "--n/a--"
# --
XP_MENU_ACCOUNTS = '//*[@aria-label="Choose accounts"]//*[@data-acct-name]'
# --
PAGE_STATUS_UNKNOWN = "__PAGE_STATUS_UNKNOWN__"
PAGE_STATUS_OK = "__PAGE_STATUS_OK__"

# --
# --
# --
def goto_page(driver):
	goto_url(driver,URL_PAGE,force=True)

def wait_page_loaded(driver,timeout=10):
	# --
	# !! bug: fid_menu_legacy_accounts.wait_page_loaded(self.driver)
	# !!      return immediately, no wait
	# --
	wait_for_xpath(driver,XP_MENU_ACCOUNTS,timeout=timeout)
	time.sleep(5)

def page_status(driver):
	label_to_ele = account_label_map(driver)
	if(len(label_to_ele)>0):
		return PAGE_STATUS_OK
	else:
		return PAGE_STATUS_UNKNOWN

# --
# -- actions
# --
def account_label_map(driver):
	label_to_ele = {}
	eles = driver.find_elements(By.XPATH,XP_MENU_ACCOUNTS)
	for ele in eles:
		pvd_id = ele.get_attribute("pvd-id")
		ele_text = ele.text
		if(pvd_id in ele_text):
			label_to_ele[pvd_id] = ele
	return label_to_ele

def select_account(driver,partial_label):
	eles = driver.find_elements(By.XPATH,XP_MENU_ACCOUNTS)
	for ele in eles:
		ele_text = ele.text
		if(partial_label.upper() in ele_text.upper()):
			ele.click()
			return ele_text
	return False



