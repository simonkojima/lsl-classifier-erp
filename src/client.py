import os
import sys

import socket
import json

sys.path.append(os.path.join(os.path.expanduser('~'), "git", "pyerp", "src"))
import pyerp
import conf

import numpy as np

def send_sock_split(conn, msg_length, chunk_length):
    for m in range(int(msg_length/chunk_length)):
        val = data[(m*chunk_length):((chunk_length*(m+1)))]
        conn.send(val)
    conn.send(data[((m+1)*chunk_length):len(data)])

with open("epochs.json", 'r') as f:
    data = json.load(f)
    
print(data.keys())

print(len(data['epochs']))
epochs = list()
for mat in data['epochs']:
    epochs += mat
print(len(epochs))

import conf
vectorizer = conf.vectorizer

vec = vectorizer.transform(np.array(epochs))

events = list()
for val in data['events']:
    events += val
print(events)
print(len(events))

SERVER = socket.gethostbyname(socket.gethostname())
IPADDR = "127.0.0.1"
IPADDR = SERVER
PORT = 49154
header = 64
#FORMAT = ''

conn = socket.socket(socket.AF_INET)
conn.settimeout(120)
conn.connect((IPADDR, PORT))
print("connected.")

"""
conns_send(conns, len(json.dumps(json_data).encode('utf-8')).to_bytes(length_header, byteorder='little'))
conns_send(conns, json.dumps(json_data).encode('utf-8'))


msg_length = int.from_bytes(cl.recv(header), 'little')
msg = cl.recv(msg_length).decode('utf-8')
msg_json = json.loads(msg)
"""


while True:
    #input("Press Any Key to Continue.")

    msg = dict()
    msg['type'] = 'cmd'
    msg['cmd'] = 'train'
    msg['epochs'] = epochs
    msg['events'] = events

    data = json.dumps(msg).encode('utf-8')
    msg_length = len(data)
    print(msg_length)
    conn.send(msg_length.to_bytes(conf.length_header, byteorder='little'))
    
    #print(int(msg_length/sock_split) + 1)
    #for m in range(int(msg_length/sock_split) + 1):
    #    val = data[((m)*sock_split):((sock_split*(m+1)))]
    #    print(len(val))
    #    conn.send(val)
    #    if m == (int(msg_length/sock_split) + 1):
    #        conn.send(data[((m-1)*sock_split):-1])
    
    # train classifier
    send_sock_split(conn, msg_length, conf.length_chunk)
    
    msg_length = int.from_bytes(conn.recv(conf.length_header), 'little')
    print(msg_length)
    msg_json = conn.recv(msg_length).decode('utf-8')
    msg_json = json.loads(msg_json)
    
    print(msg_json)
    
    if msg_json['type'] == 'info':
        if msg_json['info'] == 'training_completed':
           pass 
    

    

    
    exit()

    
    msg = dict()
    for idx, epoch in enumerate(epochs):
        msg['type'] = 'epochs'
        msg['epochs'] = epoch
        msg['event'] = events[idx]
    conn.send(len(json.dumps(msg).encode('utf-8')).to_bytes(conf.length_header, byteorder='little'))
    conn.send(json.dumps(msg).encode('utf-8'))

    msg = dict()
    for idx, epoch in enumerate(epochs):
        msg['type'] = 'info'
        msg['info'] = 'transmission_complete'
    conn.send(len(json.dumps(msg).encode('utf-8')).to_bytes(conf.length_header, byteorder='little'))
    conn.send(json.dumps(msg).encode('utf-8'))

    
