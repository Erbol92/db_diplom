import sqlalchemy as sq
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class UserRuWords(Base):
    __tablename__ = 'userruwords'

    id = sq.Column(sq.Integer, primary_key=True)
    user_id = sq.Column(sq.Integer, sq.ForeignKey(
        'user.id'), nullable=False)
    ruword_id = sq.Column(sq.Integer, sq.ForeignKey(
        'ruword.id'), nullable=False)


class User(Base):
    __tablename__ = 'user'

    id = sq.Column(sq.Integer, primary_key=True)
    tg_id = sq.Column(sq.Integer, nullable=False, unique=True)
    words = relationship(
        'RuWord',
        secondary=UserRuWords.__tablename__,
        back_populates='users',
        cascade='all',
    )

    def __str__(self):
        return self.tg_id


class RuWord(Base):
    __tablename__ = 'ruword'

    id = sq.Column(sq.Integer, primary_key=True)
    title = sq.Column(sq.String(length=40), unique=True, nullable=False)
    true_translate = sq.Column(
        sq.String(length=40), unique=False, nullable=False)
    users = relationship(
        'User',
        secondary=UserRuWords.__tablename__,
        back_populates='words',
        cascade='all',
    )

    def __str__(self):
        return f'{self.user_id} {self.title}'


class EnWord(Base):
    __tablename__ = 'enword'

    id = sq.Column(sq.Integer, primary_key=True)
    title = sq.Column(sq.String(length=40), unique=True, nullable=False)

    def __str__(self):
        return self.title


def create_tables(engine):
    Base.metadata.create_all(engine)


def drop_tables(engine):
    Base.metadata.drop_all(engine)
