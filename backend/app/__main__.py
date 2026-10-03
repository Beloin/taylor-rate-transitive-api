import asyncio
import logging

import uvicorn

from app.config import get_settings
from app.main import app
from app.security.cert import cert_paths, generate_self_signed_cert

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run() -> None:
    settings = get_settings()
    generate_self_signed_cert()
    cert_path, key_path = cert_paths()

    http_config = uvicorn.Config(
        app,
        host=settings.http_host,
        port=settings.http_port,
        log_level="info",
    )
    servers = [uvicorn.Server(http_config)]

    if cert_path.exists() and key_path.exists():
        https_config = uvicorn.Config(
            app,
            host=settings.http_host,
            port=settings.https_port,
            ssl_certfile=str(cert_path),
            ssl_keyfile=str(key_path),
            log_level="info",
        )
        servers.append(uvicorn.Server(https_config))
    else:
        logger.warning("Certificate not found, starting HTTP only")

    await asyncio.gather(*(server.serve() for server in servers))


if __name__ == "__main__":
    asyncio.run(run())