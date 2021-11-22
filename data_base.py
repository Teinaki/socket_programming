from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

engine = create_engine('sqlite:///assn2-chat-server-Teinaki.db', future=True, connect_args={'check_same_thread': False})
Base = declarative_base()

class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    message = relationship("Message", back_populates="user")

class Message(Base):
    __tablename__ = 'message'
    id = Column(Integer, primary_key=True)
    msg = Column(String)
    msg_to = Column(Integer, ForeignKey('user.id'))
    msg_from = Column(String)
    sent = Column(String)
    user = relationship("User", back_populates="message")

class Login(Base):
    __tablename__ = 'login'
    id = Column(Integer, primary_key=True)
    user = Column(Integer, ForeignKey('user.id'))
    port = Column(Integer)

Base.metadata.create_all(engine)