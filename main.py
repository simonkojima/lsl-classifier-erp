import os
import sys

import logging
import socket
import datetime
import traceback
import argparse
import msgpack

import pyicom as icom
import numpy as np

from utils.std import mkdir
from utils import log
from utils.stopping import test_distances, check_nstims

try:
    import tomllib
except:
    import toml as tomllib

def train_classifier(clf, vectorizer, epochs, events, event_id):

    logger = logging.getLogger(__name__)    
    epochs = np.array(epochs)
    
    Y = list()
    for event in  events:
        if event in event_id['target']:
            Y.append(1)
        elif event in event_id['nontarget']:
            Y.append(0)
        else:
            raise ValueError("Unknown event. '%s'"%(str(event)))
    
    logger.debug("type(epochs): %s"%str(type(epochs)))
    logger.debug("epochs.shape: %s"%str(epochs.shape))
    X = vectorizer.transform(epochs)
    logger.debug("X.shape: %s"%str(X.shape))
    
    clf.fit(X,Y)

def extract_epochs(files, name_marker_stream, name_eeg_stream):
    import pyxdf
    import scipy
    import mne
    from utils.signal import apply_sosfilter, get_raw_from_streams

    logger = logging.getLogger(__name__)    

    try:
        with open("config.toml", "r") as f:
            config = tomllib.load(f)   
    except:
        with open("config.toml", "rb") as f:
            config = tomllib.load(f)   

    epochs = list()
    for file in files:
        logger.debug("start loading '%s'"%(file))
        logging.getLogger().disabled = True
        streams, header = pyxdf.load_xdf(file)
        logging.getLogger().disabled = False
        logger.debug("finish loading xdf file")
        
        raw, events = get_raw_from_streams(streams, name_eeg_stream = name_eeg_stream, name_marker_stream = name_marker_stream)
        logger.debug("finish constructing raw file")
        logger.debug("number of channels of raw: %s"%str(len(raw.ch_names)))
        
        raw = raw.pick(picks = config['eeg']['channels'])
        logger.debug("EEG channel was picked: %s"%str(config['eeg']['channels']))
        logger.debug("raw.ch_names: "%(raw.ch_names))
        logger.debug("number of channels of channel-picked raw: %s"%str(len(raw.ch_names)))


        list_events = [str(val) for val in events[:, 2].tolist()]
        event_id = dict()
        for val in config['event_id']['offline']['nontarget']:
            if val in list_events:
                event_id['nontarget/%s'%val] = int(val)
        for val in config['event_id']['offline']['target']:
            if val in list_events:
                event_id['target/%s'%val] = int(val)
        print(event_id)

        sos = scipy.signal.butter(config['preprocess']['filter_order'],
                                  np.array(config['preprocess']['filter_range'])/(config['preprocess']['fs']/2), 'bandpass', output='sos')
        raw.apply_function(apply_sosfilter, picks = 'all', n_jobs = -1, channel_wise = True, sos=sos, zero_phase = False)
        
        baseline = config['preprocess']['baseline']
        if baseline is False:
            baseline = None
        _epochs = mne.Epochs(raw = raw,
                            events = events,
                            tmin = config['preprocess']['tmin'],
                            tmax = config['preprocess']['tmax'],
                            baseline = baseline,
                            event_id = event_id)
        
        epochs.append(_epochs)

    epochs = mne.concatenate_epochs(epochs)

    events = [str(val) for val in epochs.events[:, 2].tolist()]

    return epochs, events

def classification_main(icom_server,
                        clf,
                        vectorizer,
                        event_id,
                        dynamic_stopping,
                        p_th,
                        min_nstims,
                        alternative,
                        mode):    
    logger = logging.getLogger(__name__)
    flag = [True]
    distances = dict()
    for event in event_id:
        distances[event] = list()
        
    n_epochs = 0

    while flag[0]:
        try:
            while True:
                data = icom_server.recv()
                #data = json.loads(data.decode('utf-8'))
                data = msgpack.unpackb(data)

                if data['type'] == "epochs":
                    epochs = data['epochs']
                    events = data['events']
                    n_epochs += 1
                    logger.debug("events: %s"%str(events))
                    logger.debug("len(epochs): %s"%str(len(epochs)))
                    logger.debug("len(epochs[0]): %s"%str(len(epochs[0])))
                    logger.debug("event_id: %s"%str(event_id))
                    if events in event_id:
                        # number of epochs sent by client is always one.
                        epochs = np.atleast_3d(np.array(epochs))
                        epochs = np.transpose(epochs, (2,0,1))
                        logger.debug("epoch.shape: %s"%str(epochs.shape))
                        X = vectorizer.transform(epochs)
                        logger.debug("X.shape: %s"%str(X.shape))
                        val = clf.decision_function(X)
                        distances[events].append(val)
                        logger.debug("epoch for event '%s' was received and classified."%str(events))

                        if dynamic_stopping:
                            nstims = check_nstims(distances, event_id)
                            logger.debug("nstims: %s"%str(nstims))
                            if nstims >= min_nstims:
                                pred, p = test_distances(distances, event_id, method = 'mean', mode = mode, alternative = alternative)
                                logger.debug("pred, p: %s, %s"%(str(pred), str(p)))
                                if p < p_th:
                                    return distances, n_epochs, pred
                            
                elif data['type'] == 'cmd':
                    if data['cmd'] == 'trial-end':
                        logger.debug("trial end")
                        return (distances,) # return by tuple
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
         clf,
         vectorizer,
         event_id_train,
         event_id_online,
         name_marker_stream,
         name_eeg_stream):
    
    logger = logging.getLogger(__name__)
    
    server = icom.server(ip = ip_address, port = port, timeout=None)
    server.start()
    print("server info. ip: %s, port: %s"%(str(ip_address), str(port)))
    logger.debug("server info. ip: %s, port: %s"%(str(ip_address), str(port)))
    server.wait_for_connection()
    
    flag = [True]
    while flag[0]:
        try:
            data = server.recv()
            if len(data) == 0:
                continue
            logger.debug("received.")
            #msg_json = json.loads(data.decode('utf-8'))
            msg_json = msgpack.unpackb(data)
            logger.debug("msg: %s"%str(msg_json))

            if msg_json['type'] == 'cmd':
                if msg_json['cmd'] == 'train':
                    logger.debug("training started")
                    
                    logger.debug("files for training: %s"%str(msg_json['files']))
                    epochs, events = extract_epochs(msg_json['files'],
                                                    name_eeg_stream = name_eeg_stream,
                                                    name_marker_stream = name_marker_stream)
                    
                    train_classifier(clf, vectorizer, epochs, events, event_id_train)
                    logger.debug("training completed")

                    msg_json = dict()
                    msg_json['type'] = 'info'
                    msg_json['info'] = 'training_completed'

                    #data = json.dumps(msg_json).encode('utf-8')
                    data = msgpack.packb(msg_json)
                    server.send(data)
                    
                    logger.debug("training_completed")
                    
                elif msg_json['cmd'] == 'trial-start':
                    print("trial is started")
                    logger.debug("trial is started")
                    distances = classification_main(icom_server = server,
                                                    clf = clf,
                                                    vectorizer = vectorizer,
                                                    event_id = event_id_online,
                                                    dynamic_stopping = config['dynamic_stopping']['enable'],
                                                    p_th = config['dynamic_stopping']['p'],
                                                    min_nstims = config['dynamic_stopping']['min_nstims'],
                                                    alternative = config['dynamic_stopping']['alternative'],
                                                    mode = config['dynamic_stopping']['mode'])

                    msg = dict()
                    msg['type'] = 'info'
                    msg['info'] = 'classification_result'
                    logger.debug("distances: %s"%str(distances))
                    if len(distances) == 1:
                        distances = distances[0]
                        distance_mean = list()
                        for idx, event in enumerate(event_id_online):
                            val = np.mean(distances[event])
                            if np.isnan(val):
                                val = -float('inf')
                            distance_mean.append(np.mean(val))
                        I = np.argmax(distance_mean)
                        pred = event_id_online[I]
                        msg['pred'] = pred
                        msg['output'] = distance_mean
                    elif len(distances) == 3:
                        distances, n_epochs, pred = distances
                        msg['pred'] = pred
                        msg['output'] = distances
                        msg['n_epochs'] = n_epochs

                    #data = json.dumps(msg).encode('utf-8')
                    data = msgpack.packb(msg)
                    server.send(data)

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
    
    try:
        with open("config.toml", "r") as f:
            config = tomllib.load(f)   
    except:
        with open("config.toml", "rb") as f:
            config = tomllib.load(f)   

    parser = argparse.ArgumentParser()
    parser.add_argument('--ip', type = str, default = "localhost")
    parser.add_argument('--port', type = int, default = 49154)
    parser.add_argument('--marker', type=str, default=config['default_stream']['marker'])
    parser.add_argument('--signal', type=str, default=config['default_stream']['signal'])
    parser.add_argument("--log", type=str)
    args = parser.parse_args()

    home_dir = os.path.expanduser("~")
    
    log_strftime = "%y-%m-%d_%H-%M-%S"
    datestr =  datetime.datetime.now().strftime(log_strftime) 
    log_fname = "lsl-classifier-erp_%s.log"%datestr
    
    if args.log is not None:
        log_dir = args.log
    else:
        log_dir = os.path.join(os.path.expanduser("~"), config["directories"]["log"])

    mkdir(log_dir)
    log.set_logger(os.path.join(log_dir, log_fname), True)

    logger = logging.getLogger(__name__)
    
    logger.debug("log file will be saved in %s"%str(os.path.join(log_dir, log_fname)))
    
    for key in vars(args).keys():
        val = vars(args)[key]
        logger.debug("%s: %s"%(str(key), str(val)))
        
    from toeplitzlda.classification import ShrinkageLinearDiscriminantAnalysis, ToeplitzLDA
    clf = ShrinkageLinearDiscriminantAnalysis(n_channels=len(config['eeg']['channels']))

    home_dir = os.path.expanduser('~')
    pyerp_dir = os.path.join(home_dir, "git", "pyerp", "src")
    sys.path.append(pyerp_dir)

    import pyerp
    vectorizer = pyerp.EpochsVectorizer(ivals = config['features']['ivals'], type = 'ndarray', tmin = config['preprocess']['tmin'], tmax = config['preprocess']['tmax'], include_tmax = True, fs = config['eeg']['fs'])
    
    main(ip_address = args.ip,
         port = args.port,
         clf = clf,
         vectorizer = vectorizer,
         event_id_train = config['event_id']['offline'],
         event_id_online = config['event_id']['online'],
         name_marker_stream = args.marker, 
         name_eeg_stream = args.signal)
