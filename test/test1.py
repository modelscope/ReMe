# 2025年半年报点评：Q2业绩同比增长，CPU、DCU业务进展顺利
# https://data.eastmoney.com/report/info/AP202508061722561937.html
#
# https://pdf.dfcfw.com/pdf/H3_AP202508061722561937_1.pdf

import requests
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}
url = requests.get("https://data.eastmoney.com/report/stock.jshtml", headers=headers)
print(url.text)