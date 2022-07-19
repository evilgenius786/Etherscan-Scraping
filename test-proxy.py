import os

import requests

# proxy = "http://c531568766d745b78e4f96337d7a4c4a:@proxy.crawlera.com:8011"

if os.path.isfile('proxy.txt'):
    with open('proxy.txt', 'r', encoding='utf8') as f:
        proxy = f.read().strip()
else:
    proxy = input("Enter proxy endpoint (http://username:password@ip:port): ")
    with open('proxy.txt', 'w', encoding='utf8') as f:
        f.write(proxy)
proxies = {
    "http": proxy,
    "https": proxy,
}
# url="https://httpbin.org/ip"
url='https://lumtest.com/myip.json'
res = requests.get(url, proxies=proxies,
                   verify='zyte-proxy-ca.crt'
                   )
print(res.text)
