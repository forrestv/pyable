import socket

x = socket.socket()
x.connect(("72.14.191.28", 80))
x.send("GET / HTTP/1.1\r\n\r\n")
print x.recv(1000)
