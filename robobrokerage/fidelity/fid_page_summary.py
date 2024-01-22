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
import sys
import tempfile
import time
import locale
locale.setlocale(locale.LC_ALL, 'en_US.UTF8')

# --
# --
# --
URL_PAGE = "https://digital.fidelity.com/ftgw/digital/portfolio/summary"
# --
XP_PAGE_ID1 = '//button[@aria-label="Customize"]'
XP_LEGACY_PAGE_BTN = '//a[text()="legacy portfolio summary page"]'
# --
PAGE_STATUS_UNKNOWN = "__PAGE_STATUS_UNKNOWN__"
PAGE_STATUS_OK = "__PAGE_STATUS_OK__"

# --
# --
# --
def goto_page(driver):
	goto_url(driver,URL_PAGE,force=True)

def wait_page_loaded(driver,timeout=10):
	wait_for_clickable_xpath(driver,XP_PAGE_ID1,timeout=timeout)

def page_status(driver):
	cur_tab_ele = driver.find_elements(By.XPATH,XP_PAGE_ID1)
	if(len(cur_tab_ele)>0):
		return PAGE_STATUS_OK
	else:
		return PAGE_STATUS_UNKNOWN

# --
# -- actions
# --
def goto_legacy(driver):
	try:
		legacy_btn = driver.find_element(By.XPATH,XP_LEGACY_PAGE_BTN)
		legacy_btn.click()
		return True
	except:
		return False

