import os
import socket

ip_address = socket.gethostbyname(socket.gethostname())
port = 49154
length_header = 64
length_chunk = 2**20

log_dir = os.path.join(os.path.expanduser('~'), "log", "lsl-classifier-erp")

#clf = 