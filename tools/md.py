import datetime
from dataclasses import dataclass
from io import TextIOWrapper

import yaml


@dataclass
class Header:
    title: str | None = None
    tags: list[str] | None = None
    layout: str = "post.html.j2"
    created_at: str | datetime.datetime = datetime.datetime.min
    published_at: str | datetime.datetime = datetime.datetime.min
    published: bool | None = None

    def to_dict(self):
        return {
            "title": self.title,
            "tags": self.tags,
            "layout": self.layout,
            "created_at": self.created_at,
            "published_at": self.published_at,
            "published": self.published,
        }


def read(f: TextIOWrapper) -> tuple[Header, str]:
    content = f.read()
    if not content.startswith("---"):
        return Header(), content
    _, header, content = content.split("---", 2)
    header = yaml.safe_load(header)

    return Header(**header), content.strip("\n")


def write(f: TextIOWrapper, header: Header, content: str):
    if header:
        header_raw = yaml.safe_dump(header.to_dict())
        content = f"---\n{header_raw}\n---\n{content}\n"
    f.seek(0)
    f.write(content)
