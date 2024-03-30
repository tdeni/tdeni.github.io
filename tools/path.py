import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Self

import markdown
from jinja2 import Environment

from tools import md
from tools.common import base_path


def resolve_post_path(name: str, as_dir: bool) -> Path:
    if as_dir:
        dest = base_path.joinpath(f"posts/{name}")
        dest.mkdir(parents=True, exist_ok=True)
        return dest.joinpath("index.md")

    return base_path.joinpath(f"posts/{name}.md")


class lazyproperty(object):
    def __init__(self, fget):
        self.fget = fget

    def __get__(self, instance, cls):
        value = self.fget(instance)
        setattr(instance, self.fget.__name__, value)
        return value


@dataclass
class Post:
    path: Path
    content: str
    meta: md.Header
    files: list[Path]
    next: Self | None = None
    previous: Self | None = None

    @lazyproperty
    def context(self):
        content_html = markdown.markdown(self.content)
        url = (
            str(self.rel_path.parent)
            if self.rel_path.name == "index.md"
            else str(self.rel_path.with_suffix(""))
        )

        return {
            "page": {
                "title": self.meta.title,
                "content": content_html,
                "tags": self.meta.tags,
                "created_at": self.meta.created_at,
                "published_at": self.meta.published_at,
                "published": self.meta.published,
            },
            "url": f"/posts/{url}",
            "next": self.next if self.next else None,
            "previous": self.previous if self.previous else None,
        }

    @property
    def rel_path(self) -> Path:
        return self.path.relative_to(base_path.joinpath("posts"))

    def render(self, env: Environment):
        tmpl = env.get_template(self.meta.layout)
        render = tmpl.render(self.context)

        target_path = (
            base_path.joinpath("www/posts").joinpath(self.rel_path).with_suffix(".html")
        )
        target_dir = target_path.parent
        target_dir.mkdir(parents=True, exist_ok=True)

        with open(target_path, "w", encoding="utf-8") as f:
            f.write(render)
        for fp in self.files:
            if fp.is_dir():
                shutil.copytree(fp, target_dir.joinpath(fp.name))
            else:
                shutil.copy(fp, target_dir)


def collect_posts(posts_dir: Path) -> list[Post]:
    posts: list[Post] = []
    for fp in posts_dir.iterdir():
        if fp.is_dir():
            files = [file for file in fp.iterdir() if file.name != "index.md"]
            fp = fp.joinpath("index.md")
        else:
            if not fp.name.endswith(".md"):
                continue
            files = []

        with open(fp, encoding="utf-8") as f:
            meta, content = md.read(f)
        posts.append(Post(fp, content, meta, files))
    posts.sort(key=lambda p: p.meta.published_at, reverse=True)
    for i, post in enumerate(posts):
        if i != 0:
            post.previous = posts[i - 1]
        if len(posts) - 1 > i:
            post.next = posts[i + 1]
    return posts
