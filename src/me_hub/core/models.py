from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    Dialect,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Time,
    TypeDecorator,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, validates

from me_hub.core.colors import default_habit_color

HABIT_NAME_MAX_LENGTH = 64
TIMEZONE_MAX_LENGTH = 64

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def utcnow() -> datetime:
    return datetime.now(UTC)


def validate_timezone(value: str) -> str:
    if len(value) > TIMEZONE_MAX_LENGTH:
        raise ValueError(f"Unknown timezone: {value!r}")
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ValueError(f"Unknown timezone: {value!r}") from error
    return value


def normalize_habit_name(value: str) -> str:
    name = " ".join(value.split())
    if not name:
        raise ValueError("Habit name must not be blank")
    if len(name) > HABIT_NAME_MAX_LENGTH:
        raise ValueError(f"Habit name must be at most {HABIT_NAME_MAX_LENGTH} characters")
    return name


class UTCDateTime(TypeDecorator[datetime]):
    """Stores aware datetimes as naive UTC and returns them as aware UTC."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Naive datetimes are not allowed; pass a timezone-aware value")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    timezone: Mapped[str] = mapped_column(String(TIMEZONE_MAX_LENGTH))
    reminder_time: Mapped[time] = mapped_column(Time)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    habits: Mapped[list[Habit]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )

    @validates("timezone")
    def _validate_timezone(self, _key: str, value: str) -> str:
        return validate_timezone(value)

    @property
    def zone(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


class Habit(Base):
    """A tracked habit. Days are local to the owner; archived habits are not tracked from
    `archived_on` onwards."""

    __tablename__ = "habits"
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="name_not_blank"),
        Index(
            "uq_habits_user_id_name_active",
            "user_id",
            "name",
            unique=True,
            sqlite_where=text("archived_on IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(HABIT_NAME_MAX_LENGTH))
    color: Mapped[str] = mapped_column(String(7), default=default_habit_color)
    position: Mapped[int] = mapped_column(Integer, default=0)
    started_on: Mapped[date] = mapped_column(Date)
    archived_on: Mapped[date | None] = mapped_column(Date, default=None)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    user: Mapped[User] = relationship(back_populates="habits")
    checks: Mapped[list[HabitCheck]] = relationship(
        back_populates="habit", cascade="all, delete-orphan", passive_deletes=True
    )

    @validates("name")
    def _validate_name(self, _key: str, value: str) -> str:
        return normalize_habit_name(value)


class HabitCheck(Base):
    """A habit marked as done on a given local day. Absence of a row means not done."""

    __tablename__ = "habit_checks"

    habit_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("habits.id", ondelete="CASCADE"), primary_key=True
    )
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    habit: Mapped[Habit] = relationship(back_populates="checks")
