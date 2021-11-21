import socket
import struct
import json
import io

class MessageServer:
    def __init__(self, data):
        self.data = data
        self._header_len = None
        self.header = None
        self.request = None


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
        print(f"THIS IS DATA: {self.data}")
        print("received request", repr(self.request))

    def _decode(self, data, encoding):
        tiow = io.TextIOWrapper(io.BytesIO(data), encoding=encoding)
        decoded = json.load(tiow)
        tiow.close()
        return decoded