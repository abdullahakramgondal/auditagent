"""The production server: the API under /api and the built front end at /.

Run (project root):  uvicorn auditagent.api.web:create_web_app --factory
Build the front end first:  cd auditagent-web && npm run build
The front end has its own address /audits/<id>, the same as the API, so the API lives under /api here.
Environment: AUDITAGENT_WEB_DIR (default auditagent-web/dist), plus the settings of the API itself.
"""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from auditagent.api.app import create_app
from auditagent.api.jobs import JobManager

DEFAULT_WEB_DIR = Path(__file__).resolve().parents[3] / "auditagent-web" / "dist"


class SpaFiles(StaticFiles):
    """Static files where an address that is not a file (/history, /audits/abc) gives index.html.

    The routes of the front end are drawn in the browser, so a reload on one of them must still
    open the app. A missing file under /assets stays a 404: that is a broken build, not a route.
    """

    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            # On Windows the path comes with backslashes: assets\missing.js
            if exc.status_code == 404 and not path.replace("\\", "/").startswith("assets/"):
                return await super().get_response("index.html", scope)
            raise


def create_web_app(manager: JobManager | None = None, web_dir: Path | None = None) -> FastAPI:
    """The API at /api and the built front end everywhere else. Tests pass a manager and a folder."""
    folder = Path(web_dir or os.environ.get("AUDITAGENT_WEB_DIR", DEFAULT_WEB_DIR))
    if not (folder / "index.html").is_file():
        raise RuntimeError(
            f"The front end is not built: {folder / 'index.html'} is missing. "
            "Run: cd auditagent-web && npm run build"
        )
    app = FastAPI(title="AuditAgent AI", docs_url=None, redoc_url=None, openapi_url=None)
    app.mount("/api", create_app(manager))  # the API docs are at /api/docs
    app.mount("/", SpaFiles(directory=folder, html=True))
    return app
