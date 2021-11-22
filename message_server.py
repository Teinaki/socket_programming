import struct
import json
import io
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime

import data_base

PREHEADER_SIZE = 2
ENCODING = "utf-8"

class MessageServer:
    def __init__(self, data, port):
        self.data = data
        self.port = port
        self._header_len = None
        self.header = None
        self.request = None
        self.created_response = False
        self.send_response = b''
        self.session = Session(data_base.engine)
        self.user = self.logged_in_user()

    def logged_in_user(self):   
        """ 
            Find the name of the logged in user by using the port number and saved database data.
        """  
        login_query = select(data_base.Login).where(data_base.Login.port == self.port)
        login = self.session.execute(login_query).scalars().first() #we check if the login has been created before on this port
        if login:
            #if login has been created before we can access the user data using the login.user foreign key
            user_query = select(data_base.User.name).where(data_base.User.id == login.user)
            logged_in = self.session.execute(user_query).scalars().first()
            return logged_in
        return

    def read(self):
        """ 
            Go through the various stages of reading the data the client sent.
        """
        if self._header_len is None: #if header_len is none we havn't started processing
            self._preheader() #1st stage we process the preheader

        if self._header_len: #if header len is set from the preheader
            if self.header is None: #header is still unprocessed
                self._header() #2nd stage is process the header

        if self.header: #after this has processed
            if self.request is None: #no request has been given
                self._request() #we start processing what request type the client wants

    def _preheader(self):
        """ 
            Unpacks the preheader, constant size of 2 defined in chatservice
        """
        if len(self.data) >= PREHEADER_SIZE:
            self._header_len = struct.unpack(">H", self.data[:PREHEADER_SIZE])[0]
            self.data = self.data[PREHEADER_SIZE:]

    def _header(self):
        """ 
            Process the header by slicing various 
        """
        headlen = self._header_len
        if len(self.data) >= headlen:
            self.header = self._decode(self.data[:headlen], ENCODING) #decode the header
            self.data = self.data[headlen:] #slice so we leave off the header
            for required in ("Content-type","Content-encoding",):
                if required not in self.header:
                    raise ValueError(f'Missing required header "{required}".') #check if client is sending correct headers

    def _request(self):
        """ 
            Recieves the request the client sent
        """
        content_len = self.header["Content-length"]
        if not len(self.data) >= content_len:
            return  #if content length in header 
        data = self.data[:content_len] #slice so remaining data is just content, no header
        self.data = self.data[content_len:] #slice so its empty
        encoding = self.header["Content-encoding"]
        self.request = self._decode(data, encoding)
        print("received request", repr(self.request))

    def _decode(self, data, encoding):
        """ 
            Decode the data to json.
        """
        temp = io.TextIOWrapper(io.BytesIO(data), encoding=encoding)
        decoded = json.load(temp)
        return decoded

    def write(self):
        """ 
            Initiates a request to respond to the client.
        """
        if self.request: #if client has a request we can start creating a response
            if not self.created_response:
                self._respond() #we create a response if none is created yet

    def _respond(self):
        """ 
            Responds back to the client depending on the differing actions the client gave the server 
        """
        if self.header["Content-type"] == "application/json":
            action = self.request.get("action") #action that the user input. login, send, get, logout.
            print(action)
            if action == "login":
                query = self.request.get("params") #we use the passed params the client sent
                name = query["name"] #take the name they logged in with
                self.action_login(name) 
                content = {"action": "login", "result" : f"{name} has logged in", "errors" : [] }
            elif action == "send_messages":
                query = self.request.get("params")
                message = query["messages"] #take the list of messages
                for msg in message:
                    self.action_send_messages(msg["msg"], msg["to"]) #for every message create instance in db
                content = {"action" : "send_messages" , "result": f"Messages have been sent", "errors" : [] }
            elif action == "get_messages":
                messages = self.action_get_messages()
                reply = []
                for message in messages:
                    reply.append({"to": message.msg_to ,"from" : message.msg_from, "msg" : message.msg , "sent" : message.sent})
                content = {"action" : "send_messages" , "result": f"Messages have been sent", "messages": reply, "errors" : [] }
            elif action == "logout":
                self.action_logout()
                content = {"logout": f"{self.user} has successfully logged out"}
            else:
                content = {"ERROR": "Invalid Action!"} #if action is invalid I'll add it to content and send it back
            content_encoding = "utf-8"
            response = {
                "content_bytes": json.dumps(content, ensure_ascii=False).encode(content_encoding),
                "content_type": "application/json",
                "content_encoding": content_encoding,
            }
            message = self._message(**response)
            self.created_response = True
            self.send_response += message #after we have our message all set we can save it and use it in the Server.py

    def _message(self, *, content_bytes, content_type, content_encoding):
        """ 
            Builds the pieces of the message together.
        """
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
        """ 
            For the user action login, logs into user, creates the user if not already created.
        """
        query = select(data_base.User).where(data_base.User.name == username)
        user = self.session.execute(query).scalars().first() #if query empty create a user
        if not user:
            new_user = data_base.User(name=username) #create a user on the database
            self.session.add(new_user)
        user = self.session.execute(query).scalars().first()
        login = data_base.Login(user=user.id, port=self.port) #create the instance of a log in
        self.session.add(login)
        self.session.commit()

    def action_send_messages(self, msg, msg_to):
        """ 
            For the user action send message, saves message data to database
        """
        new_message = data_base.Message(msg=msg, msg_to=msg_to, msg_from=self.user, sent=datetime.now())
        self.session.add(new_message) 
        self.session.commit()

    def action_get_messages(self):
        """ 
            For the user action get message, gets message data from database
        """
        query = select(data_base.Message).where(data_base.Message.msg_to == self.user) #get messages that are to the logged in user
        messages = self.session.execute(query).scalars()
        return messages

    def action_logout(self):
        """ 
            For the user action logout, delete Login data from database so port can be used for another user.
        """
        query = select(data_base.Login).where(data_base.Login.port == self.port) #delete the active user from the login db
        logged_in = self.session.execute(query).scalars().first()
        self.session.delete(logged_in)