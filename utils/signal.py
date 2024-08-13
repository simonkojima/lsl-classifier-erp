import logging
import numpy as np
import scipy
import mne

def apply_sosfilter(data, sos, zero_phase = True):
    # channel_wise should be set True, when it's called from mne_instance.apply_function().
    if zero_phase:
        r = scipy.signal.sosfiltfilt(sos, data)
    else:
        r = scipy.signal.sosfilt(sos, data)
    return r

def get_raw_from_streams(streams, name_eeg_stream, name_marker_stream):
    
    eeg = None
    marker = None

    for stream in streams:
        name = stream['info']['name'][0]

        if name == name_eeg_stream:
            eeg = stream
        elif name == name_marker_stream:
            marker = stream
    
    if eeg is None:
        raise ValueError("'%s' was not found"%(name_eeg_stream))

    if marker is None:
        raise ValueError("'%s' was not found"%(name_marker_stream))
    
    data = eeg['time_series'].T
    times = eeg['time_stamps']

    events = marker['time_series']
    mrk_times = marker['time_stamps']
    
    events = [int(val[0]) for val in events]
    
    times = np.array(times)
    mrk_times = np.array(mrk_times)
    
    events_mne = list()
    for idx, event in enumerate(events):
        diff = np.abs(times - mrk_times[idx])
        I = np.argmin(diff)
        
        events_mne.append([I, 0, event])
        
    events = np.array(events_mne)
    
    data = data[0:9, :]

    raw = mne.io.RawArray(data = data,
                          info = mne.create_info(ch_names = 9, sfreq = 1000, ch_types = 'eeg'))
    
    return raw, events