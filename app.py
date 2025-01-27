__version__ = "1.1.1"

import os

from motor.motor_asyncio import AsyncIOMotorClient
from sanic import Sanic, response
from sanic.exceptions import NotFound
from jinja2 import Environment, FileSystemLoader

from core.models import LogEntry


if "URL_PREFIX" in os.environ:
    print("Using the legacy config var `URL_PREFIX`, rename it to `LOG_URL_PREFIX`")
    prefix = os.environ["URL_PREFIX"]
else:
    prefix = os.getenv("LOG_URL_PREFIX", "/logs")

if prefix == "NONE":
    prefix = ""

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    MONGO_URI = os.environ["CONNECTION_URI"]

subdir = os.getenv("SUBDIR", "")
if subdir:
    subdir = "/" + subdir

app = Sanic(__name__)
app.static(subdir + "/static", "./static")

jinja_env = Environment(loader=FileSystemLoader("templates"))


def render_template(name, *args, **kwargs):
    template = jinja_env.get_template(name + ".html")
    kwargs["subdir"] = subdir
    return response.html(template.render(*args, **kwargs))


app.ctx.render_template = render_template


@app.listener("before_server_start")
async def init(app, loop):
    app.ctx.db = AsyncIOMotorClient(MONGO_URI).modmail_bot


@app.exception(NotFound)
async def not_found(request, exc):
    return render_template("not_found")


@app.get(subdir + "/")
async def index(request):
    return render_template("index")


@app.get(subdir + prefix + "/raw/<key>")
async def get_raw_logs_file(request, key):
    """Returns the plain text rendered log entry"""
    document = await app.ctx.db.logs.find_one({"key": key})

    if document is None:
        raise NotFound

    log_entry = LogEntry(app, document)

    return log_entry.render_plain_text()


@app.get(subdir + prefix + "/<key>")
async def get_logs_file(request, key):
    """Returns the html rendered log entry"""
    document = await app.ctx.db.logs.find_one({"key": key})

    if document is None:
        raise NotFound

    log_entry = LogEntry(app, document)

    return log_entry.render_html()


if __name__ == "__main__":
    app.run(
        host=os.getenv("HOST", "0.0.0.0"),
        port=os.getenv("PORT", 8000),
        debug=bool(os.getenv("DEBUG", False)),
    )
