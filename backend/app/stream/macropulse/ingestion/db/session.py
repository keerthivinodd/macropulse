import os
from contextvars import ContextVar

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

# Load .env from ops/ folder for local runs
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../ops/.env"))

POSTGRES_URL = os.getenv(
    "POSTGRES_URL",
    "postgresql+asyncpg://macropulse:macropulse@localhost:5432/macropulse",
)
INDIA_DB_URL = os.getenv("INDIA_DB_URL", POSTGRES_URL)
GCC_DB_URL = os.getenv("GCC_DB_URL", POSTGRES_URL)


def _create_sessionmaker(url: str) -> async_sessionmaker[AsyncSession]:
    # NullPool avoids cross-event-loop asyncpg connection reuse during local
    # test runs and direct script invocations on Windows.
    engine = create_async_engine(url, echo=False, pool_pre_ping=True, poolclass=NullPool)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


_ENGINE_URLS = {
    "DEFAULT": POSTGRES_URL,
    "IN": INDIA_DB_URL,
    "UAE": GCC_DB_URL,
    "SA": GCC_DB_URL,
}
_SESSIONMAKERS = {region: _create_sessionmaker(url) for region, url in _ENGINE_URLS.items()}
_SESSION_FACTORY_CTX: ContextVar[async_sessionmaker[AsyncSession] | None] = ContextVar(
    "macropulse_session_factory",
    default=None,
)


def region_to_engine_key(region: str | None) -> str:
    if region in {"UAE", "SA", "GCC"}:
        return "UAE"
    if region == "IN":
        return "IN"
    return "DEFAULT"


def get_engine(region: str = "DEFAULT"):
    return _SESSIONMAKERS[region_to_engine_key(region)].kw["bind"]


def get_engine_url(region: str = "DEFAULT") -> str:
    return _ENGINE_URLS[region_to_engine_key(region)]


def get_sessionmaker(region: str = "DEFAULT") -> async_sessionmaker[AsyncSession]:
    return _SESSIONMAKERS[region_to_engine_key(region)]


def set_session_region(region: str):
    return _SESSION_FACTORY_CTX.set(get_sessionmaker(region))


def reset_session_region(token) -> None:
    _SESSION_FACTORY_CTX.reset(token)


def AsyncSessionLocal() -> AsyncSession:
    factory = _SESSION_FACTORY_CTX.get() or get_sessionmaker("DEFAULT")
    return factory()


engine = get_engine("DEFAULT")


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
