import os
import logging
import socket
import datetime
import json
import traceback

import numpy as np

from utils.std import mkdir
from utils import log


def recv_sock_split(conn, msg_length, chunk_length):
    msg = list()
    for m in range(int(msg_length/chunk_length)):
        data = conn.recv(chunk_length).decode('utf-8')
        msg.append(data)
    msg.append(conn.recv(msg_length%chunk_length).decode('utf-8'))
    return "".join(msg)[0:(msg_length)]

def train_classifier(clf, vectorizer, epochs, events, event_id):

    epochs = np.array(epochs)
    
    print(epochs.shape)
    
    Y = list()
    for event in  events:
        if event in event_id['target']:
            Y.append(1)
        elif event in event_id['nontarget']:
            Y.append(0)
        else:
            raise ValueError("Unknown event. '%s'"%(str(event)))
    print(events)
    print(Y)
    
    X = vectorizer.transform(epochs)
    print(X.shape)
    
    clf.fit(X,Y)

    



def main(ip_address,
         port,
         length_header,
         length_chunk,
         clf,
         vectorizer,
         event_id):
    
    logger = logging.getLogger(__name__)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((ip_address, port))
    print("server info. ip: %s, port: %s"%(str(ip_address), str(port)))

    server.listen()
    conn, addr = server.accept()
    conn.settimeout(0.1)
    logger.debug("New socket connection was established. '%s'"%str(addr))
    
    
    conn.settimeout(None)
    data = conn.recv(length_header)

    msg_length = int.from_bytes(data, 'little')


    print(msg_length)
    msg = recv_sock_split(conn, msg_length, length_chunk)
    print(len(msg))
    msg_json = json.loads(msg)
    
    print(msg_json.keys())

    if msg_json['type'] == 'cmd':
        if msg_json['cmd'] == 'train':
            train_classifier(clf, vectorizer, msg_json['epochs'], msg_json['events'], event_id)
            msg_json = dict()
            msg_json['type'] = 'info'
            msg_json['info'] = 'training_completed'

            data = json.dumps(msg_json).encode('utf-8')
            msg_length = len(data)
            print(msg_length)
            conn.send(msg_length.to_bytes(conf.length_header, byteorder='little'))
            conn.send(data)

if __name__ == "__main__":

    import conf
    log_dir = os.path.join(os.path.expanduser('~'), "log", "lsl-epoching")

    log_strftime = "%y-%m-%d"
    datestr =  datetime.datetime.now().strftime(log_strftime) 
    log_fname = "%s.log"%datestr
    
    print(log_dir)

    mkdir(log_dir)
    if os.path.exists(os.path.join(conf.log_dir, log_fname)):
        os.remove(os.path.join(conf.log_dir, log_fname))
    log.set_logger(os.path.join(log_dir, log_fname), True)
    
    logger = logging.getLogger(__name__)
    logger.debug("ip address: %s"%str(conf.ip_address))
    logger.debug("port: %s"%str(conf.port))
    
    main(conf.ip_address,
         conf.port,
         conf.length_header,
         conf.length_chunk,
         conf.clf,
         conf.vectorizer,
         conf.event_id)
