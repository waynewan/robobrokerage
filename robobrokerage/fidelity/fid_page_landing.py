from selenium.webdriver.common.by import By

from .crawler_util import *
from . import fid_menu_site

# --
URL_PAGE = "https://www.fidelity.com/"
XP_LOGIN_TOP_MENU = '//a[text()[contains(.,"Log In")]]'
XP_LOGIN_MENU = '//a[@name="login"]'
PAGE_STATUS_UNKNOWN = "__PAGE_STATUS_UNKNOWN__"
PAGE_STATUS_OK = "__PAGE_STATUS_OK__"


def match(driver):
	return len(driver.find_elements(By.XPATH, XP_LOGIN_MENU)) > 0 or len(driver.find_elements(By.XPATH, XP_LOGIN_TOP_MENU)) > 0


def goto_page(driver):
	goto_url(driver, URL_PAGE, force=True)


def wait_page_loaded(driver, timeout=10):
	for nn in range(0, timeout):
		try:
			ele = wait_for_xpath(driver, XP_LOGIN_MENU, timeout=1)
			if ele is not None:
				return
		except:
			ele = wait_for_xpath(driver, XP_LOGIN_TOP_MENU, timeout=1)
			if ele is not None:
				return


def page_status(driver):
	url = driver.current_url
	if url.startswith(URL_PAGE):
		return PAGE_STATUS_OK
	return PAGE_STATUS_UNKNOWN


def click_login_btn(driver, timeout=10):
	try:
		ele = driver.find_element(By.XPATH, XP_LOGIN_MENU)
		ele.click()
	except:
		ele = driver.find_element(By.XPATH, XP_LOGIN_TOP_MENU)
		ele.click()
