from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import os

def get_selenium_driver():
    options = Options()
    
    # 1. PATH CORRECTION: 
    # Try multiple possible Chrome/Chromium locations
    chrome_paths = [
        "/usr/bin/chromium",
        "/usr/bin/google-chrome",
        "/usr/bin/chrome",
        "/snap/bin/chromium",
        "/usr/bin/chromium-browser",
        "/opt/google/chrome/chrome",
        "/usr/local/bin/chrome",
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",  # Windows
        "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"  # Windows x86
    ]
    
    chrome_binary = None
    for path in chrome_paths:
        if os.path.exists(path):
            chrome_binary = path
            break
    
    if chrome_binary:
        options.binary_location = chrome_binary
        print(f"Using Chrome binary: {chrome_binary}")
    else:
        print("Chrome binary not found, using default")
    
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

    # 4. FLEXIBLE DRIVER SETUP:
    # Try to find chromedriver automatically, or use specific paths
    driver_paths = [
        "/usr/bin/chromedriver",
        "/usr/local/bin/chromedriver",
        "/snap/bin/chromedriver.chromedriver",
        "chromedriver",  # Let selenium find it in PATH
    ]
    
    service = None
    for path in driver_paths:
        try:
            if path == "chromedriver":
                # Let selenium find it automatically
                service = Service()
            elif os.path.exists(path):
                service = Service(path)
                print(f"Using ChromeDriver: {path}")
                break
        except:
            continue
    
    if service is None:
        service = Service()  # Fallback to auto-detection
    
    try:
        driver = webdriver.Chrome(service=service, options=options)
        
        # 4. JAVASCRIPT STEALTH: 
        # This prevents the website from detecting Selenium's 'webdriver' property.
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })
        
        return driver
    except Exception as e:
        print(f"Failed to create Chrome driver: {e}")
        raise e