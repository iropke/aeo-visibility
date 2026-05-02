"""v2 SQLAlchemy DeclarativeBase.

기존 v1 ``app.models.tables.Base``는 곧 제거될 레거시.
v2의 모든 ORM 모델은 이 ``Base``를 상속한다.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
