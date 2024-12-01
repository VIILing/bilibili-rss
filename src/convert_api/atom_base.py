from pydantic import BaseModel, Field


class Media(BaseModel):
    def html(self) -> str:
        pass


class Text(Media):
    text: str
    bold: bool = Field(False, description="是否需要加粗文本")

    def html(self):
        content = self.text
        if self.bold:
            content = f'<b>{content}</b>'
        return f"<p>{content}</p>"


class Image(Media):
    src: str

    def html(self):
        return f'<img src="{self.src}"/>'


class Video(Media):
    aid: str
    bid: str
    cover: str
    desc: str
    duration: str
    jump_url: str
    title: str

    def html(self):
        return f"""
<p>投稿了视频</p>
<p><b>{self.title}</b></p>
<p>{self.desc}</p>
<p>视频暂不支持直接播放。</p>
<img src="{self.cover}"/>
""".strip()


class AtomEntry(BaseModel):
    title: str = Field(..., description='title')
    link: str = Field(..., description='entry link')
    eid: str = Field(..., description='entry id')
    updated: str = Field(..., description='YYYY-MM-DDTHH:MM:SSZ')
    summary: str = Field(..., description='summary when no expand')
    content: str = Field(..., description='full content')

    def xml(self):
        return f"""
<entry>
    <title>{self.title}</title>
    <link href="{self.link}"/>
    <id>https://t.bilibili.com/{self.eid}</id>
    <updated>{self.updated}</updated>
    <summary>{self.summary}</summary>
    <content type="html"><![CDATA[{self.content}]]></content>
</entry>
""".strip()


class AtomFeed(BaseModel):
    title: str
    link: str
    updated: str
    authors: list[str]
    fid: str
    entry_list: list[AtomEntry]

    def xml(self):
        authors = '\n'.join([f'<name>{n}</name>' for n in self.authors])
        entry_list = '\n'.join([e.xml() for e in self.entry_list])
        return f"""
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>{self.title}</title>
  <link href="{self.link}" />
  <updated>{self.updated}</updated>
  <author>{authors}</author>
  <id>{self.fid}</id>
  {entry_list}
</feed>
""".strip()
