# !/usr/bin/env python3
import json
import base64
import contextlib
import socket
import ssl

EMAIL = "mail@example.com"
PASSWORD = "password"


class SMTPLetter:
    separator = b'someseparator'

    def __init__(self, to: list, subject: str):
        if len(to) == 0:
            raise ValueError("Hey, where I should send this?")
        if not subject:
            raise ValueError("Can't send letter without subject")
        self.to = to
        self.subject = subject
        self.letter_bytes = self._get_letter_start()

    def _get_letter_start(self):
        b = b''
        b += b'from: ' + EMAIL.encode(encoding='ascii') + b'\n'
        b += b'to: ' + self.to[0].encode(encoding='ascii') + b'\n'
        b += b'Subject: '
        parts = trim_and_encode_str(self.subject, 60)
        for i in range(len(parts)):
            if i != 0:
                b += b'\t'
            b += parts[i] + b'\n'
        b += b'MIME-Version: 1.0\n'
        b += b'Content-Type: multipart/mixed; boundary="' + self.separator + b'\n\n'
        return b

    def add_text(self, text: str):
        b = b'--' + self.separator+b'\n'
        b += b'Content-Type: text/plain; charset="UTF-8"\n'
        b += b'Content-Transfer-Encoding: base64\n'
        b += b'\n'
        b += base64.encodebytes(text.encode(encoding='utf-8'))
        #b += b'\n'
        self.letter_bytes += b

    def add_attachment_content(self, name: str,
                               content_type=b"application/octet-stream"):
        b = b'--' + self.separator+b'\n'
        b += b'Content-Type: ' + content_type + b';\n'
        name_encoded = trim_and_encode_str(name, 78)
        for i in range(len(name_encoded)):
            b += b'\t'
            if i == 0:
                b += b'name="'
            b += name_encoded[i]
            if i == len(name_encoded) - 1:
                b += b'"'
            b += b'\n'
        b += b'Content-Disposition: attachment;\n'
        name_encoded = trim_and_encode_str(name, 78)
        for i in range(len(name_encoded)):
            b += b'\t'
            if i == 0:
                b += b'filename="'
            b += name_encoded[i]
            if i == len(name_encoded) - 1:
                b += b'"'
            b += b'\n'
        b += b'Content-Transfer-Encoding: base64\n'
        b += b'\n'
        with open(name, "rb") as f:
            b += base64.encodebytes(f.read())
        b += b'\n'
        self.letter_bytes += b

    def add_ending(self):
        self.letter_bytes += b'--' + self.separator + b'--\n.\n'


def trim_and_encode_str(string, length):
    s = list(trim(base64.b64encode(string.encode(encoding='utf-8')), length))
    result = list()
    for i in range(len(s)):
        result.append(
            b'=?UTF-8?B?' + s[i] + (
                b'==?=' if i == 0 and len(s) > 1 else b'?='))
    return result


def trim(b, length):
    while len(b) > length:
        yield b[:length]
        b = b[length:]
    if len(b) > 0:
        yield b


def main():
    to, subject, attachments = read_config()
    letter = SMTPLetter(to, subject)
    with open("conf/letter.txt", encoding='utf-8') as f:
        letter.add_text(f.read())
    for att in attachments:
        letter.add_attachment_content(att)
    letter.add_ending()

    sock = socket.socket()
    sock.connect(('smtp.example.com', 25))
    sock = ssl.wrap_socket(sock)

    with contextlib.closing(sock):
        def send_and_rcv(bytes_):
            sock.sendall(bytes_)
            print(sock.recv(1024).decode())

        print(sock.recv(1024).decode())

        send_and_rcv(b'EHLO ' + EMAIL.encode(encoding='ascii') + b'\n')
        send_and_rcv(b'AUTH LOGIN\n')
        s = EMAIL.encode(encoding='ascii')
        send_and_rcv(base64.b64encode(s) + b'\n')
        s = PASSWORD.encode(encoding='ascii')
        send_and_rcv(base64.b64encode(s) + b'\n')
        send_and_rcv(b'MAIL FROM: ' + EMAIL.encode(encoding='ascii') + b'\n')
        for t in to:
            send_and_rcv(b'RCPT TO: ' + t.encode(encoding='ascii') + b'\n')
        send_and_rcv(b'DATA\n' + letter.letter_bytes)
        send_and_rcv(b'QUIT')


def read_config():
    with open("conf/config.json", encoding='utf-8') as f:
        obj = json.load(f)
    return obj["to"], obj["Subject"], obj["Attachments"]


if __name__ == '__main__':
    main()
