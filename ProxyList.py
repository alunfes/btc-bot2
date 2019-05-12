import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from time import sleep
from selenium.webdriver.chrome.options import Options
#import chromedriver_binary
import shutil
import os
import random
import re
import threading
import time
from SystemFlg import SystemFlg

#http://proxy.moo.jp/ja/?c=JP&pt=&pr=&a%5B%5D=0&a%5B%5D=1&a%5B%5D=2&u=90

class ProxyList:
    def __init__(self):
        self.target_url = 'https://www.yahoo.co.jp'
        self.PermissionTime = 5
        self.userdata_dir = './UserData'
        if os.path.exists(self.userdata_dir):
            shutil.rmtree(self.userdata_dir)
            os.makedirs(self.userdata_dir)
        else:
            os.makedirs(self.userdata_dir)
        shutil.rmtree(self.userdata_dir)
        os.makedirs(self.userdata_dir, exist_ok=True)
        self.__main_thread()


    def __start_wb(self):
        #chromedriver_binary.add_chromedriver_to_path()
        self.options = webdriver.ChromeOptions()
        self.options.add_argument('--headless')
        self.options.add_argument('--user-data-dir=' + self.userdata_dir)
        self.driver = webdriver.Chrome('./chromedriver',options=self.options)
        self.driver.start_client()

    def __main_thread(self):
        while SystemFlg.get_system_flg():
            proxys = self.__get_proxy()
            self.good_proxy = self.__checkProxy(proxys)
            time.sleep(3600)

    def get_proxy_list(self):
        return self.good_proxy

    def __get_proxy(self):
        self.__start_wb()
        self.driver.get('http://www.cybersyndrome.net/')
        time.sleep(1)
        self.driver.get('http://www.cybersyndrome.net/plr6.html')
        time.sleep(1)
        soup = BeautifulSoup(self.driver.page_source.encode('utf-8'), 'html.parser')
        data = soup.find_all('td', id=re.compile("^n"))
        self.driver.close()
        proxyList = []
        for proxyT in data:
            proxyList.append('http://' + proxyT.text)
        return proxyList

    def __is_bad_proxy(self, proxy):
        try:
            self.__start_wb()
            self.options.add_argument("--proxy-server=" + proxy)
            self.options.add_argument('--headless')
            self.options.add_argument('--user-data-dir=' + self.userdata_dir)
            self.driver = webdriver.Chrome('./chromedriver',options=self.options)
            self.driver.set_page_load_timeout(self.PermissionTime)
            self.driver.get(self.targetUrl)
            self.driver.close()
        except:
            self.driver.close()
            return True
        return False

    def __checkProxy(self, proxys):
        temp = None
        for item in proxys:
            if self.__is_bad_proxy(item):
                print("Bad Proxy:", item)
            else:
                print("Nice Proxy:", item)
                temp = item
                break
        else:
            return None
        return temp

if __name__ == '__main__':
    SystemFlg.initialize()
    pl = ProxyList()
    print(pl.get_proxy_list())



