import urllib.parse

from .conf import UNIVERSAL_UA, FetchResult
from .auth import encWbi

import httpx


async def get_space_data(client: httpx.AsyncClient, bili_ticket: str, buvid3: str, buvid4: str, img_key: str, sub_key: str, user_id: int) -> FetchResult[dict]:
    url = f'https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space'
    params = {
        'host_mid': user_id,
        'offset': '',
        'timezone_offset': '-480',
        'platform': 'web',
        "features": "itemOpusStyle,listOnlyfans,opusBigCover",
    }
    headers = {
        'user-agent': UNIVERSAL_UA,
        'Origin': 'https://space.bilibili.com',
        'referer': f'https://space.bilibili.com/{user_id}/dynamic',
        "accept-language": "en,zh-CN;q=0.9,zh;q=0.8",
    }
    # 2024.11.21 时，buvid3 和 buvid4 的值为 "buvid3" 和 "buvid4" 也可用
    cookies = {
        'bili_ticket': bili_ticket,
        'buvid3': buvid3,
        'buvid4': buvid4,
    }
    signed_params = encWbi(
        params=params,
        img_key=img_key,
        sub_key=sub_key
    )
    query = urllib.parse.urlencode(signed_params)
    # full_url = f'{url}?{query}&{DM_APPEND}'
    full_url = f'{url}?{query}'
    resp = await client.get(full_url, headers=headers, cookies=cookies)

    if resp.status_code != 200:
        return FetchResult(ok=False, msg='resp.status_code != 200')
    json_data = resp.json()
    if 'code' not in json_data and json_data['code'] != '0':
        return FetchResult(ok=False, msg='code != 0')
    return FetchResult(ok=True, data=json_data)
