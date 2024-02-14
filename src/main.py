import os
import logging
import socket
import datetime
import json
import traceback

import pyicom as icom
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
    
    Y = list()
    for event in  events:
        if event in event_id['target']:
            Y.append(1)
        elif event in event_id['nontarget']:
            Y.append(0)
        else:
            raise ValueError("Unknown event. '%s'"%(str(event)))
    
    X = vectorizer.transform(epochs)
    
    clf.fit(X,Y)

def classification_main(icom_server,
                        client_name,
                        length_header,
                        length_chunk,
                        clf,
                        vectorizer,
                        event_id):    
    flag = [True]
    distances = dict()
    for event in event_id:
        distances[event] = list()

    while flag[0]:
        try:
            while True:
                data = icom_server.recv(names = [client_name])[0]
                data = json.loads(data.decode('utf-8'))

                if data['type'] == "epochs":
                    epochs = data['epochs']
                    events = data['events']
                    for idx, epoch in enumerate(epochs):
                        epoch = np.atleast_3d(np.array(epoch))
                        epoch = np.transpose(epoch, (2,0,1))
                        X = vectorizer.transform(epoch)
                        val = clf.decision_function(X)
                        distances[events[idx]].append(val)
                elif data['type'] == 'cmd':
                    if data['cmd'] == 'trial-end':
                        logger.debug("trial end")
                        return distances
                else:
                    logger.error("data['type']: %s was received"%str(data['type']))
                    continue

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
         client_name,
         length_header,
         length_chunk,
         clf,
         vectorizer,
         event_id_train,
         event_id_online):
    
    logger = logging.getLogger(__name__)
    
    server = icom.server(ip = ip_address, port = port)
    server.start()
    print("server info. ip: %s, port: %s"%(str(ip_address), str(port)))
    logger.debug("server info. ip: %s, port: %s"%(str(ip_address), str(port)))
    while len(server.conns) == 0:
        pass
    
    flag = [True]
    while flag[0]:
        try:
            data = server.recv(names = [client_name])[0]
            logger.debug("recieved.")
            msg_json = json.loads(data.decode('utf-8'))
            logger.debug("json was parsed")

            if msg_json['type'] == 'cmd':
                if msg_json['cmd'] == 'train':
                    logger.debug("training started")
                    #
                    epochs = list()
                    events = list()
                    with open("sub-simon_epochs_training_task-asme_run-1.json", 'r') as f:
                        data = json.load(f)

                    for epoch in data['epochs']:
                        epochs += epoch
                        
                    for event in data['events']:
                        events += event

                    #
                    #train_classifier(clf, vectorizer, msg_json['epochs'], msg_json['events'], event_id_train)
                    train_classifier(clf, vectorizer, epochs, events, event_id_train)
                    logger.debug("training completed")

                    msg_json = dict()
                    msg_json['type'] = 'info'
                    msg_json['info'] = 'training_completed'

                    data = json.dumps(msg_json).encode('utf-8')
                    server.send(data, names=[client_name])
                    
                    logger.debug("training_completed")
                    
                elif msg_json['cmd'] == 'trial-start':
                    print("trial is started")
                    logger.debug("trial is started")
                    distances = classification_main(server,
                                                    client_name,
                                                    length_header,
                                                    length_chunk,
                                                    clf,
                                                    vectorizer,
                                                    event_id_online)
                    distance_mean = list()
                    for idx, event in enumerate(event_id_online):
                        distance_mean.append(np.mean(distances[event]))
                    I = np.argmax(distance_mean)
                    pred = event_id_online[I]
                    
                    msg = dict()
                    msg['type'] = 'info'
                    msg['info'] = 'classification_result'
                    msg['pred'] = pred
                    msg['output'] = distance_mean

                    data = json.dumps(msg).encode('utf-8')
                    server.send(data, names = [client_name])

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
         conf.client_name,
         conf.length_header,
         conf.length_chunk,
         conf.clf,
         conf.vectorizer,
         conf.event_id,
         conf.event_id_online)
