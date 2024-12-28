import re
import random
from pixivpy3 import AppPixivAPI
from rss_model import *
from cache_proxy import CacheLib
from init import AbsCacheProxy, get_logger


Logger = get_logger('pixiv')


def to_proxy_url(ori: str):
    x = ori.replace('https://', 'https---').replace('http://', 'http---')
    xx = f'/rss/pixiv/img_proxy/{x}'
    return xx


def user_novels(api: AppPixivAPI, user_id: int, cache_proxy: AbsCacheProxy) -> tuple[str, list[AtomEntry]]:
    jresp = api.user_novels(user_id)
    Logger.info(f'Fetch user novels done, user id: {user_id}')

    author_name: str = jresp['user']['name']

    ret: list[AtomEntry] = []
    for n in jresp['novels']:
        novel_id = n['id']
        # series_id = n['series'].get('id', -1)
        # series_name = n['series'].get('title', '')
        title = n['title']
        cover = n.get('image_urls', []).get('large', '')
        summary = n['caption'].replace('<\br />', '\n')
        tags = [e['name'] for e in n['tags']]
        pulib_time_str = n['create_date']  # 2024-12-02T01:17:58+09:00

        novel_content_cache_key = f'[Pixiv][NovelId][{novel_id}]'
        content = cache_proxy.get(novel_content_cache_key)
        if content is not None:
            content_str = content.decode()
        else:
            content_str = novel_content(api, novel_id)
            cache_proxy.set(novel_content_cache_key, content_str, lib=CacheLib.RUNTIME)

        media_list = []
        if cover != '':
            media_list.append(Image(src=to_proxy_url(cover)))
        media_list.append(Text(text=f'Tags: ' + ' '.join(tags)))
        media_list.extend(
            [Text(text=line) for line in content_str.split('\n')]
        )

        ret.append(AtomEntry(
            title=f'{author_name} 更新了小说: {title}',
            link=f'/rss/pixiv/novel_redirect/{novel_id}',
            eid=str(novel_id),
            updated=pulib_time_str,
            summary=summary,
            content=''.join([e.html() for e in media_list])
        ))

    return author_name, ret


def novel_content(api: AppPixivAPI, novel_id: str) -> str:
    jresp2 = api.webview_novel(novel_id)
    Logger.info(f'Fetch novel done, novel id: {novel_id}')

    images = jresp2['images']
    original_text: str = jresp2['text']
    replace_id_list = re.findall(r'\[uploadedimage:(\d+)]', original_text)
    replace_kv: dict[str, str] = {rid: images.get(rid, {}).get('urls', None) for rid in replace_id_list if rid in images and 'urls' in images[rid] and 'original' in images[rid]['urls']}
    text: str = original_text.replace('\t', '    ')
    v: dict
    for k, v in replace_kv.items():
        if v is None:
            continue
        if 'original' in v:
            vv = v['original']
        else:
            vv = random.choice(list(v.values()))
        vvv = to_proxy_url(vv)
        text = text.replace(k, f'\n<img src="{vvv}"/>\n')
    return text
