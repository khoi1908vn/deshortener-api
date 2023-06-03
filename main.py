import os, time, requests, asyncio, traceback
from fastapi import FastAPI, Response, Header
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium import webdriver
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
app = FastAPI()

"""class BrowserPool:
    def __init__(self, pool_size=int(os.environ.get("browser_pool_size", 1))):
        self.pool_size = pool_size
        self.pool = []
        self.lock = Lock()
        self.create_pool()
        
    def create_pool(self):
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--enable-features=WebContentsForceDark')
        
        prefs = {
            "download_restrictions": 3,
            "download.open_pdf_in_system_reader": False,
            "download.prompt_for_download": True,
            "download.default_directory": "/dev/null",
            "plugins.always_open_pdf_externally": False
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        for _ in range(self.pool_size):
            browser = webdriver.Chrome(options=chrome_options)
            self.pool.append(browser)
    
    def get_browser(self):
        with self.lock:
            browser = self.pool.pop()
        return browser
    
    def release_browser(self, browser):
        with self.lock:
            self.pool.append(browser)
            
browser_pool = BrowserPool()

def de_shorten_url(browser, url):
    els = time.time()
    browser.get(url)
    wait = WebDriverWait(browser, 10)
    wait.until(EC.presence_of_element_located((By.XPATH, "//body[not(@class='loading')]")))
    time.sleep(3)
    
    urls = [url]
    while True:
        current_url = browser.current_url
        if current_url == url:
            break
        urls.append(current_url)
        url = current_url
        browser.get(url)
        wait.until(EC.presence_of_element_located((By.XPATH, "//body[not(@class='loading')]")))
        time.sleep(3)
    elapsed = 1000*(time.time() - els)
    return urls, round(elapsed)
"""

from aiohttp import ClientSession

async def de_shorten_url(url):
    els = time.time()
    urls = [url]
    async with ClientSession() as session:
        while True:
            async with session.get(url, allow_redirects=False) as resp:
                if resp.status not in [301, 302, 303, 307, 308]:
                    break
                url = resp.headers['Location']
                urls.append(url)
    elapsed = 1000*(time.time() - els)
    return list(set(urls)), round(elapsed)


@app.get('/')
def root():
    return 'Hello there'

@app.get('/unshorten')
async def image(authorization: str = Header(None), url: str = Header(None)):
    try:
        if not authorization:
            return Response('Missing authorization', status_code=400)
        if authorization != os.environ.get('allowed_key', 'testkey_'):
            return Response(f'Invalid token, given {authorization}', status_code=401)
        if not url:
            return Response('Missing URL in header', status_code=400)
        print("Working on URL:", url)
        loop = asyncio.get_running_loop()
        redirect_list, elapsed = await de_shorten_url(url)
        with open('log.txt', 'a+') as f:
            f.write(str(int(time.time())) + ' ' + f'{url} | {elapsed}ms\n')
        return {"redirects": redirect_list, "elapsed": elapsed}
    except Exception as e:
        traceback.print_exc()
        return Response(f'Error: {e}', status_code=500)
