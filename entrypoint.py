import datetime as dt
import shutil
from pathlib import Path

import typer
from jinja2 import Environment, FileSystemLoader, select_autoescape
from slugify import slugify
from typing_extensions import Annotated

from tools import md
from tools.common import base_path
from tools.path import collect_posts, resolve_post_path

app = typer.Typer()


@app.command()
def post(
    title: Annotated[str, typer.Argument(help="Post title")],
    as_dir: Annotated[bool, typer.Option("--as-dir")] = False,
):
    env = Environment(
        loader=FileSystemLoader("templates"), autoescape=select_autoescape(["md"])
    )

    slug = slugify(title)
    dest = resolve_post_path(slug, as_dir)
    if dest.exists():
        raise FileExistsError()

    tmpl = env.get_template("post.md")
    content = tmpl.render(
        {
            "title": title,
            "slug": slug,
            "create_time": dt.datetime.now().isoformat(),
        }
    )
    with open(dest, "w", encoding="utf-8") as f:
        f.write(content)


@app.command()
def publish(path: Annotated[Path, typer.Argument(help="Post path")]):
    if path.is_dir():
        path = path.joinpath("index.md")
    with open(path, "r+", encoding="utf-8") as f:
        header, content = md.read(f)
        if header.published:
            return
        header.published = True
        header.published_at = dt.datetime.now().isoformat()
        md.write(f, header, content)


@app.command()
def build(draft: Annotated[bool, typer.Option("--draft")] = False):
    env = Environment(
        loader=FileSystemLoader(["layout", "pages"]),
        autoescape=select_autoescape(["md"]),
    )

    www_dir = base_path.joinpath("www")
    if www_dir.exists():
        shutil.rmtree(www_dir)
    www_dir.mkdir()

    posts_dir = base_path.joinpath("posts")
    posts = collect_posts(posts_dir)
    if not draft:
        posts = [p for p in posts if p.meta.published is True]

    posts_ctx = []
    for p in posts:
        p.render(env)
        posts_ctx.append(p.context)

    ctx = {"posts": posts_ctx}

    pages_dir = base_path.joinpath("pages")

    def recusive_pages(path: Path = pages_dir):
        fp, dirs, files = next(path.walk())
        for file in files:
            template_path = fp.joinpath(file).relative_to(pages_dir)
            tmpl = env.get_template(str(template_path))
            content = tmpl.render(ctx)

            target = www_dir.joinpath(template_path).with_suffix("")
            with open(target, "w", encoding="utf-8") as f:
                f.write(content)
        for d in dirs:
            target = fp.joinpath(d)
            www_dir.joinpath(target.relative_to(pages_dir)).mkdir(
                parents=True, exist_ok=True
            )
            recusive_pages(target)

    recusive_pages()

    shutil.copytree(base_path.joinpath("assets"), www_dir.joinpath("assets"))


if __name__ == "__main__":
    app()
