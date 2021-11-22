import struct
import json
import io
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime

import data_base

class MessageServer:
    def __init__(self, data):
        self.data = data
        self._header_len = None
        self.header = None
        self.request = None
        self.needed_response = False
        self.created_response = False
        self.send_response = b''
        self.session = Session(data_base.engine)
        self.user = None


    def read(self):
        if self._header_len is None:
            self._preheader()

        if self._header_len:
            if self.header is None:
                self._header()

        if self.header:
            if self.request is None:
                self._request()

    def _preheader(self):
        if len(self.data) >= 2:
            self._header_len = struct.unpack(">H", self.data[:2])[0]
            self.data = self.data[2:]
            print(self.data)
            print(self._header_len)

    def _header(self):
        headlen = self._header_len
        if len(self.data) >= headlen:
            self.header = self._decode(self.data[:headlen], "utf-8")
            self.data = self.data[headlen:] #slice so self.data will only have header
            for required in ("Content-type","Content-encoding",):
                if required not in self.header:
                    raise ValueError(f'Missing required header "{required}".') #check if client is sending correct headers
            print(self.data)
            print(self.header)

    def _request(self):
        content_len = self.header["Content-length"]
        if not len(self.data) >= content_len:
            return  #if content length in header 
        data = self.data[:content_len] #slice so remaining data is just content, no header
        self.data = self.data[content_len:] #slice so its empty
        encoding = self.header["Content-encoding"] 
        self.request = self._decode(data, encoding)
        print("received request", repr(self.request))
               
        self.needed_response = True

    def _decode(self, data, encoding):
        temp = io.TextIOWrapper(io.BytesIO(data), encoding=encoding)
        decoded = json.load(temp)
        return decoded

    def write(self):
        if self.request:
            if not self.created_response:
                self._respond() #we create a response if none is created yet

    def _respond(self):
        if self.header["Content-type"] == "application/json":
            action = self.request.get("action") #action that the user input. login, send, get, logout.
            print(action)
            if action == "login":
                query = self.request.get("params") #this is filler data, needs true database for users.
                name = query["name"]
                self.action_login(name)
                print(name)
                content = {"reply": f"{name} has logged in"}
            elif action == "send_messages":
                query = self.request.get("params")
                message = query["messages"]
                for msg in message:
                    self.action_send_messages(msg["msg"], msg["to"])
                content = {"reply": f"Messages have been sent"}
            else:
                content = {"ERROR": "Invalid Action!"} #if action is invalid I'll add it to content and send it back
            content_encoding = "utf-8"
            response = {
                "content_bytes": json.dumps(content, ensure_ascii=False).encode(content_encoding),
                "content_type": "application/json",
                "content_encoding": content_encoding,
            }
            message = self._message(**response)
            self.needed_response = False
            self.created_response = True
            self.send_response += message #after we have our message all set we can save it and use it in the Server.py

    def _message(self, *, content_bytes, content_type, content_encoding):
        header = {
            "Content-type": content_type,
            "Content-encoding": content_encoding,
            "Content-length": len(content_bytes),
        }
        header_bytes = json.dumps(header, ensure_ascii=False).encode(content_encoding)
        message_head = struct.pack(">H", len(header_bytes))
        message = message_head + header_bytes + content_bytes #add pieces of our message all together ready to send
        return message

    def action_login(self, username):
        query = select(data_base.User).where(data_base.User.name == username)
        user = self.session.execute(query).scalars().first() #if query empty create a user
        if not user:
            new_user = data_base.User(name=username) #create a user on the database
            self.session.add(new_user)
        login = data_base.Login(user=username) #create the instance of a log in
        self.session.add(login)
        self.session.commit()

        self.user = username #set our user for this thread instance of the MessageServer as the logged in user

    def action_send_messages(self, msg, msg_to):
        new_message = data_base.Message(msg=msg, msg_to=msg_to, msg_from = self.user, sent = datetime.now())
        self.session.add(new_message)
        self.session.commit()