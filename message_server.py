import socket
import struct
import json
import io

class MessageServer:
    def __init__(self, data):
        self.data = data
        self._send_buffer = b""
        self._jsonheader_len = None
        self.jsonheader = None
        self.request = None
        self.response_created = False


    def read(self):
        if self._jsonheader_len is None:
            self.process_protoheader()

        if self._jsonheader_len is not None:
            if self.jsonheader is None:
                self.process_jsonheader()

        if self.jsonheader:
            if self.request is None:
                self.process_request()

    def process_protoheader(self):
        hdrlen = 2
        if len(self.data) >= hdrlen:
            self._jsonheader_len = struct.unpack(
                ">H", self.data[:hdrlen]
            )[0]
            self.data = self.data[hdrlen:]
            print(self.data)
            print(self._jsonheader_len)

    def process_jsonheader(self):
        hdrlen = self._jsonheader_len
        if len(self.data) >= hdrlen:
            self.jsonheader = self._json_decode(self.data[:hdrlen], "utf-8")
            self.data = self.data[hdrlen:]
            for reqhdr in (
                "Content-type",
                "Content-encoding",
            ):
                if reqhdr not in self.jsonheader:
                    raise ValueError(f'Missing required header "{reqhdr}".')
            print(self.data)
            print(self.jsonheader)

    def process_request(self):
        content_len = self.jsonheader["Content-length"]
        if not len(self.data) >= content_len:
            return
        data = self.data[:content_len]
        self.data = self.data[content_len:]
        if self.jsonheader["Content-type"] == "application/json":
            encoding = self.jsonheader["Content-encoding"]
            self.request = self._json_decode(data, encoding)
            print("received request", repr(self.request))
        else:
            # Binary or unknown content-type
            self.request = data
            print("THIS IS THE ELSE")
            print(
                f'received {self.jsonheader["content-type"]}'
            )
        # Done reading now need to write

    def _json_decode(self, json_bytes, encoding):
        tiow = io.TextIOWrapper(
            io.BytesIO(json_bytes), encoding=encoding, newline=""
        )
        obj = json.load(tiow)
        tiow.close()
        return obj