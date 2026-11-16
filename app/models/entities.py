from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Tarif(Base):
    __tablename__ = 'tarif'
    __table_args__ = (
        CheckConstraint('internet BETWEEN 0 AND 100000'),
        CheckConstraint('count_minutes BETWEEN 0 AND 10000'),
        CheckConstraint('count_sms BETWEEN 0 AND 10000'),
        CheckConstraint('salary BETWEEN 0 AND 100000000'),
        {'sqlite_autoincrement': True},
    )

    id_tarif: Mapped[int] = mapped_column(primary_key=True)
    tarif_name: Mapped[str] = mapped_column(String(100), unique=True)
    internet: Mapped[int]
    count_minutes: Mapped[int]
    count_sms: Mapped[int]
    salary: Mapped[int]


class Client(Base):
    __tablename__ = 'client'

    number_phone: Mapped[str] = mapped_column(String(12), primary_key=True)
    id_tarif: Mapped[int | None] = mapped_column(ForeignKey('tarif.id_tarif', ondelete='RESTRICT'), index=True)
    lastname: Mapped[str] = mapped_column(String(50))
    firstname: Mapped[str] = mapped_column(String(50))
    patronymic_name: Mapped[str] = mapped_column(String(50), default='')
    date_birthday: Mapped[str] = mapped_column(String(10))
    pasport_serial: Mapped[str] = mapped_column(String(4))
    pasport_number: Mapped[str] = mapped_column(String(6))
    date_issue: Mapped[str] = mapped_column(String(10))
    tarif: Mapped[Tarif | None] = relationship(lazy='joined')


class Employee(Base):
    __tablename__ = 'employee'
    __table_args__ = (CheckConstraint("role IN ('manager', 'admin')"), {'sqlite_autoincrement': True})

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(10))
    full_name: Mapped[str] = mapped_column(String(200))


class AuthSession(Base):
    __tablename__ = 'auth_session'

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey('employee.id', ondelete='CASCADE'), index=True)
    expires_at: Mapped[int] = mapped_column(BigInteger, index=True)
