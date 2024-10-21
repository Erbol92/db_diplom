import sqlalchemy as sq
from sqlalchemy.orm import declarative_base, relationship
import pandas as pd
from sqlalchemy.orm import sessionmaker
import logging

logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

Base = declarative_base()


class UserRuWords(Base):
    __tablename__ = 'userruwords'

    id = sq.Column(sq.Integer, primary_key=True, autoincrement=True)
    user_id = sq.Column(sq.Integer, sq.ForeignKey(
        'user.id'), nullable=False)
    ruword_id = sq.Column(sq.Integer, sq.ForeignKey(
        'ruword.id'), nullable=False)


class User(Base):
    __tablename__ = 'user'

    id = sq.Column(sq.Integer, primary_key=True, autoincrement=True)
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

    id = sq.Column(sq.Integer, primary_key=True, autoincrement=True)
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

    id = sq.Column(sq.Integer, primary_key=True, autoincrement=True)
    title = sq.Column(sq.String(length=40), unique=True, nullable=False)

    def __str__(self):
        return self.title


def create_tables(engine):
    Base.metadata.create_all(engine)


def drop_tables(engine):
    Base.metadata.drop_all(engine)


DSN = "postgresql://postgres:postgres@localhost:5432/translate_db"
engine = sq.create_engine(DSN)

drop_tables(engine)
create_tables(engine)

# сессия
Session = sessionmaker(bind=engine)
session = Session()

csv_files = ['enword.csv', 'ruword.csv']
for file in csv_files:
    df = pd.read_csv(file)
    df.to_sql(file.split('.')[0], con=engine, if_exists='append', index=False)
    print(f"Данные успешно загружены в таблицу `{file.split('.')[0]}`.")
