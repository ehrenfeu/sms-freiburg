from pathlib import Path
import sms_freiburg
from sms_freiburg.client import SMSFreiburgClient, browser, webdriver, be

sms_freiburg.setup_logger(3)
settings, profiles = sms_freiburg.load_config(Path("config.yaml"), headless=False)

profile = profiles[0]
client = SMSFreiburgClient(profile.user, profile.password)

options = webdriver.ChromeOptions()
# options.add_argument("--headless=new")
browser.config.driver_options = options
browser.config.window_width = 1920
browser.config.window_height = 1080
browser.open("https://www.sms-freiburg.de/")

client._login()

browser.element('a[title="Speiseplan"]').click()
browser.element("table.Table_Standard").should(be.present)

table = browser.element("table.Table_Standard")
rows = table.locate().find_elements("xpath", "./tbody/tr")
header_cells = rows[0].find_elements("xpath", "./td")
food_cells = rows[1].find_elements("xpath", "./td")
