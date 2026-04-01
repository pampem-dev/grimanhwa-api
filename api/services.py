from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

def get_selenium_driver():
    options = Options()
    
    # 1. PATH CORRECTION: 
    # In Ubuntu Noble (Railway), the binary is usually at /usr/bin/chromium
    options.binary_location = "/usr/bin/chromium"
    
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')

    # 2. IDENTITY: 
    # This makes the server look like a real Windows laptop, not a headless script.
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

    # 3. STEALTH: 
    # Disables the "I am a bot" flags that Chrome sends by default.
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=options)

    # 4. JAVASCRIPT STEALTH: 
    # This prevents the website from detecting Selenium's 'webdriver' property.
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    
    return driver