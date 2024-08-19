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
    print(eeg['info']['desc'][0]['channels'][0]['channel'])
    channels = eeg['info']['desc'][0]['channels'][0]['channel']
    ch_names = [ch['label'][0] for ch in channels]
    sfreq = float(eeg['info']['nominal_srate'][0])

    raw = mne.io.RawArray(data = data,
                          info = mne.create_info(ch_names = ch_names, sfreq = sfreq, ch_types = 'eeg'))
    
    return raw, events

if __name__ == "__main__":
    import pyxdf
    import os
    import xml.etree.ElementTree as ET

    streams, header = pyxdf.load_xdf(os.path.join(os.path.expanduser('~'), "Documents", "eeg", "asme-speller", "sub-P99", "ses-S001", "eeg", "sub-P99_ses-S001_task-asmeoffline_run-001_eeg.xdf"))
    get_raw_from_streams(streams, "jarvis-erp", 'scab-c')