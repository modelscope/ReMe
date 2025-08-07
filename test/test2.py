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

# 全局配置
BASE_URL = "https://reportapi.eastmoney.com/report/list"
DETAIL_BASE_URL = "https://data.eastmoney.com/report/info/"

# 读取config.json获取stock_code
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)
STOCK_CODE = config.get('stock_code', '600519')
MIN_PAGES = config.get('min_pages', 20)
DOWNLOAD_DIR = config.get('download_dir', "reports_pdf")
YEARS_AGO = config.get('years_ago', 2)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

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


def fetch_jsonp_data(page_no=1):
    """
    获取研究报告列表数据
    :param page_no: 页码
    :return: 解析后的数据字典
    """
    # 计算日期
    today = datetime.today()
    end_time = today.strftime('%Y-%m-%d')
    begin_time = (today - timedelta(days=365 * YEARS_AGO)).strftime('%Y-%m-%d')

    # 检查是否存在已保存的原始数据
    raw_data_dir = "raw_data"
    raw_data_file = os.path.join(raw_data_dir, f"page_{page_no}_{STOCK_CODE}_{begin_time}_{end_time}.json")

    if os.path.exists(raw_data_file):
        print(f"使用已保存的原始数据: {raw_data_file}")
        try:
            with open(raw_data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"读取已保存数据失败: {e}")

    params = {
        "cb": "datatable6333112",
        "pageNo": page_no,
        "pageSize": 50,
        "code": STOCK_CODE,
        "industryCode": "*",
        "industry": "*",
        "rating": "*",
        "ratingchange": "*",
        "beginTime": begin_time,
        "endTime": end_time,
        "fields": "",
        "qType": 0,
        "p": page_no,
        "pageNum": page_no,
        "pageNumber": page_no,
        "_": int(time.time() * 1000)  # 使用当前时间戳
    }
    headers = {
        "User-Agent": get_random_user_agent(),
        "Referer": "https://data.eastmoney.com/"
    }
    try:
        response = requests.get(BASE_URL, params=params, headers=headers)
        response.raise_for_status()
        # 提取JSON部分
        json_str = re.search(r'\((.*)\)', response.text).group(1)
        data = json.loads(json_str)

        # 保存原始数据到本地
        if not os.path.exists(raw_data_dir):
            os.makedirs(raw_data_dir, exist_ok=True)

        with open(raw_data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"原始数据已保存: {raw_data_file}")
        return data
    except Exception as e:
        print(f"获取第{page_no}页数据失败: {e}")
        return None


def get_report_detail(info_code):
    """
    获取研究报告详情页内容
    :param info_code: 报告ID
    :return: 详情页HTML内容
    """
    # 检查是否存在已保存的详情页HTML
    detail_data_dir = "detail_data"
    detail_html_file = os.path.join(detail_data_dir, f"detail_{info_code}.html")

    if os.path.exists(detail_html_file):
        print(f"使用已保存的详情页HTML: {detail_html_file}")
        try:
            with open(detail_html_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"读取已保存详情页失败: {e}")

    url = urljoin(DETAIL_BASE_URL, f"{info_code}.html")
    headers = {
        "User-Agent": get_random_user_agent(),
        "Referer": "https://data.eastmoney.com/"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        # 保存详情页HTML原始数据
        if not os.path.exists(detail_data_dir):
            os.makedirs(detail_data_dir, exist_ok=True)

        with open(detail_html_file, 'w', encoding='utf-8') as f:
            f.write(response.text)

        print(f"详情页HTML已保存: {detail_html_file}")
        return response.text
    except Exception as e:
        print(f"获取报告详情{info_code}失败: {e}")
        return None


def parse_detail_page(html, info_code):
    """
    解析详情页获取PDF下载链接及相关信息
    :param html: 详情页HTML
    :param info_code: 报告ID
    :return: dict，包含PDF下载URL及命名所需字段
    """
    try:
        # 使用正则提取zwinfo变量
        match = re.search(r'var zwinfo\s*=\s*({.*?});', html, re.DOTALL)
        if not match:
            return None
        zwinfo = json.loads(match.group(1))

        # 保存解析后的zwinfo数据
        detail_data_dir = "detail_data"
        zwinfo_file = os.path.join(detail_data_dir, f"zwinfo_{info_code}.json")
        with open(zwinfo_file, 'w', encoding='utf-8') as f:
            json.dump(zwinfo, f, ensure_ascii=False, indent=2)

        print(f"zwinfo数据已保存: {zwinfo_file}")

        # 提取所需字段
        return {
            'attach_url': zwinfo.get('attach_url'),
            'notice_title': zwinfo.get('notice_title', ''),
            'short_name': zwinfo.get('short_name', ''),
            'notice_date': zwinfo.get('notice_date', ''),
            'source_sample_name': zwinfo.get('source_sample_name', ''),
            'attach_pages': zwinfo.get('attach_pages', '')
        }
    except Exception as e:
        print(f"解析详情页失败: {e}")
        return None


def is_pdf_complete(pdf_path, expected_pages):
    """
    检查PDF页数是否与预期一致
    :param pdf_path: PDF文件路径
    :param expected_pages: 预期页数（int）
    :return: bool
    """
    try:
        with open(pdf_path, 'rb') as f:
            reader = PdfReader(f)
            actual_pages = len(reader.pages)
        return actual_pages == expected_pages, actual_pages
    except Exception as e:
        print(f"读取PDF页数失败: {e}")
        return False, 0


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


def process_all_reports():
    """处理所有研究报告"""
    # 获取第一页数据
    first_page_data = fetch_jsonp_data(1)
    if not first_page_data:
        return

    total_page = first_page_data.get("TotalPage", 1)
    total_reports = first_page_data.get("hits", 0)
    print(f"共发现{total_reports}篇研究报告，{total_page}页")

    # 处理所有页面
    for page in range(1, total_page + 1):
        print(f"\n正在处理第{page}/{total_page}页...")
        # 获取当前页数据
        if page == 1:
            page_data = first_page_data
        else:
            page_data = fetch_jsonp_data(page)
            if not page_data:
                continue
        # 处理每篇报告
        report_list = page_data.get("data", [])
        random.shuffle(report_list)
        for report in report_list:
            info_code = report.get("infoCode")
            if not info_code:
                continue

            # 检查页数，只有大于20页的才下载
            attach_pages = report.get("attachPages", 0)
            try:
                attach_pages = int(attach_pages)
            except (ValueError, TypeError):
                attach_pages = 0

            if attach_pages < MIN_PAGES:
                print(f"跳过页数不足的报告: {report.get('title')} (页数: {attach_pages})")
                continue

            print(f"\n处理报告: {report.get('title')} [{info_code}] (页数: {attach_pages})")
            # 获取详情页
            detail_html = get_report_detail(info_code)
            if not detail_html:
                continue
            # 解析PDF链接及命名信息
            detail_info = parse_detail_page(detail_html, info_code)
            if not detail_info or not detail_info.get('attach_url'):
                print("未找到PDF链接")
                continue
            # 组装文件名，避免重复拼接
            notice_title = detail_info.get('notice_title', '').strip().replace('/', '_')
            short_name = detail_info.get('short_name', '').strip().replace('/', '_')
            notice_date = detail_info.get('notice_date', '').replace('-', '')[:8]  # 只取年月日
            source_sample_name = detail_info.get('source_sample_name', '').strip().replace('/', '_')

            filename_parts = []
            filename_parts.append(notice_date)
            # 判断source_sample_name是否已在notice_title中
            if source_sample_name and source_sample_name not in notice_title:
                filename_parts.append(source_sample_name)
            # 判断short_name是否已在notice_title中
            if short_name and short_name not in notice_title:
                filename_parts.append(short_name)
            filename_parts.append(notice_title)
            # 分离文件名和目录
            pdf_filename = f"{'_'.join(filename_parts)}.pdf"
            pdf_subdir = f"{short_name}"

            # 判断是否为深度报告（页数大于20页）
            if attach_pages >= 20:
                pdf_subdir = f"{short_name}/深度报告"

            pdf_full_path = os.path.join(DOWNLOAD_DIR, pdf_subdir, pdf_filename)

            # 检查并创建目录
            pdf_dir = os.path.join(DOWNLOAD_DIR, pdf_subdir)
            if not os.path.exists(pdf_dir):
                os.makedirs(pdf_dir, exist_ok=True)
                print(f"创建目录: {pdf_dir}")

            # 检查文件是否已存在
            if os.path.exists(pdf_full_path):
                print(f"文件已存在，跳过下载: {pdf_full_path}")
                continue

            # 下载PDF并校验页数，最多重试3次
            max_retries = 5
            for attempt in range(1, max_retries + 1):
                download_pdf(detail_info['attach_url'], os.path.join(pdf_subdir, pdf_filename))
                # 校验PDF页数
                try:
                    expected_pages = int(detail_info.get('attach_pages', 0))
                except Exception:
                    expected_pages = 0
                is_complete = True
                actual_pages = 0
                if expected_pages > 0:
                    is_complete, actual_pages = is_pdf_complete(pdf_full_path, expected_pages)
                    if is_complete:
                        print(f"✓ PDF页数校验通过：{actual_pages}页")
                        break
                    else:
                        print(
                            f"✗ PDF页数不符：实际{actual_pages}页，预期{expected_pages}页，正在重试({attempt}/{max_retries})...")
                        # 删除不完整文件
                        try:
                            os.remove(pdf_full_path)
                        except Exception:
                            pass
                        sleep(1)
                else:
                    break
                sleep(60 * attempt)

            else:
                print(f"!!! PDF多次下载后仍不完整：{pdf_full_path}")
            # 礼貌性延迟
            sleep(30)


if __name__ == "__main__":
    import time

    start_time = time.time()

    process_all_reports()

    end_time = time.time()
    print(f"\n全部完成，耗时: {end_time - start_time:.2f}秒")