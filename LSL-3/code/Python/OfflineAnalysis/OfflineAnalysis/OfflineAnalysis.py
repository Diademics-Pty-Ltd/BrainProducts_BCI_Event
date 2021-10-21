import pyxdf
from os.path import abspath, join, dirname
import sys
import matplotlib.pyplot as plt
import numpy as np
import statistics
import scipy.signal

# load the data
fname = abspath(join(dirname(__file__), '.', 'Tuesday_01.xdf'))
streams, fileheader = pyxdf.load_xdf(fname)

# extract the EEG stream
for stream in streams:
    if stream['info']['type'][0] == 'EEG':
        eeg_stream = stream
    if (stream['info']['name'][0]== 'TriggerBoxValues') & (len(stream['time_series']) is not 0):
        marker_stream = stream

# save some useful data into their own variables
nominal_srate = int(float(eeg_stream['info']['nominal_srate'][0]))
channel_count = int(eeg_stream['info']['channel_count'][0])

# get the channels of interest
bp_channels = ['Cz', 'C3', 'C4']
ref_channels = ['Tp9', 'Tp10']
bp_channel_indices = []
ref_channel_indices = []

for i, ch in enumerate(eeg_stream['info']['desc'][0]['channels'][0]['channel']):
    for label in bp_channels:
        if ch['label'][0] == label:
            bp_channel_indices.append(i)
    for label in ref_channels:
        if ch['label'][0] == label:
            ref_channel_indices.append(i)

# save and rereference the channels we are interested in
eeg = np.ndarray(shape=(len(eeg_stream['time_series'][:,0]), len(bp_channel_indices)))
for i in range(len(eeg_stream['time_series'][:,0])):
    val = 0.0;
    for ch in ref_channel_indices:
        val = val + eeg_stream['time_series'][i,ch]
    val = val / len(ref_channel_indices)
    count = 0
    for ch in bp_channel_indices:
        eeg[i,ch] = eeg_stream['time_series'][i,ch] - val

# phase preserving filter
[b,a] = scipy.signal.butter(2,[.1], btype='highpass', fs=nominal_srate) 
eeg_highpassed = scipy.signal.filtfilt(b,a, eeg, axis=0)
[b,a] = scipy.signal.butter(2,[5], btype='lowpass', fs=nominal_srate) 
eeg = scipy.signal.filtfilt(b,a, eeg_highpassed, axis=0)

# get the triggers from the marker stream 
trigger_points_from_markers = []
trigger_point = 0
for i, s in enumerate(marker_stream['time_series']):
    if s[0]=='1':
        while eeg_stream['time_stamps'][trigger_point]<marker_stream['time_stamps'][i]:
            trigger_point += 1
        trigger_points_from_markers.append(trigger_point)

# segment around the marker trigger points
segment_start_seconds = -5
segment_end_seconds = 2
segment_seconds = segment_end_seconds - segment_start_seconds 
segments = np.ndarray(shape=(int(segment_seconds * nominal_srate), len(bp_channels), len(trigger_points_from_markers)))
for i, pt in enumerate(trigger_points_from_markers):
    start_pt = pt + nominal_srate * segment_start_seconds
    end_pt = pt + nominal_srate * segment_end_seconds
    segments[:, :, i] = eeg[start_pt:end_pt,0:len(bp_channel_indices)]

time_scale = np.arange(segment_start_seconds, segment_end_seconds, 1.0/nominal_srate)

baseline_start_seconds = -4.5 
baseline_start_samples = int(nominal_srate * (baseline_start_seconds - segment_start_seconds))
baseline_end_seconds = -3.5
baseline_end_samples = int(nominal_srate * (baseline_end_seconds - segment_start_seconds))
for i in range(len(segments[0,0,:])):
    for j in range(len(segments[0,:,0])):
        baseline = np.mean(segments[baseline_start_samples:baseline_end_samples,j,i])
        for k,s in enumerate(segments[:,j,i]):
            segments[k,j,i] = s-baseline
        
average = np.zeros((len(segments[:,0,0]), len(segments[0,:,0])))

for i in range(len(segments[0,0,:])):
    for j in range(len(segments[0,:,0])):
        average[:,j] = average[:,j] + (segments[:,j,i])/len(segments[0,0,:])

plt.subplot(221)
plt.plot(time_scale, segments[:,0,:])
plt.subplot(222)
plt.plot(time_scale, segments[:,1,:])
plt.subplot(223)
plt.plot(time_scale, segments[:,2,:])
plt.subplot(224)
plt.plot(time_scale, average)
plt.show()



