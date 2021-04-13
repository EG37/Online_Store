import sqlalchemy
from .db_session import SqlAlchemyBase
from sqlalchemy_serializer import SerializerMixin


class Item(SerializerMixin, SqlAlchemyBase):
    __tablename__ = 'items'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    category = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('categories.id') ,nullable=True)
    description = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    special_price = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)
    special_currency = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)
    photo_name = sqlalchemy.Column(sqlalchemy.String, nullable=True)