import random

import requests
import json
import re
import os
from urllib.parse import urljoin
from time import sleep
import pycurl
from io import BytesIO
from PyPDF2 import PdfReader
from datetime import datetime, timedelta

DOWNLOAD_DIR = "./"

# 随机User-Agent列表
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
]


def get_random_user_agent():
    """获取随机User-Agent"""
    import random
    return random.choice(USER_AGENTS)


def download_pdf(pdf_url, filename):
    """
    使用pycurl下载PDF文件（模拟curl请求）

    参数:
        pdf_url (str): PDF文件的URL
        filename (str): 保存文件名（不含路径）

    返回:
        bool: 是否下载成功
    """
    save_path = os.path.join(DOWNLOAD_DIR, filename)
    buffer = BytesIO()
    c = pycurl.Curl()

    try:
        # 设置curl选项
        c.setopt(pycurl.URL, pdf_url)
        c.setopt(pycurl.WRITEDATA, buffer)
        c.setopt(pycurl.FOLLOWLOCATION, True)
        c.setopt(pycurl.MAXREDIRS, 5)
        c.setopt(pycurl.CONNECTTIMEOUT, 30)
        c.setopt(pycurl.TIMEOUT, 300)

        # 设置防爬虫headers
        headers = [
            f"User-Agent: {get_random_user_agent()}",
            "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer: https://data.eastmoney.com/",
            "Accept-Language: zh-CN,zh;q=0.9"
        ]
        c.setopt(pycurl.HTTPHEADER, headers)

        # 执行下载
        c.perform()

        # 验证响应
        if c.getinfo(pycurl.HTTP_CODE) != 200:
            print(f"下载失败 HTTP {c.getinfo(pycurl.HTTP_CODE)}")
            return False

        # 保存文件
        with open(save_path, 'wb') as f:
            f.write(buffer.getvalue())

        print(f"✓ 成功下载 {filename}")
        return True

    except pycurl.error as e:
        errno, errstr = e.args
        print(f"pycurl错误({errno}): {errstr}")
        return False
    except Exception as e:
        print(f"下载异常: {str(e)}")
        return False
    finally:
        c.close()
        buffer.close()

if __name__ == '__main__':
    url_list = [
        "https://pdf.dfcfw.com/pdf/H3_AP202508061722531920_1.pdf?1754495126000.pdf",
    ]

    url_list = [x.split("?")[0] for x in url_list]
    for url in url_list:
        name = url.split("_")[1]
        download_pdf(url, f"{name}.pdf")
