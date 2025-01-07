from logging import Logger

from init import AbsCacheProxy
from pixivpy3 import AppPixivAPI, PixivError

_AApi: AppPixivAPI | None = None


class FetchError(Exception):
    pass


def update_aapi(logger: Logger, cache_proxy: AbsCacheProxy) -> AppPixivAPI | None:

    refresh_token = cache_proxy.get('pixiv_refresh_token')
    if refresh_token is None:
        cache_proxy.set('pixiv_refresh_token', '')
        return None
    else:
        if refresh_token == b'':
            return None
        else:
            pass

    logger.info(f'Start login to pixiv')
    api = AppPixivAPI(proxies={'http': 'http://127.0.0.1:10809', 'https': 'http://127.0.0.1:10809'})
    # api = AppPixivAPI()
    try:
        api.auth(refresh_token=refresh_token.decode())
    except PixivError:
        return None
    global _AApi
    _AApi = api
    logger.info('Successfully login to pixiv.')
    return api


def get_aapi():
    return _AApi
