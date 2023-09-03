from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time

options = Options()
options.add_experimental_option("detach", True)

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

driver.get("https://www.iplusinteractif.com/")
driver.maximize_window()

print("hello")

emailElement = driver.find_element("xpath", "//*[@id='loginId']")
emailElement.click()
emailElement.send_keys("")

passwordElement = driver.find_element("xpath", "//*[@id='password']")
passwordElement.click()
passwordElement.send_keys("")

sendButton = driver.find_element("xpath", "//*[contains(@class, 'blue button')]")
sendButton.click()

time.sleep(2)
accessListElements = driver.find_elements("xpath", "//div[contains(@class, 'accessContainer')]")
for element in accessListElements:
    print("x")
    time.sleep(1)
    


