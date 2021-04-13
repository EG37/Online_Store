import sqlalchemy
from .db_session import SqlAlchemyBase
from sqlalchemy_serializer import SerializerMixin


class Currency(SerializerMixin, SqlAlchemyBase):
    __tablename__ = 'currencies'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    logotype = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    is_integer = sqlalchemy.Column(sqlalchemy.Boolean, nullable=True)
