from selenium.common.exceptions import NoSuchElementException
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait

from ..crawler_util import *
# from .fid_common import *
from . import fid_menu_site

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
URL_PAGE = "https://www.fidelity.com/"
# --
XP_LOGIN_TOP_MENU = '//a[text()[contains(.,"Log In")]]'
XP_LOGIN_MENU = '//a[@name="login"]'
# --
PAGE_STATUS_UNKNOWN = "__PAGE_STATUS_UNKNOWN__"
PAGE_STATUS_OK = "__PAGE_STATUS_OK__"

# --
# --
# --
def goto_page(driver):
	goto_url(driver,URL_PAGE,force=True)

def wait_page_loaded(driver,timeout=10):
	for nn in range(0,timeout):
		try:
			ele = wait_for_xpath(driver,XP_LOGIN_MENU,timeout=1)
			if(ele is not None):
				return
		except:
			ele = wait_for_xpath(driver,XP_LOGIN_TOP_MENU,timeout=1)
			if(ele is not None):
				return

def page_status(driver):
	url = driver.current_url
	if(url.startswith(URL_PAGE)):
		return PAGE_STATUS_OK
	else:
		return PAGE_STATUS_UNKNOWN

# --
# -- actions
# --
def click_login_btn(driver,timeout=10):
	# fid_menu_site.click_menu_label(driver, "LOG IN")
	try:
		ele = driver.find_element(By.XPATH,XP_LOGIN_MENU)
		ele.click()
	except:
		ele = driver.find_element(By.XPATH,XP_LOGIN_TOP_MENU)
		ele.click()

