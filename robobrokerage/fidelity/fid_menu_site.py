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
URL_PAGE = "--n/a--"
# --
XP_MENU_SITE = '//div[@id="pgnb"]/*//ul/li'
# --
PAGE_STATUS_UNKNOWN = "__PAGE_STATUS_UNKNOWN__"
PAGE_STATUS_OK = "__PAGE_STATUS_OK__"

# --
# --
# --
def goto_page(driver):
	goto_url(driver,URL_PAGE,force=True)

def wait_page_loaded(driver,timeout=10):
	wait_for_xpath(driver,XP_MENU_SITE,timeout=timeout)

def page_status(driver):
	label_to_ele = menu_label_map(driver)
	if("LOGOUT" in label_to_ele and "ACCOUNTS&TRADE" in label_to_ele):
		return PAGE_STATUS_OK
	else:
		return PAGE_STATUS_UNKNOWN

# --
# -- actions
# --
def menu_label_map(driver):
	label_to_ele = {}
	eles = driver.find_elements(By.XPATH,XP_MENU_SITE)
	for ele in eles:
		label = ele.text.replace(" ","").upper().strip()
		if(len(label)>0):
			label_to_ele[label] = ele
	return label_to_ele

def click_menu_label(driver,partial_label):
	eles = driver.find_elements(By.XPATH,XP_MENU_SITE)
	for ele in eles:
		label = ele.text.replace(" ","").upper().strip()
		if(partial_label.upper() in label.upper()):
			ele.click()
			return label
	return None

