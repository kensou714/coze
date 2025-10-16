# -*- coding: utf-8 -*-
"""
抖音无水印视频解析 - Coze 插件 by Kensou714

使用 pycurl 库实现网络请求
"""

import re
import json
import pycurl
from io import BytesIO
from runtime import Args
from typings.douyin_video_url_get.douyin_video_url_get import Input, Output


# 请求头，模拟移动端访问
HEADERS = [
    'User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) EdgiOS/121.0.2277.107 Version/17.0 Mobile/15E148 Safari/604.1'
]


def curl_get(url, headers=None, follow_redirects=True):
    """使用 pycurl 发送 GET 请求"""
    buffer = BytesIO()
    header_buffer = BytesIO()

    c = pycurl.Curl()
    c.setopt(c.URL, url)
    c.setopt(c.WRITEDATA, buffer)
    c.setopt(c.HEADERFUNCTION, header_buffer.write)

    if headers:
        c.setopt(c.HTTPHEADER, headers)

    if follow_redirects:
        c.setopt(c.FOLLOWLOCATION, True)

    c.setopt(c.TIMEOUT, 30)
    c.setopt(c.CONNECTTIMEOUT, 10)

    try:
        c.perform()
        status_code = c.getinfo(c.RESPONSE_CODE)
        final_url = c.getinfo(c.EFFECTIVE_URL)
        c.close()

        body = buffer.getvalue().decode('utf-8')
        return {
            'status_code': status_code,
            'body': body,
            'final_url': final_url
        }
    except Exception as e:
        c.close()
        raise Exception(f"请求失败: {str(e)}")


def extract_video_id_from_url(url):
    """从URL中提取video_id"""
    match = re.search(r'/video/(\d+)', url)
    if match:
        return match.group(1)

    parts = url.split('?')[0].strip('/').split('/')
    for part in reversed(parts):
        if part.isdigit():
            return part

    raise ValueError("无法从URL中提取video_id")


def parse_douyin_video(share_text: str) -> dict:
    """解析抖音视频信息"""

    # 提取分享链接
    urls = re.findall(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',
        share_text
    )

    if not urls:
        raise ValueError("未找到有效的分享链接")

    share_url = urls[0]

    # 访问分享链接，获取重定向后的真实URL
    response1 = curl_get(share_url, headers=HEADERS, follow_redirects=True)

    if response1['status_code'] != 200:
        raise Exception(f"访问分享链接失败，状态码: {response1['status_code']}")

    # 提取video_id
    video_id = extract_video_id_from_url(response1['final_url'])

    # 访问标准视频页面
    standard_url = f'https://www.iesdouyin.com/share/video/{video_id}'
    response2 = curl_get(standard_url, headers=HEADERS, follow_redirects=False)

    if response2['status_code'] != 200:
        raise Exception(f"访问视频页面失败，状态码: {response2['status_code']}")

    # 从HTML中提取JSON数据
    pattern = re.compile(
        pattern=r"window\._ROUTER_DATA\s*=\s*(.*?)</script>",
        flags=re.DOTALL,
    )
    find_res = pattern.search(response2['body'])

    if not find_res or not find_res.group(1):
        raise ValueError("从HTML中解析视频信息失败")

    # 解析JSON
    json_str = find_res.group(1).strip()
    json_data = json.loads(json_str)

    # 提取视频信息
    VIDEO_ID_PAGE_KEY = "video_(id)/page"
    NOTE_ID_PAGE_KEY = "note_(id)/page"

    loader_data = json_data.get("loaderData", {})

    if VIDEO_ID_PAGE_KEY in loader_data:
        original_video_info = loader_data[VIDEO_ID_PAGE_KEY]["videoInfoRes"]
    elif NOTE_ID_PAGE_KEY in loader_data:
        original_video_info = loader_data[NOTE_ID_PAGE_KEY]["videoInfoRes"]
    else:
        raise Exception("无法从JSON中解析视频或图集信息")

    item_list = original_video_info.get("item_list", [])
    if not item_list:
        raise Exception("视频信息列表为空")

    data = item_list[0]

    # 提取各项信息
    video_play_addr = data["video"]["play_addr"]
    watermarked_url = video_play_addr["url_list"][0]
    no_watermark_url = watermarked_url.replace("playwm", "play")

    title = data.get("desc", "").strip() or f"douyin_{video_id}"
    author_info = data.get("author", {})
    statistics = data.get("statistics", {})
    video_info = data.get("video", {})

    # 构建返回结果
    result = {
        "status": "success",
        "video_id": video_id,
        "title": title,
        "author": author_info.get("nickname", ""),
        "download_url_no_watermark": no_watermark_url,
        "download_url_with_watermark": watermarked_url,
        "digg_count": statistics.get("digg_count", 0),
        "comment_count": statistics.get("comment_count", 0),
        "share_count": statistics.get("share_count", 0),
        "collect_count": statistics.get("collect_count", 0),
        "duration": video_info.get("duration", 0) / 1000.0,
        "width": video_info.get("width", 0),
        "height": video_info.get("height", 0),
        "error": ""
    }

    return result


"""
Each file needs to export a function named `handler`. This function is the entrance to the Tool.

Parameters:
args: parameters of the entry function.
args.input - input parameters, you can get test input value by args.input.share_url.
args.logger - logger instance used to print logs, injected by runtime.

Input:
- share_url (str): 抖音分享链接或包含链接的文本

Output:
- status (str): 状态 success 或 error
- video_id (str): 视频ID
- title (str): 视频标题
- author (str): 作者昵称
- download_url_no_watermark (str): 无水印下载链接
- download_url_with_watermark (str): 有水印下载链接
- digg_count (int): 点赞数
- comment_count (int): 评论数
- share_count (int): 分享数
- collect_count (int): 收藏数
- duration (float): 视频时长(秒)
- width (int): 视频宽度
- height (int): 视频高度
- error (str): 错误信息(仅在失败时)

Remember to fill in input/output in Metadata, it helps LLM to recognize and use tool.
"""
def handler(args: Args[Input]) -> Output:
    try:
        # 获取输入参数 - args.input 可能是字符串、字典或对象
        share_url = ""

        # 尝试多种方式获取 share_url
        if isinstance(args.input, str):
            # 直接就是字符串
            share_url = args.input
        elif hasattr(args.input, 'share_url'):
            # 对象属性方式
            share_url = args.input.share_url
        elif isinstance(args.input, dict):
            # 字典方式
            share_url = args.input.get("share_url", "")

        if not share_url:
            return {
                "status": "error",
                "title": "",
                "author": "",
                "download_url_no_watermark": "",
                "download_url_with_watermark": "",
                "video_id": "",
                "digg_count": 0,
                "comment_count": 0,
                "share_count": 0,
                "collect_count": 0,
                "duration": 0.0,
                "width": 0,
                "height": 0,
                "error": "缺少share_url参数"
            }

        if hasattr(args, 'logger'):
            args.logger.info(f"开始解析抖音链接: {share_url}")

        result = parse_douyin_video(share_url)

        if hasattr(args, 'logger'):
            args.logger.info(f"解析成功: {result['title']}")

        return result

    except Exception as e:
        if hasattr(args, 'logger'):
            args.logger.error(f"解析失败: {str(e)}")

        return {
            "status": "error",
            "title": "",
            "author": "",
            "download_url_no_watermark": "",
            "download_url_with_watermark": "",
            "video_id": "",
            "digg_count": 0,
            "comment_count": 0,
            "share_count": 0,
            "collect_count": 0,
            "duration": 0.0,
            "width": 0,
            "height": 0,
            "error": str(e)
        }