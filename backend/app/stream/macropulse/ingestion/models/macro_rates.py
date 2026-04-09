from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.stream.macropulse.ingestion.db.session import Base


class MacroRate(Base):
    __tablename__ = "macro_rates"
    __table_args__ = (UniqueConstraint("source", "date", name="uq_macro_rates_source_date"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    region: Mapped[str] = mapped_column(String(8), default="IN", nullable=False)
    repo_rate_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    gsec_10y_yield_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    cpi_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    wpi_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Day 3 — GCC columns
    saibor_3m_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    saibor_6m_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    eibor_1m_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    eibor_3m_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    confidence_tier: Mapped[str] = mapped_column(String(32), default="primary", nullable=False)
