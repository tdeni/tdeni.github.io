import datetime as dt
import shutil
import sys
from http.server import HTTPServer
from pathlib import Path

import typer
from jinja2 import Environment, FileSystemLoader, select_autoescape
from slugify import slugify
from typing_extensions import Annotated
from watchdog.events import FileSystemEvent, PatternMatchingEventHandler
from watchdog.observers import Observer

from tools import md
from tools.common import base_path
from tools.path import collect_posts, resolve_post_path
from tools.serve import HTTPRequestHandler

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

    build_dir = base_path.joinpath("www")
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir()

    shutil.copytree(base_path.joinpath("assets"), build_dir.joinpath("assets"))
    sys.stderr.write("Copy assets\n")
    sys.stderr.write("=============\n")

    posts_dir = base_path.joinpath("posts")
    posts = collect_posts(posts_dir)
    if not draft:
        posts = [p for p in posts if p.meta.published is True]

    posts_ctx = []
    for p in posts:
        p.render(env)
        posts_ctx.append(p.context)
    sys.stderr.write("=============\n")

    ctx = {"posts": posts_ctx}

    pages_dir = base_path.joinpath("pages")

    def recusive_pages(path: Path = pages_dir):
        fp, dirs, files = next(path.walk())
        for file in files:
            template_path = fp.joinpath(file).relative_to(pages_dir)
            tmpl = env.get_template(str(template_path))
            content = tmpl.render(ctx)

            target = build_dir.joinpath(template_path).with_suffix("")
            with open(target, "w", encoding="utf-8") as f:
                sys.stderr.write(f"Create file - {target.relative_to(build_dir)}\n")
                f.write(content)
        for d in dirs:
            target = fp.joinpath(d)
            build_dir.joinpath(target.relative_to(pages_dir)).mkdir(
                parents=True, exist_ok=True
            )
            recusive_pages(target)

    recusive_pages()
    sys.stderr.write("=============\n")
    sys.stderr.write("Build finished\n\n")


@app.command()
def serve(
    host: str = "localhost",
    port: int = 3000,
    draft: Annotated[bool, typer.Option("--draft")] = False,
):
    def _build(event: FileSystemEvent):
        path_parts = event.src_path.split("/")
        if len(path_parts) > 1:
            if path_parts[1] == "www" or path_parts[1].startswith("."):
                return
        try:
            build(draft=draft)
        except Exception as e:
            sys.stderr.write(str(e))

    build(draft=draft)

    handler = PatternMatchingEventHandler(["*"], [], True, True)
    for attr in ("on_created", "on_deleted", "on_modified", "on_moved"):
        setattr(handler, attr, _build)

    observer = Observer()
    observer.schedule(handler, ".", recursive=True)
    observer.start()
    try:
        httpd = HTTPServer((host, port), HTTPRequestHandler)
        httpd.serve_forever()
    except KeyboardInterrupt:
        observer.stop()
        observer.join()


if __name__ == "__main__":
    app()
