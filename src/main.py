import os
import logging
import socket
import datetime
import json
import traceback
import threading

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

def classification_main(conn, length_header, length_chunk, clf, vectorizer, event_id):    
    flag = [True]
    distances = dict()
    for event in event_id:
        distances[event] = list()
    print(distances)
    while flag[0]:
        try:
            while True:


                data = conn.recv(length_header)
                msg_length = int.from_bytes(data, 'little')
                msg = conn.recv(msg_length).decode('utf-8')
                data = json.loads(msg)

                if data['type'] == "epochs":
                    data = conn.recv(length_header)
                    msg_length = int.from_bytes(data, 'little')
                    print(msg_length)
                    msg = recv_sock_split(conn, msg_length, length_chunk)
                    data = json.loads(msg)
                    print(data.keys())
                    epochs = data['epochs']
                    events = data['events']
                    
                    print(events)
                    print(len(epochs))
                    for idx, epoch in enumerate(epochs):
                        print(events[idx])
                        epoch = np.atleast_3d(np.array(epoch))
                        epoch = np.transpose(epoch, (2,0,1))
                        print(epoch.shape)
                        X = vectorizer.transform(epoch)
                        val = clf.decision_function(X)
                        distances[events[idx]].append(val)
                elif data['type'] == 'cmd':
                    if data['cmd'] == 'trial-end':
                        logger.debug("trial end")
                        #flag[0] = False
                        return distances
                else:
                    logger.error("data['type']: %s was received"%str(data['type']))
                    continue
            flag[0] = False
            continue
            
            msg = recv_sock_split(conn, msg_length, length_chunk)
            print(len(msg))
            msg_json = json.loads(msg)
            print(msg_json.keys())
            
            flag[0] = False

            
            msg_json = conn.recv(msg_length).decode('utf-8')

            print(msg_json)
            msg_json = json.loads(msg_json)
            print(msg_length)

        except socket.timeout as e:
            print(e)
            logger.debug(traceback.format_exc())
            pass
        except socket.error as e:
            print(e)
            logger.debug(traceback.format_exc())
            flag[0] = False
        except KeyboardInterrupt as e:
            print(e)
            logger.debug(traceback.format_exc())
            exit()
        except Exception as e:
            print(e)
            logger.debug(traceback.format_exc())
            flag[0] = False

def main(ip_address,
         port,
         length_header,
         length_chunk,
         clf,
         vectorizer,
         event_id_train,
         event_id_online):
    
    logger = logging.getLogger(__name__)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((ip_address, port))
    print("server info. ip: %s, port: %s"%(str(ip_address), str(port)))

    server.listen()
    #server.settimeout(0)
    conn, addr = server.accept()
    conn.setblocking(True)
    logger.debug("New socket connection was established. '%s'"%str(addr))
    
    flag = [True]
    #conn.settimeout(0)
    while flag[0]:
        try:
            data = conn.recv(length_header)
            msg_length = int.from_bytes(data, 'little')
            msg_json = conn.recv(msg_length).decode('utf-8')
            print(msg_json)
            msg_json = json.loads(msg_json)
            print(msg_length)

            if msg_json['type'] == 'cmd':
                if msg_json['cmd'] == 'train':
                    data = conn.recv(length_header)
                    msg_length = int.from_bytes(data, 'little')
                    msg = recv_sock_split(conn, msg_length, length_chunk)
                    print(len(msg))
                    msg_json = json.loads(msg)
                    print(msg_json.keys())
                    train_classifier(clf, vectorizer, msg_json['epochs'], msg_json['events'], event_id_train)
                    msg_json = dict()
                    msg_json['type'] = 'info'
                    msg_json['info'] = 'training_completed'

                    data = json.dumps(msg_json).encode('utf-8')
                    msg_length = len(data)
                    print(msg_length)
                    conn.send(msg_length.to_bytes(conf.length_header, byteorder='little'))
                    conn.send(data)
                elif msg_json['cmd'] == 'trial-start':
                    print("trial is started")
                    distances = classification_main(conn,
                                                    length_header,
                                                    length_chunk,
                                                    clf,
                                                    vectorizer,
                                                    event_id_online)
                    distance_mean = list()
                    for idx, event in enumerate(event_id_online):
                        distance_mean.append(np.mean(distances[event]))
                    print(distance_mean)
                    I = np.argmax(distance_mean)
                    pred = event_id_online[I]
                    
                    print(pred)
                    
                    msg = dict()
                    msg['type'] = 'info'
                    msg['info'] = 'classification_result'
                    msg['pred'] = pred
                    msg['output'] = distance_mean

                    data = json.dumps(msg).encode('utf-8')
                    msg_length = len(data)
                    conn.send(msg_length.to_bytes(conf.length_header, byteorder='little'))
                    conn.send(data)

        except socket.timeout as e:
            print(e)
            pass
        except KeyboardInterrupt as e:
            exit()
        except socket.error as e:
            print(e)
            logger.debug(traceback.format_exc())
        except Exception as e:
            logger.debug(traceback.format_exc())
            flag[0] = False

if __name__ == "__main__":

    import conf
    log_dir = os.path.join(os.path.expanduser('~'), "log", "lsl-classifier")

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
         conf.event_id,
         conf.event_id_online)
