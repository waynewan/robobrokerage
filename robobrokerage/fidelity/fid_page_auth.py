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
XP_USERNAME_INP = '//input[@id="userId-input"]'
XP_PASSWORD_INP = '//input[@id="password"]'
XP_LOGIN_BTN = '//button[@id="fs-login-button"]'
# --
PAGE_STATUS_UNKNOWN = "__PAGE_STATUS_UNKNOWN__"
PAGE_STATUS_OK = "__PAGE_STATUS_OK__"

# --
# --
# --
def goto_page(driver):
	goto_url(driver,URL_PAGE,force=True)

def wait_page_loaded(driver,timeout=10):
	wait_for_clickable_xpath(driver,XP_USERNAME_INP,timeout=timeout)
	wait_for_clickable_xpath(driver,XP_PASSWORD_INP,timeout=timeout)
	wait_for_clickable_xpath(driver,XP_LOGIN_BTN,timeout=timeout)

def page_status(driver):
	uid_inp_ele = driver.find_element(By.XPATH,XP_USERNAME_INP)
	pwd_inp_ele = driver.find_element(By.XPATH,XP_PASSWORD_INP)
	login_btn_ele = driver.find_element(By.XPATH,XP_LOGIN_BTN)
	if(uid_inp_ele is None or pwd_inp_ele is None or login_btn_ele is None):
		return PAGE_STATUS_UNKNOWN
	else:
		return PAGE_STATUS_OK

# --
# -- actions
# --
def fill_username_inp(driver,username):
	ele = driver.find_element(By.XPATH,XP_USERNAME_INP)
	ele.send_keys(Keys.CONTROL+"a")
	ele.send_keys(username)

def fill_password_inp(driver,password):
	ele = driver.find_element(By.XPATH,XP_PASSWORD_INP)
	ele.send_keys(Keys.CONTROL+"a")
	ele.send_keys(password)

def click_login_btn(driver):
	ele = driver.find_element(By.XPATH,XP_LOGIN_BTN)
	ele.click()

