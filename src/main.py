import os
import logging
import socket
import datetime
import json
import traceback
import argparse

import pyicom as icom
import numpy as np

from utils.std import mkdir
from utils import log

"""
def recv_sock_split(conn, msg_length, chunk_length):
    msg = list()
    for m in range(int(msg_length/chunk_length)):
        data = conn.recv(chunk_length).decode('utf-8')
        msg.append(data)
    msg.append(conn.recv(msg_length%chunk_length).decode('utf-8'))
    return "".join(msg)[0:(msg_length)]
"""


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

def extract_epochs(files):
    import pyxdf
    import scipy
    import conf
    import mne
    from utils.signal import apply_sosfilter, get_raw_from_streams

    logger = logging.getLogger(__name__)    

    epochs = list()
    for file in files:
        streams, header = pyxdf.load_xdf(file)
        logger.debug("finish loading xdf file")
        
        raw, events = get_raw_from_streams(streams, name_eeg_stream=conf.name_eeg_stream, name_marker_stream=conf.name_marker_stream)
        logger.debug("finish constructing raw file")


        list_events = [str(val) for val in events[:, 2].tolist()]
        event_id = dict()
        for val in conf.event_id['nontarget']:
            if val in list_events:
                event_id['nontarget/%s'%val] = int(val)
        for val in conf.event_id['target']:
            if val in list_events:
                event_id['target/%s'%val] = int(val)
        print(event_id)

        sos = scipy.signal.butter(conf.filter_order,
                                  np.array(conf.filter_range)/(conf.fs/2), 'bandpass', output='sos')
        raw.apply_function(apply_sosfilter, picks = 'all', n_jobs = -1, channel_wise = True, sos=sos, zero_phase = False)
        
        _epochs = mne.Epochs(raw = raw,
                            events = events,
                            tmin = conf.tmin,
                            tmax = conf.tmax,
                            baseline = conf.baseline,
                            event_id = event_id)
        
        epochs.append(_epochs)

    epochs = mne.concatenate_epochs(epochs)

    events = [str(val) for val in epochs.events[:, 2].tolist()]

    return epochs, events

def classification_main(icom_server,
                        client_name,
                        clf,
                        vectorizer,
                        event_id):    
    logger = logging.getLogger(__name__)
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
                    logger.debug("events: %s"%str(events))
                    logger.debug("len(epochs): %s"%str(len(epochs)))
                    logger.debug("len(epochs[0]): %s"%str(len(epochs[0])))
                    if events in event_id:
                        epochs = np.atleast_3d(np.array(epochs))
                        epochs = np.transpose(epochs, (2,0,1))
                        logger.debug("epoch.shape: %s"%str(epochs.shape))
                        X = vectorizer.transform(epochs)
                        val = clf.decision_function(X)
                        distances[events].append(val)
                        logger.debug("epoch for event '%s' was received and classified."%str(events))
                    """
                    for idx, event in enumerate(events):
                        if event in event_id:
                            epochs = np.atleast_3d(np.array(epochs))
                            epochs = np.transpose(epochs, (2,0,1))
                            logger.debug("epoch.shape: %s"%str(epochs.shape))
                            X = vectorizer.transform(epochs)
                            val = clf.decision_function(X)
                            distances[event].append(val)
                            logger.debug("epoch for event '%s' was received and classified."%str(event))
                    """
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
            if len(data) == 0:
                continue
            logger.debug("recieved.")
            print(data)
            msg_json = json.loads(data.decode('utf-8'))
            logger.debug("json was parsed")

            if msg_json['type'] == 'cmd':
                if msg_json['cmd'] == 'train':
                    logger.debug("training started")
                    
                    print(msg_json)
                    epochs, events = extract_epochs(msg_json['files'])
                    
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
    
    
    log_strftime = "%y-%m-%d_%H-%M-%S"
    datestr =  datetime.datetime.now().strftime(log_strftime) 
    log_fname = "%s.log"%datestr
    
    mkdir(conf.log_dir)
    #if os.path.exists(os.path.join(conf.log_dir, log_fname)):
    #    os.remove(os.path.join(conf.log_dir, log_fname))
    log.set_logger(os.path.join(conf.log_dir, log_fname), True)

    logger = logging.getLogger(__name__)
    
    logger.debug("log file will be saved in %s"%str(os.path.join(conf.log_dir, log_fname)))
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--ip', type = str, default=conf.default_ip_address)
    parser.add_argument('--port', type = int, default = conf.default_port)
    
    args = parser.parse_args()
    
    for key in vars(args).keys():
        val = vars(args)[key]
        logger.debug("%s: %s"%(str(key), str(val)))
    
    main(ip_address = args.ip,
         port = args.port,
         client_name = conf.client_name,
         clf = conf.clf,
         vectorizer = conf.vectorizer,
         event_id_train = conf.event_id,
         event_id_online = conf.event_id_online)
