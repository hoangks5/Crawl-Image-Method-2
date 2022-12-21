"""
Copyright 2022 hoangks5

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

import time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import ElementNotVisibleException, StaleElementReferenceException
import platform
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import os.path as osp
from pexels_api import API
import os
import threading
from dotenv import load_dotenv
from fastapi import FastAPI, Form
load_dotenv()
app = FastAPI(
    title="API Crawl",
    description="",
    version="1.0",
    docs_url='/crawl/docs',
    openapi_url='/openapi.json', # This line solved my issue, in my case it was a lambda function
    redoc_url='/crawl/redoc'
)

def create_browser(no_gui=False):
        chrome_options = Options()
        if no_gui == True :
            chrome_options.add_argument('--headless')
        browser = webdriver.Chrome(ChromeDriverManager().install(), chrome_options=chrome_options)
        return browser

def get_scroll(self):
        pos = self.browser.execute_script("return window.pageYOffset;")
        return pos

def wait_and_click(self, xpath):
    #  Sometimes click fails unreasonably. So tries to click at all cost.
    try:
        w = WebDriverWait(self.browser, 15)
        elem = w.until(EC.element_to_be_clickable((By.XPATH, xpath)))
        elem.click()
        self.highlight(elem)
    except Exception as e:
        print('Click time out - {}'.format(xpath))
        print('Refreshing browser...')
        self.browser.refresh()
        time.sleep(2)
        return self.wait_and_click(xpath)

    return elem

def highlight(self, element):
    self.browser.execute_script("arguments[0].setAttribute('style', arguments[1]);", element,
                                "background: yellow; border: 2px solid red;")


def remove_duplicates(_list):
    return list(dict.fromkeys(_list))


def naver_(keyword):
    browser = create_browser(no_gui=False)
    browser.get(
        "https://search.naver.com/search.naver?where=image&sm=tab_jum&query={}{}".format(keyword, ""))

    time.sleep(1)
    links = []
    elem = browser.find_element(By.TAG_NAME, "body")

    for i in range(60):
        elem.send_keys(Keys.PAGE_DOWN)
        time.sleep(0.2)

    imgs = browser.find_elements(By.XPATH,
                                    '//div[@class="photo_bx api_ani_send _photoBox"]//img[@class="_image _listImage"]')


    

    for img in imgs:
        try:
            src = img.get_attribute("src")
            if src[0] != 'd':
                links.append(src)
        except Exception as e:
            print('[Exception occurred while collecting links from naver] {}'.format(e))

    links = remove_duplicates(links)
    browser.close()
    return links


def flickr_(keyword,page):
    browser = create_browser(no_gui=False)
    links = []
    
    browser.get(
        "https://flickr.com/search/?text="+keyword+"&view_all="+str(page)+"")

    time.sleep(1)
    print('Scrolling down') 

    elem = browser.find_element(By.TAG_NAME, "body")

    for i in range(60):
        elem.send_keys(Keys.PAGE_DOWN)
        time.sleep(0.2)

    imgs = browser.find_elements(By.XPATH,
                                    '//*[@class="photo-list-photo-container"]/img')
    for img in imgs:
        try:
            src = img.get_attribute("src")
            if src[0] != 'd':
                links.append(src)
        except Exception as e:
            print('[Exception occurred while collecting links from naver] {}'.format(e))
    links = remove_duplicates(links)
    browser.close()
    return links

def pexels_(keyword):
    PEXELS_API_KEY = os.getenv('PEXELS_API_KEY')
    api = API(PEXELS_API_KEY)
    links = []

    for i in range(1, 3, 1):
        api.search(keyword, page=i, results_per_page=80)
        photos = api.get_entries()
        for photo in photos:
            links.append(photo.original)
    links = remove_duplicates(links)
    return links


def crawl_all(label):
    data = []
    def t1(label):
        data.append(naver_(label))
    def t2(label):
        data.append(flickr_(label,1))
    def t3(label):
        data.append(flickr_(label,2))
    def t4(label):
        data.append(flickr_(label,3))
    def t5(label):
        data.append(pexels_(label))
    threads = []
    threads.append(threading.Thread(target=t1,args={label,}))
    threads.append(threading.Thread(target=t2,args={label,}))
    threads.append(threading.Thread(target=t3,args={label,}))
    threads.append(threading.Thread(target=t4,args={label,}))
    threads.append(threading.Thread(target=t5,args={label,}))
    
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return data
    


@app.post("/crawl")
async def crawl(label: str = Form(description='label text')
                ):
    return crawl_all(label)
