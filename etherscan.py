import csv
import json
import os
import random
import threading
import time
import traceback

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from urllib3.exceptions import InsecureRequestWarning
from webdriver_manager.chrome import ChromeDriverManager
import urllib3

urllib3.disable_warnings(InsecureRequestWarning)

API_KEY = "05b802522dd0ce9f6cd24b443db4d88a"
data_sitekey = '6Le1YycTAAAAAJXqwosyiATvJ6Gs2NLn8VEzTVlS'
es = "etherscan.io"
page_url = f'https://{es}/login'
timeout = 5
debug = os.path.isfile('chromedriver.exe')
if not os.path.isfile("blocked.txt"):
    with open('blocked.txt', 'w') as bfile:
        bfile.write("\n".join(["eth2-depositor", "gnosis-safe-multisig", "token-contract"]))
with open('blocked.txt', 'r') as bfile:
    blocked = bfile.read().splitlines()
account_headers = ['Address', 'Name Tag', 'Name Tag URL', 'AddressLink', 'AddressType', 'LabelIDs',
                   'Subcategory', 'Time']
token_headers = ['Address', 'AddressLink', 'Name', 'Abbreviation', 'Website', 'SocialLinks', 'Image', 'LabelIDs',
                 'OverviewText', 'MarketCap', 'Holder', 'AdditionalInfo', 'Overview', 'AddressType', 'Time']
ac_hdrs = ['Subcategory', 'Desc', 'Label', 'Page', 'AT', 'Address', 'Name Tag', 'Balance', 'Txn Count']
tkn_hdrs = ['Subcategory', 'Desc', 'Label', 'Page', 'AT', '#', 'Contract Address', 'Token Name', 'Market Cap',
            'Holders', 'Website']
thread_count = 20
semaphore = threading.Semaphore(thread_count)
lock = threading.Lock()
busy = False
scraped = {}
version = 34.0
proxy = "http://ac5a4cbb84ae4ec1907dfc3a38284ca4:@proxy.crawlera.com:8011"
proxies = {
    "http": proxy,
    "https": proxy,
}
# def processCSV():
#     for at in ['Account','Token']:
        

def getToken(soup, tr):
    tkn = tr['Contract Address']
    try:
        try:
            tr['Description'] = json.loads(soup.find('script', {"type": "application/ld+json"}).text)['description']
        except:
            tr['Description'] = ""
        hldr = 'ContentPlaceHolder1_tr_tokenHolders'
        try:
            print(soup.find('div', {'class': 'table-responsive mb-2'}).text)
        except:
            pass
        data = {
            "Address": tkn,
            "AddressLink": f"https://{es}/address/{tkn}",
            "Name": soup.find('div', {'class': "media-body"}).find('span').text.strip() if soup.find('div', {
                'class': "media-body"}) is not None else "",
            "Abbreviation": getTag(soup, 'div', {'class': 'col-md-8 font-weight-medium'}).split()[-1],
            "Website": soup.find('div', {"id": 'ContentPlaceHolder1_tr_officialsite_1'}).find('a')['href'] if soup.find('div', {"id": 'ContentPlaceHolder1_tr_officialsite_1'}) is not None else "",
            "SocialLinks": [{li.find('a')['data-original-title'].split(':')[0]: li.find('a')['href']} for li in
                            soup.find_all('li', {"class": "list-inline-item mr-3"})],
            "Image": f"https://{es}/{soup.find('img', {'class': 'u-sm-avatar mr-2'})['src']}",
            "LabelIDs": [a.text for a in soup.find_all('div', {'class': 'mt-1'})[1].find_all('a') if
                         soup.find_all('div', {'class': 'mt-1'}) is not None and len(
                             soup.find_all('div', {'class': 'mt-1'})) > 1],
            "OverviewText": soup.find('h2', {"class": "card-header-title"}).find('span').text.strip()[1:-1],
            "MarketCap": tr['Market Cap'],
            "Holder": soup.find('div', {'id': hldr}).find('div', {'class': 'mr-3'}).text.split('(')[0].strip(),
            "AdditionalInfo": "",
            "Overview": tr['Description'],
            "AddressType": tr['Subcategory'],
            "Time": time.strftime('%d-%m-%Y %H:%M:%S'),
        }
        print(json.dumps(data, indent=4))
        filename = f"./CSVs/{tr['Label']}-token.csv"
        if not os.path.exists(filename):
            with open(filename, 'w', newline='', encoding='utf8') as file:
                csv.DictWriter(file, fieldnames=token_headers).writeheader()
        with open(filename, 'a', newline='', encoding='utf8') as file:
            csv.DictWriter(file, fieldnames=token_headers).writerow(data)
        with open('scraped_tokens.txt', 'a', encoding='utf8') as sfile:
            sfile.write(tkn + "\n")
        scraped['tokens'].append(tkn)
    except:
        print(soup)
        print(f"Error on token {tkn}")
        traceback.print_exc()
        with open('Error-Token.txt', 'a', encoding='utf8') as efile:
            efile.write(f"{tkn}\n")


def getAccount(soup, tr):
    addr = tr['Address']
    try:
        try:
            print(soup.find('div', {'class': 'table-responsive mb-2'}).text.replace('OVERVIEW', ''))
        except:
            pass
        tag = soup.find("span", {"title": 'Public Name Tag (viewable by anyone)'})
        data = {
            "Name Tag": tag.text if tag is not None else tr['Name Tag'],
            "Address": addr,
            "AddressLink": f"https://{es}/address/{addr}",
            "AddressType": soup.find('h1').text.strip().split()[0],
            "Name Tag URL": tag.parent.find('a')[
                'href'] if tag is not None and tag.parent is not None and tag.parent.find('a') is not None else "",
            "LabelIDs": [a.text for a in soup.find_all('div', {'class': 'mt-1'})[1].find_all('a') if
                         soup.find_all('div', {'class': 'mt-1'}) is not None and len(
                             soup.find_all('div', {'class': 'mt-1'})) > 1],
            "Subcategory": tr['Subcategory'],
            "Time": time.strftime('%d-%m-%Y %H:%M:%S'),
        }
        print(json.dumps(data, indent=4))
        filename = f"./CSVs/{tr['Label']}-accounts.csv"
        if not os.path.exists(filename):
            with open(filename, 'w', newline='', encoding='utf8') as file:
                csv.DictWriter(file, fieldnames=account_headers).writeheader()
        with open(filename, 'a', newline='', encoding='utf8') as file:
            csv.DictWriter(file, fieldnames=account_headers).writerow(data)
        with open('scraped_accounts.txt', 'a', encoding='utf8') as sfile:
            sfile.write(addr + "\n")
        scraped['accounts'].append(addr)
    except:
        print(soup)
        print(f"Error on account {addr}")
        traceback.print_exc()
        with open('Error-Account.txt', 'a', encoding='utf8') as efile:
            efile.write(f"{addr}\n")
        # print(soup)


def isBusy(soup):
    if soup.find('title') is not None and "Maintenance Mode" in soup.find('title').text:
        return True
    if soup.find('h1') is not None and "request" in soup.find('h1').text.strip().lower():
        return True
    # if "User account suspended" in str(soup):
    #     checkIp()
    #     print("Account suspended!")
    #     return True
    return False


def scrape(driver, tr, at, retry=3):
    try:
        global busy
        while busy:
            time.sleep(1)
        addr = tr['Address'] if at == 'accounts' else tr['Contract Address']
        url = f'https://{es}/{"address" if at == "accounts" else "token"}/{addr}'
        with semaphore:
            print(f"Working on {at[:-1]} {addr} {url}")
            soup = getSession(driver, url)
        if busy:
            while busy:
                time.sleep(random.randint(1, 5))
            with semaphore:
                print(f"Working on {at[:-1]} {addr}")
                soup = getSession(driver, url)
        if "User account suspended" in str(soup):
            checkIp()
            # print("Account suspended!")
            with lock:
                busy = True
                print(f"Processing via browser {url}")
                driver.get(url)
                soup = getSoup(driver)
        elif isBusy(soup):
            busy = True
            print(soup.find('title').text.strip())
            with lock:
                print(f"Processing via browser {url}")
                driver.get(url)
                soup = getSoup(driver)
                while isBusy(soup):
                    print(soup.find('title').text.strip())
                    busy = True
                    driver.get(url)
                    time.sleep(random.randint(3, 5))
                    soup = getSoup(driver)
        busy = False
        if at == "tokens":
            getToken(soup, tr)
        else:
            getAccount(soup, tr)
    except:
        if retry > 0:
            scrape(driver, tr, at, retry - 1)
        else:
            traceback.print_exc()
            return


def scrapeLabel(driver, label, at):
    print(f"Working on label {label} ({at})")
    driver.get(f'https://{es}/{at}/label/{label}?subcatid=undefined&size=100&start=0&order=asc')
    fn = tkn_hdrs if at == "tokens" else ac_hdrs

    for i in range(2):
        try:
            print("Fetching rows...")
            getElement(driver, '//tr[@class="odd"]')
            break
        except:
            time.sleep(1)
    try:
        getElement(driver, '//tr[@class="odd"]')
    except:
        print(f"No {at} found!")
        with open('scraped_labels.txt', 'a', encoding='utf8') as sfile:
            sfile.write(f"{label}-{at}\n")
        scraped['labels'].append(f"{label}-{at}")
        return
    soup = getSoup(driver)
    ul = soup.find('ul', {"class": "nav nav-custom nav-borderless nav_tabs"})
    subcats = {"Main": "0"}
    if ul is not None:
        for a in ul.find_all('a', {"class": "nav-link"}):
            subcats[a.text.split()[0]] = a['val']
    print("Subcategories:", json.dumps(subcats, indent=4))
    d = soup.find('div', {"class": "card-body"})
    desc = ""
    if d and "found" not in d.text:
        print(d.text.strip())
        desc = d.text.strip()
    csv_file = f'./labelcloud/{label}_{at}_Main.csv'
    for subcat in subcats.keys():
        print(f"Working on category {subcat}")
        csv_file = f'./labelcloud/{label}_{at}_{subcat}.csv'
        if not os.path.isfile(csv_file):
            start = 0
            with open(csv_file, 'w', encoding='utf8', newline='') as lfile:
                csv.DictWriter(lfile, fieldnames=fn).writeheader()
        else:
            start = 0
            with open(csv_file, encoding='utf8', newline='') as lfile:
                fl = csv.DictReader(lfile, fieldnames=fn)
                next(fl)
                for line in fl:
                    try:
                        page = int(line['Page']) + 1
                        if page > start:
                            start = page
                    except:
                        traceback.print_exc()
            print(f'Resuming from page {start}')
        driver.get(f'https://{es}/{at}/label/{label}?subcatid={subcats[subcat]}&size=100&start=0&order=asc')
        soup = getSoup(driver)
        pageno = soup.find('li', {'class': 'page-item disabled'})
        if pageno is not None:
            pagenos = pageno.find_all('strong')[1].text
            print(soup.find('div', {"role": "status"}).text.strip())
            print("Total pages:", pagenos)
            for i in range(start, int(pagenos)):
                trs = ths = []
                for _ in range(3):
                    try:
                        print(f"Working on page#{i + 1}")
                        t_url = f'https://{es}/{at}/label/{label}?subcatid={subcats[subcat]}' \
                                f'&size=100&start={i * 100}&order=asc'
                        print(t_url)
                        driver.get(t_url)
                        time.sleep(1)
                        getElement(driver, '//tr[@class="odd" and @role="row"]/td')
                        soup = getSoup(driver)
                        table = soup.find('table', {"id": f"table-subcatid-{subcats[subcat]}"})
                        if table is None:
                            table = soup.find('table')
                        ths = table.find('thead').find_all('th')
                        trs = table.find('tbody').find_all('tr')
                        break
                    except:
                        traceback.print_exc()
                rows = []
                for tr in trs:
                    tds = tr.find_all('td')
                    if len(tds) == len(ths):
                        data = {"Subcategory": subcat, "Desc": desc, "Label": label, "Page": i, "AT": at}
                        for t in range(len(ths)):
                            try:
                                if ths[t].text == "Website":
                                    data[ths[t].text] = tds[t].find('a')['href']
                                else:
                                    data[ths[t].text.strip()] = tds[t].text
                            except:
                                print(tds)
                        rows.append(data)
                # print(json.dumps(rows, indent=4))
                with open(csv_file, 'a', encoding='utf8', newline='') as lfile:
                    csv.DictWriter(lfile, fieldnames=fn).writerows(rows)
    threads = []
    with open(csv_file, 'r', encoding='utf8') as cfile:
        x = csv.DictReader(cfile, fieldnames=fn)
        next(x)
        for tr in x:
            if at == 'accounts' or at == 'tokens':
                addr = tr['Address'] if at == 'accounts' else tr['Contract Address']
                if addr not in scraped[at]:
                    thread = threading.Thread(target=scrape, args=(driver, tr, at,))
                    thread.start()
                    threads.append(thread)
                    time.sleep(0.1)
                else:
                    print(f"{at} {addr} already scraped!")
                    scraped[at].append(addr)
    for thread in threads:
        thread.join()
    with open('scraped_labels.txt', 'a', encoding='utf8') as sfile:
        sfile.write(f"{label}-{at}\n")
    scraped['labels'].append(label)
    combineCSVs()


def main():
    global scraped
    logo()
    time.sleep(0.5)
    if not os.path.isfile('zyte-proxy-ca.crt'):
        with open('zyte-proxy-ca.crt', 'w') as zfile:
            zfile.write(cert)
    driver = getChromeDriver()

    for d in ['CSVs', 'labelcloud']:
        if not os.path.isdir(d):
            os.mkdir(d)
    if not debug:
        reCaptchaSolver(driver)
        driver.get(f'https://{es}/labelcloud')
    btnclass = 'col-md-4 col-lg-3 mb-3 secondary-container'
    getElement(driver, f'//div[@class="{btnclass}"]')
    soup = getSoup(driver)
    divs = [
        x for x in soup.find_all('div', {'class': btnclass})
        if x.find('button')['data-url'] not in blocked
    ]
    data = {"total_accounts": 0, "total_tokens": 0, "total_labels": len(divs)}
    for x in ['labels', 'accounts', 'tokens']:
        if os.path.isfile(f"scraped_{x}.txt"):
            with open(f"scraped_{x}.txt", encoding='utf8') as afile:
                scraped[x] = afile.read().splitlines()
        else:
            scraped[x] = []
        data[f'scraped_{x}'] = len(scraped[x])
    for div in divs:
        for a in [ahref.text.lower() for ahref in div.find_all('a')]:
            if 'account' in a:
                try:
                    data["total_accounts"] += int(a.split('(')[1].split(')')[0])
                except:
                    traceback.print_exc()
            elif 'token' in a:
                try:
                    data["total_tokens"] += int(a.split('(')[1].split(')')[0])
                except:
                    traceback.print_exc()
    for d in ['accounts', 'tokens', 'labels']:
        data[f'left_{d}'] = data[f'total_{d}'] - data[f'scraped_{d}']
    print(json.dumps(data, indent=4))
    time.sleep(2)
    try:
        for div in divs:
            label = div.find('button')['data-url']
            for at in [a['href'].split('/')[1] for a in div.find_all('a')]:
                if at.lower() in ['accounts', 'tokens']:
                    if f"{label}-{at}" not in scraped['labels']:
                        # print(label, at)
                        scrapeLabel(driver, label, at)
                    else:
                        print(f"{label} ({at}) already scraped!")
    except KeyboardInterrupt:
        pass
    combineCSVs()


def combineCSVs():
    token_rows = []
    account_rows = []
    for file in os.listdir('CSVs'):
        if file.endswith('-token.csv'):
            with open(f'./CSVs/{file}', encoding='utf8') as tfile:
                token_rows.extend([x for x in csv.DictReader(tfile)])
        elif file.endswith('-accounts.csv'):
            with open(f'./CSVs/{file}', encoding='utf8') as afile:
                account_rows.extend([x for x in csv.DictReader(afile)])
    print(f"Account rows: {len(account_rows)}")
    print(f"Token rows: {len(token_rows)}")
    with open('AccountsMaster.csv', 'w', newline='', encoding='utf8') as afile:
        c = csv.DictWriter(afile, fieldnames=account_headers)
        c.writeheader()
        c.writerows(account_rows)
    with open('TokensMaster.csv', 'w', newline='', encoding='utf8') as tfile:
        c = csv.DictWriter(tfile, fieldnames=token_headers)
        c.writeheader()
        c.writerows(token_rows)


def getChromeDriver():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('start-maximized')
    chrome_options.add_argument(f'user-agent={UserAgent().random}')
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    if debug and os.path.isfile('chromedriver.exe'):
        # print("Connecting existing Chrome for debugging...")
        chrome_options.debugger_address = "127.0.0.1:9222"
    # chrome_options.add_argument("--blink-settings=imagesEnabled=false")
    chrome_options.add_argument(f'--user-data-dir={os.getcwd()}/ChromeProfile')
    if os.name != 'nt':
        chrome_options.add_argument("--headless")
    if os.path.isfile('chromedriver.exe'):
        driver = webdriver.Chrome(
            # service=Service(ChromeDriverManager().install()),
            options=chrome_options)
    else:
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options)
    return driver


def waitCloudflare(driver):
    global busy
    while "Checking your browser" in driver.page_source:
        print("Waiting for cloudflare...")
        busy = True
        time.sleep(random.randint(3, 5))
    busy = False


def reCaptchaSolver(driver):
    print("Logging in...")
    driver.get(page_url)
    time.sleep(2)
    waitCloudflare(driver)
    while "busy" in driver.current_url or "unusual traffic" in driver.page_source.lower():
        time.sleep(3)
        driver.get(page_url)
        print("Busy")
    time.sleep(1)
    if "login" not in driver.current_url:
        print(f"Already logged in as {driver.find_element(By.TAG_NAME, 'h4').text}")
        return
    driver.find_element(By.ID, "ContentPlaceHolder1_txtUserName").send_keys("tapendra")
    driver.find_element(By.ID, "ContentPlaceHolder1_txtPassword").send_keys("12345678")
    driver.find_element(By.XPATH, '//label[@for="ContentPlaceHolder1_chkRemember"]').click()
    u1 = f"https://2captcha.com/in.php?key={API_KEY}&method=userrecaptcha&googlekey" \
         f"={data_sitekey}&pageurl={page_url}&json=1&invisible=1"
    r1 = requests.get(u1)
    print(r1.json())
    time.sleep(10)
    rid = r1.json().get("request")
    u2 = f"https://2captcha.com/res.php?key={API_KEY}&action=get&id={int(rid)}&json=1"
    time.sleep(5)
    while True:
        r2 = requests.get(u2)
        print(r2.json())
        if r2.json().get("status") == 1:
            form_tokon = r2.json().get("request")
            break
        time.sleep(5)
    driver.execute_script(f'document.getElementById("g-recaptcha-response").innerHTML="{form_tokon}";')
    time.sleep(3)
    button = driver.find_element(By.XPATH, "/html/body/div[1]/main/div/form/div[8]/div[2]/input")
    driver.execute_script("arguments[0].click();", button)
    print("Logged in!")
    time.sleep(5)


def getSession(driver, url):
    s = requests.Session()
    s.headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/101.0.4951.67 Safari/537.36'
    }
    for cookie in driver.get_cookies():
        s.cookies.set(cookie['name'], cookie['value'])
    return BeautifulSoup(s.get(url,
                               proxies=proxies,
                               verify='zyte-proxy-ca.crt',
                               # verify=False,
                               ).content, 'lxml')


def logo():
    print(fr"""
    ___________  __   .__                                                   
    \_   _____/_/  |_ |  |__    ____ _______  ______  ____  _____     ____  
     |    __)_ \   __\|  |  \ _/ __ \\_  __ \/  ___/_/ ___\ \__  \   /    \ 
     |        \ |  |  |   Y  \\  ___/ |  | \/\___ \ \  \___  / __ \_|   |  \
    /_______  / |__|  |___|  / \___  >|__|  /____  > \___  >(____  /|___|  /
            \/             \/      \/            \/      \/      \/      \/ 
=================================================================================
           Etherscan labelcloud scraper by github.com/evilgenius786
=================================================================================
[+] Scrapes accounts and tokens
[+] CSV/JSON Output
[+] Multi-threaded ({thread_count})
[+] Proxy integrated
[+] Version {version}
_________________________________________________________________________________
""")


def getSoup(driver):
    time.sleep(1)
    return BeautifulSoup(driver.page_source, 'lxml')


def getTag(soup, tag, attrib):
    try:
        return soup.find(tag, attrib).text.strip()
    except:
        return ""


def getElement(driver, xpath):
    waitCloudflare(driver)
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.XPATH, xpath)))


def checkAccount():
    s = requests.Session()
    s.headers = {'user-agent': 'Mozilla/5.0'}
    adrs = '0x791018934df872b729eb2852dec200bab6f95709'
    soup = BeautifulSoup(s.get(f'https://{es}/address/{adrs}').content, 'lxml')
    ac_data = {
        "Address": adrs,
        "Subcategory": 'Subcategory',
        "Label": 'label',
        'Name Tag': ""
    }
    getAccount(soup, ac_data)


def checkToken():
    s = requests.Session()
    s.headers = {'user-agent': 'Mozilla/5.0'}
    adrs = '0x41f723448433367be140d528d35efecd3e023db6'
    soup = BeautifulSoup(s.get(f'https://{es}/token/{adrs}').content, 'lxml')
    tk_data = {
        'Contract Address': adrs,
        "Subcategory": 'Subcategory',
        "Label": 'Label',
        "Market Cap": 'MarketCap',
    }
    getToken(soup, tk_data)


def checkIp():
    res = requests.get('http://lumtest.com/myip.json',
                       proxies=proxies
                       )
    print("Lumtest", res.text)


cert = """-----BEGIN CERTIFICATE-----
MIIERzCCAy+gAwIBAgIJAN/VCi6U4Y5SMA0GCSqGSIb3DQEBCwUAMIG5MQswCQYD
VQQGEwJJRTEQMA4GA1UECAwHTXVuc3RlcjENMAsGA1UEBwwEQ29yazEUMBIGA1UE
CgwLU2NyYXBpbmdIdWIxNTAzBgNVBAsMLExlYWRpbmcgVGVjaG5vbG9neSBhbmQg
UHJvZmVzc2lvbmFsIFNlcnZpY2VzMRQwEgYDVQQDDAtDcmF3bGVyYSBDQTEmMCQG
CSqGSIb3DQEJARYXc3VwcG9ydEBzY3JhcGluZ2h1Yi5jb20wHhcNMTUwNTE5MTQ1
NjA3WhcNMjUwNTE2MTQ1NjA3WjCBuTELMAkGA1UEBhMCSUUxEDAOBgNVBAgMB011
bnN0ZXIxDTALBgNVBAcMBENvcmsxFDASBgNVBAoMC1NjcmFwaW5nSHViMTUwMwYD
VQQLDCxMZWFkaW5nIFRlY2hub2xvZ3kgYW5kIFByb2Zlc3Npb25hbCBTZXJ2aWNl
czEUMBIGA1UEAwwLQ3Jhd2xlcmEgQ0ExJjAkBgkqhkiG9w0BCQEWF3N1cHBvcnRA
c2NyYXBpbmdodWIuY29tMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA
3I3nDH62M7FHT6HG5ZNS9cBeXmMZaKaxYdr+7ioSiVXzruDkH3uX6CQZLkvR2KpG
icHOnd0FM4S4rHYQoWc82b/UGgwjQdi47ED8fqCPusEcgo/7eY3y2Y/JivEWKk6f
z+gBlvEHjKj2EyzZ7FaExTEMQTTe28EroXTNySUctY9jprtKrs8jjGXd2sR6AHF1
M6O+5CT/5kXhuDO9/Q9Tfym7wxBsU/k+6hhNH+RkYlNEvkv0d8vdku/ZKTCBuL9D
NTqgXFvAmOj0MNEjf5kFrF95g+k5+PxPU04TPUtOwU30GYbCjE+ecYsoTODg6+ju
TQoNk3RFt0A0wZS3ly1rnQIDAQABo1AwTjAdBgNVHQ4EFgQUn6fXHOpDIsaswTMr
K2DwcOHLtZ0wHwYDVR0jBBgwFoAUn6fXHOpDIsaswTMrK2DwcOHLtZ0wDAYDVR0T
BAUwAwEB/zANBgkqhkiG9w0BAQsFAAOCAQEAOLtBuyHixFblY2BieG3ZCs8D74Xc
Z1usYCUNuVxOzKhuLt/cv49r39SVienqvS2UTr3kmKdyaaRJnYQ06b5FmAP72vdI
4wUAU2F7bFErAVnH1rihB+YMRE/5/6VPLfwuK8yf3rkzdrKcV2DlRQwsnwroSIR8
iON6JK2HOI0/LsKxPXUk9cHrli7e99yazS5+jBhRFGx8AVfoJg/6uLe6IKuw5xEZ
xAzDdjEIB/tf1cE0SQ+5sdmepO1cIjQYVSL7U+br+y9A1J9N+FYkBKVevM/W25tb
iGWBe46djkdm/6eyQ7gtuxhby5lwtRl5sIm9/ID/vWWDMf8O4GPPnW/Xug==
-----END CERTIFICATE-----"""
if __name__ == '__main__':
    # checkToken()
    main()

    # checkIp()
