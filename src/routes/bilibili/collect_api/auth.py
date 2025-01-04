import time
import hmac
import hashlib
import urllib.parse
from hashlib import md5
from functools import reduce

import requests as rq

from .conf import UNIVERSAL_UA, FetchResult


class InitializeDynamicCookieError(Exception):
    pass


def check_resp_code(resp: rq.Response, hint: str) -> dict:
    if resp.status_code != 200:
        raise InitializeDynamicCookieError(hint)
    json_data = resp.json()
    if 'code' not in json_data and json_data['code'] != '0':
        raise InitializeDynamicCookieError(hint)
    return json_data


def hmac_sha256(key, message):
    """
    使用HMAC-SHA256算法对给定的消息进行加密
    :param key: 密钥
    :param message: 要加密的消息
    :return: 加密后的哈希值
    """
    # 将密钥和消息转换为字节串
    key = key.encode('utf-8')
    message = message.encode('utf-8')

    # 创建HMAC对象，使用SHA256哈希算
    hmac_obj = hmac.new(key, message, hashlib.sha256)

    # 计算哈希值
    hash_value = hmac_obj.digest()

    # 将哈希值转换为十六进制字符串
    hash_hex = hash_value.hex()

    return hash_hex


def get_bili_ticket():
    o = hmac_sha256("XgwSnGZ1p", f"ts{int(time.time())}")
    url = "https://api.bilibili.com/bapis/bilibili.api.ticket.v1.Ticket/GenWebTicket"
    params = {
        "key_id": "ec02",
        "hexsign": o,
        "context[ts]": f"{int(time.time())}",
        "csrf": ''
    }

    headers = {
        'user-agent': UNIVERSAL_UA
    }
    resp = rq.post(url, params=params, headers=headers)
    json_data = check_resp_code(resp, 'get bili_ticket failed')
    return json_data['data']['ticket']


def getMixinKey(orig: str):
    """
    对 imgKey 和 subKey 进行字符顺序打乱编码
    """
    mixinKeyEncTab = [
        46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
        33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
        61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
        36, 20, 34, 44, 52
    ]
    return reduce(lambda s, i: s + orig[i], mixinKeyEncTab, '')[:32]


def encWbi(params: dict, img_key: str, sub_key: str):
    """
    为请求参数进行 wbi 签名
    """
    mixin_key = getMixinKey(img_key + sub_key)
    curr_time = round(time.time())
    params['wts'] = curr_time  # 添加 wts 字段
    params = dict(sorted(params.items()))  # 按照 key 重排参数
    # 过滤 value 中的 "!'()*" 字符
    params = {
        k: ''.join(filter(lambda char: char not in "!'()*", str(v)))
        for k, v
        in params.items()
    }
    query = urllib.parse.urlencode(params)  # 序列化参数
    wbi_sign = md5((query + mixin_key).encode()).hexdigest()  # 计算 w_rid
    params['w_rid'] = wbi_sign
    return params


def getWbiKeys() -> tuple[str, str]:
    """
    获取最新的 img_key 和 sub_key
    """
    headers = {
        'User-Agent': UNIVERSAL_UA,
        'Referer': 'https://www.bilibili.com/'
    }
    resp = rq.get('https://api.bilibili.com/x/web-interface/nav', headers=headers)
    json_content = check_resp_code(resp, "get wbi keys failed")
    img_url: str = json_content['data']['wbi_img']['img_url']
    sub_url: str = json_content['data']['wbi_img']['sub_url']
    img_key = img_url.rsplit('/', 1)[1].split('.')[0]
    sub_key = sub_url.rsplit('/', 1)[1].split('.')[0]
    return img_key, sub_key


def getCookies():
    headers = {
        'User-Agent': UNIVERSAL_UA,
        'Referer': 'https://www.bilibili.com/'
    }
    resp = rq.get('https://api.bilibili.com/x/frontend/finger/spi', headers=headers)
    json_content = check_resp_code(resp, "request cookie failed")
    buvid3 = json_content['data']['b_3']
    buvid4 = json_content['data']['b_4']
    return buvid3, buvid4


def update() -> FetchResult[tuple[str, str, str, str, str]]:
    # API 收集来源于项目
    # https://github.com/SocialSisterYi/bilibili-API-collect
    #
    # 获取未登录 cookie 的 ts 示例
    # https://github.com/renmu123/biliAPI/blob/906a9dbc9d3a3dd6b44cae4b9e529dd6cac19fe0/src/user/index.ts#L79
    #
    # 获取动态的 ts 实例
    # https://github.com/renmu123/biliAPI/blob/906a9dbc9d3a3dd6b44cae4b9e529dd6cac19fe0/src/user/index.ts#L141
    #
    # 关于 dm 参数的讨论
    # https://github.com/SocialSisterYi/bilibili-API-collect/issues/868
    # https://github.com/SocialSisterYi/bilibili-API-collect/issues/868#issuecomment-1850110882
    # https://www.52pojie.cn/thread-1862056-1-1.html

    try:
        bili_ticket = get_bili_ticket()
        img_key, sub_key = getWbiKeys()
        buvid3, buvid4 = getCookies()
        print('Sucessfully update bilibili anonymous cookie.')

        return FetchResult(ok=True, data=(bili_ticket, img_key, sub_key, buvid3, buvid4))

    except InitializeDynamicCookieError:
        return FetchResult(ok=False)
