from datetime import datetime
from typing import Callable, Any
from typing_extensions import Self
from pydantic import BaseModel
from .atom_base import Media, Text, Image, AtomEntry, AtomFeed


class MajorType:
    MAJOR_TYPE_NONE = 'MAJOR_TYPE_NONE'
    MAJOR_TYPE_UGC_SEASON = 'MAJOR_TYPE_UGC_SEASON'
    MAJOR_TYPE_ARTICLE = 'MAJOR_TYPE_ARTICLE'
    MAJOR_TYPE_DRAW = 'MAJOR_TYPE_DRAW'
    MAJOR_TYPE_ARCHIVE = 'MAJOR_TYPE_ARCHIVE'
    MAJOR_TYPE_LIVE_RCMD = 'MAJOR_TYPE_LIVE_RCMD'
    MAJOR_TYPE_COMMON = 'MAJOR_TYPE_COMMON'
    MAJOR_TYPE_PGC = 'MAJOR_TYPE_PGC'
    MAJOR_TYPE_COURSES = 'MAJOR_TYPE_COURSES'
    MAJOR_TYPE_MUSIC = 'MAJOR_TYPE_MUSIC'
    MAJOR_TYPE_OPUS = 'MAJOR_TYPE_OPUS'
    MAJOR_TYPE_UNKNOWN = 'MAJOR_TYPE_UNKNOWN'


def enum_register(enum_value: str):
    def wrapper(func):
        def inner(*args, **kwargs):
            return func(*args, **kwargs)
        inner.enum_value = enum_value
        return inner
    return wrapper


def get_chain_node(root: dict, *names) -> Any | None:
    ref = root
    for name in names:
        if type(root) is dict and name in ref:
            ref = ref[name]
        else:
            return None
    return ref


class MajorExtractResult(BaseModel):
    media_list: list[Media]
    title: str | None = None
    summary: str | None = None


class MajorExtractor:
    _instance: Self | None = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(MajorExtractor, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        self.type_map: dict[str, Callable[[dict], MajorExtractResult]] = dict()
        for x in dir(self):
            obj = getattr(self, x)
            if 'enum_value' in dir(obj):
                self.type_map[obj.enum_value] = obj

    def extract(self, major: dict) -> MajorExtractResult:
        type_str = major.get('type')
        if type_str in self.type_map:
            return self.type_map[type_str](major)
        else:
            return self.type_map[MajorType.MAJOR_TYPE_UNKNOWN](major)

    @staticmethod
    @enum_register(MajorType.MAJOR_TYPE_NONE)
    def _none_type(_major: dict) -> MajorExtractResult:
        """
        失效动态
        :param _major:
        :return:
        """
        return MajorExtractResult(
            media_list=[Text(text="动态已失效。")]
        )

    @staticmethod
    @enum_register(MajorType.MAJOR_TYPE_UGC_SEASON)
    def _ugc_season(_major: dict) -> MajorExtractResult:
        """
        合集信息
        :param _major:
        :return:
        """
        return MajorExtractResult(
            media_list=[Text(text="暂未实现。（合集信息）")]
        )

    @staticmethod
    @enum_register(MajorType.MAJOR_TYPE_ARTICLE)
    def _article(_major: dict) -> MajorExtractResult:
        """
        专栏类型
        :param _major:
        :return:
        """
        return MajorExtractResult(
            media_list=[Text(text="暂未实现。（专栏类型）")]
        )

    @staticmethod
    @enum_register(MajorType.MAJOR_TYPE_DRAW)
    def _draw(_major: dict) -> MajorExtractResult:
        """
        带图动态
        :param _major:
        :return:
        """
        return MajorExtractResult(
            media_list=[Text(text="暂未实现。（带图动态）")]
        )

    @staticmethod
    @enum_register(MajorType.MAJOR_TYPE_ARCHIVE)
    def _archive(_major: dict) -> MajorExtractResult:
        """
        视频信息
        :param _major:
        :return:
        """
        return MajorExtractResult(
            media_list=[Text(text="暂未实现。（视频信息）")]
        )

    @staticmethod
    @enum_register(MajorType.MAJOR_TYPE_LIVE_RCMD)
    def _live_rcmd(_major: dict) -> MajorExtractResult:
        """
        直播状态
        :param _major:
        :return:
        """
        return MajorExtractResult(
            media_list=[Text(text="暂未实现。（直播状态）")]
        )

    @staticmethod
    @enum_register(MajorType.MAJOR_TYPE_COMMON)
    def _common(_major: dict) -> MajorExtractResult:
        """
        一般类型
        :param _major:
        :return:
        """
        return MajorExtractResult(
            media_list=[Text(text="暂未实现。（一般类型）")]
        )

    @staticmethod
    @enum_register(MajorType.MAJOR_TYPE_PGC)
    def _pgc(_major: dict) -> MajorExtractResult:
        """
        剧集信息
        :param _major:
        :return:
        """
        return MajorExtractResult(
            media_list=[Text(text="暂未实现。（剧集信息）")]
        )

    @staticmethod
    @enum_register(MajorType.MAJOR_TYPE_COURSES)
    def _courses(_major: dict) -> MajorExtractResult:
        """
        课程信息
        :param _major:
        :return:
        """
        return MajorExtractResult(
            media_list=[Text(text="暂未实现。（课程信息）")]
        )

    @staticmethod
    @enum_register(MajorType.MAJOR_TYPE_MUSIC)
    def _music(_major: dict) -> MajorExtractResult:
        """
        音频信息
        :param _major:
        :return:
        """
        return MajorExtractResult(
            media_list=[Text(text="暂未实现。（音频信息）")]
        )

    @staticmethod
    @enum_register(MajorType.MAJOR_TYPE_OPUS)
    def _opus(major: dict) -> MajorExtractResult:
        """
        图文动态
        :param major:
        :return:
        """
        opus = major['opus']
        title = opus.get('title')
        media_list: list[Media] = []
        if title is not None:
            media_list.append(Text(text=title, bold=True))
        summary_text = get_chain_node(opus, 'summary', 'text')
        if summary_text is not None:
            media_list.append(Text(text=summary_text))
        pics: dict | None = opus.get('pics')
        if pics is not None:
            for pic in pics:
                media_list.append(Image(src=pic['url']))
        return MajorExtractResult(
            media_list=media_list,
            title=title,
            summary=summary_text
        )

    @staticmethod
    @enum_register(MajorType.MAJOR_TYPE_UNKNOWN)
    def _not_support(_major: dict) -> MajorExtractResult:
        return MajorExtractResult(
            media_list=[Text(text="未知的动态内容类型。")]
        )


class DynamicExtractor:
    _instance: Self | None = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(DynamicExtractor, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        self.major_extractor = MajorExtractor()

    def extract(self, dynamic: dict) -> AtomEntry:
        dynamic_id = dynamic['id_str']
        modules = dynamic['modules']
        title = None
        pub_timestamp = modules['module_author']['pub_ts']
        pub_str = datetime.fromtimestamp(float(pub_timestamp)).strftime('%Y-%m-%dT%H:%M:%S+08:00')

        media_list: list[Media] = []

        desc = modules['module_dynamic']['desc']
        if desc is not None:
            media_list.append(Text(text=desc['text']))
            title = desc['text'] if title is None else title

        # orig
        if dynamic['type'] == 'DYNAMIC_TYPE_FORWARD':
            orig = dynamic['orig']
            orig_author = orig['modules']['module_author']['name']
            media_list.append(Text(text=f'转发自@{orig_author}'))
            major_extract_result = self.major_extractor.extract(orig['modules']['module_dynamic']['major'])
            media_list.extend(major_extract_result.media_list)
            title = major_extract_result.title if title is None else title
            title = major_extract_result.summary if title is None else title
            title = '转发动态' if title is None else title if title == '转发动态' else f'{title} @转发动态'
        else:
            major = modules['module_dynamic']['major']
            major_extract_result = self.major_extractor.extract(major)
            media_list.extend(major_extract_result.media_list)
            title = major_extract_result.title if title is None else title
            title = major_extract_result.summary if title is None else title

        # at bottom
        if modules['module_dynamic']['additional'] is not None:
            media_list.append(Text(text="卡片信息。（暂未实现）"))

        content = ''.join([e.html() for e in media_list])

        return AtomEntry(
            title='未提取成功，若发现存在标题，请提issue反馈。' if title is None else title,
            link=f"https://t.bilibili.com/{dynamic_id}",
            eid=dynamic_id,
            updated=pub_str,
            summary='未提取成功，若发现存在标题，请提issue反馈。' if title is None else title,
            content=content
        )


def extract_dynamic(user_id: int, json_resp: dict) -> AtomFeed:
    data = json_resp['data']
    # has_more = data['has_more']
    # offset = data['offset']
    # update_num = data['update_num']

    dynamic_extractor = DynamicExtractor()
    entr_list: list[AtomEntry] = []
    for item in data['items']:
        entr_list.append(dynamic_extractor.extract(item))

    author_name: str | None = None
    if data['items']:
        author_name = get_chain_node(data['items'][0], 'modules', 'module_author', 'name')

    author_name = f'用户{user_id}' if author_name is None else author_name
    atom_feed = AtomFeed(
        title=f'{author_name}的动态',
        link=f'/bilibili/dynamic?user_id={user_id}',
        updated=datetime.now().strftime('%Y-%m-%dT%H:%M:%S+08:00'),
        authors=['VIILing'],
        fid=f'https://space.bilibili.com/{user_id}',
        entry_list=entr_list
    )
    return atom_feed
