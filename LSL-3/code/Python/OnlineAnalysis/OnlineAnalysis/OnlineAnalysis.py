from pylsl import StreamInlet, resolve_stream
import matplotlib.pyplot as plt
import threading
import time
import numpy as np
import scipy.signal
import matplotlib.pyplot as plt

class OnlineAnalysisBP:
    """
    Class encapsulating LSL listeners analysis and plotting functions for Bereitschaftspotential paradigm
    """
    def __init__ (self, eeg_stream_type='EEG', marker_stream_type="Markers", event_trigger_value="1"):
        # find the streamns of interest
        streams = resolve_stream('type', eeg_stream_type)
        self.eeg_inlet = StreamInlet(streams[0])
        self.eeg_info = self.eeg_inlet.info()
        streams =resolve_stream('type', marker_stream_type)
        self.marker_inlet = StreamInlet(streams[0])
        self.event_trigger_value = event_trigger_value

        # set up pre-allocated ring buffers for online data processing
        self.eeg_ring_buffer = np.ndarray((int(self.eeg_info.nominal_srate()*15), self.eeg_info.channel_count()))
        self.eeg_timestamp_ring_buffer = np.ndarray((int(self.eeg_info.nominal_srate()*15), 1))
        self.eeg_ring_buffer_wrt_ptr = 0

        # segmentation parameters
        self.post_segment_period = 2
        self.pre_segment_period = 5
        self.segment_period = self.post_segment_period + self.pre_segment_period
        segment_samples = int(self.segment_period * self.eeg_info.nominal_srate())

        # channels of interest
        motor_cortex_channels = ['Cz', 'C3', 'C4']
        ref_channels = ['Tp9', 'Tp10']
        self.motor_cortex_channel_indices = []
        self.ref_channel_indices = []
        ch = self.eeg_info.desc().child("channels").child("channel")
        for k in range(self.eeg_info.channel_count()):
            for i, mc_ch in enumerate(motor_cortex_channels):
                if mc_ch == ch.child_value("label"):
                    self.motor_cortex_channel_indices.append(i)
            for i, mc_ch in enumerate(ref_channels):
                if mc_ch == ch.child_value("label"):
                    self.ref_channel_indices.append(i)
            ch = ch.next_sibling()

        # buffers for segmentation and pre-processing
        self.eeg_segment_buffer = np.ndarray((segment_samples, len(self.motor_cortex_channel_indices)))
        self.sample = np.ndarray(len(self.motor_cortex_channel_indices))
        self.average_storage = []

        # filtering
        filter_order = 6
        [self.b, self.a] = scipy.signal.butter(filter_order,[.1, 5], btype='bandpass', fs=self.eeg_info.nominal_srate()) 

        # thread management objects
        self.listening_to_eeg = True
        self.listening_to_markers = True
        self.eeg_listen_thread = threading.Thread(target=self.eegListener)
        self.eeg_listen_thread.start()
        self.marker_listen_thread = threading.Thread(target=self.markerListener)
        self.marker_listen_thread.start()
        self.eeg_data_lock = threading.Lock()
    
    # this method listens for new eeg data over LSL
    def eegListener(self):
        while self.listening_to_eeg:
            chunk, timestamps = self.eeg_inlet.pull_chunk()
            if timestamps: # pull_chunk returns empty buffers if no new data is available, on proceed otherwise
                
                # avoid race conditions
                self.eeg_data_lock.acquire()

                # copy the new data into the ring buffers
                for i, t in enumerate(timestamps):
                    for ch, val in enumerate(chunk[i]):
                        self.eeg_ring_buffer[self.eeg_ring_buffer_wrt_ptr,ch] = val
                    self.eeg_timestamp_ring_buffer[self.eeg_ring_buffer_wrt_ptr] = t
                    self.eeg_ring_buffer_wrt_ptr+=1
                    l = len(self.eeg_timestamp_ring_buffer[:,0])
                    if self.eeg_ring_buffer_wrt_ptr >= l:
                        self.eeg_ring_buffer_wrt_ptr-=l

                # now it is safe to release the lock
                self.eeg_data_lock.release()
            else:
                time.sleep(.005)

    # listen for markers and if we get the one we want, launch the thread that copies the new data
    def markerListener(self):
        while self.listening_to_markers:
            # pull_sample blocks until a new sample is available, so no need to check the result
            marker, timestamp = self.marker_inlet.pull_sample()
            # if the method returns, check to see if it is the marker we are interested in
            if marker[0] == self.event_trigger_value:
                print(f"received {marker} at time {timestamp}")
                # if so, do the segmentation/pre-processing
                t = threading.Thread(target=self.processData(timestamp))
                t.start()

    # segment, baseline correct, and filter the data
    def processData(self, timestamp):

        # wait for +2 seconds of data to have arrived
        while timestamp + self.post_segment_period < self.eeg_timestamp_ring_buffer[self.eeg_ring_buffer_wrt_ptr]:
            time.sleep(.01)

        # avoid race conditions with thread locking
        self.eeg_data_lock.acquire()

        # 'now' we are at the end of the segment
        ring_buffer_rd_ptr = self.eeg_ring_buffer_wrt_ptr

        # backup to the start of the segment
        while timestamp - self.pre_segment_period > self.eeg_timestamp_ring_buffer[ring_buffer_rd_ptr]:
            ring_buffer_rd_ptr-=1
            if ring_buffer_rd_ptr<0:
                ring_buffer_rd_ptr += len(self.eeg_timestamp_ring_buffer)

        # copy the new segment data from the ring buffer to the segment buffer sample by sample 
        for i, s in enumerate(self.eeg_segment_buffer):
            ref_val = 0
            for ch in self.ref_channel_indices:
              ref_val += self.eeg_ring_buffer[ring_buffer_rd_ptr, ch] 
            ref_val /= len(self.ref_channel_indices)
            for ch in self.motor_cortex_channel_indices:
                self.sample[ch] = self.eeg_ring_buffer[ring_buffer_rd_ptr, ch]  - ref_val
            self.eeg_segment_buffer[i,:] = self.sample
            ring_buffer_rd_ptr += 1
            l = len(self.eeg_timestamp_ring_buffer[:,0])
            if ring_buffer_rd_ptr>=l:
                ring_buffer_rd_ptr -= l
        
        # at this point we can release the lock
        self.eeg_data_lock.release()

        self.eeg_segmenmt_buffer = scipy.signal.filtfilt(self.b, self.a, self.eeg_segment_buffer, axis=0)
        self.averageAndPlot()

    def averageAndPlot(self):

        # store in our list
        self.average_storage.append(self.eeg_segment_buffer)

        # average
        average = np.zeros(self.eeg_segment_buffer.shape)
        for segment in self.average_storage:
            for s in range(len(segment[:,0])):
                for ch in range(len(segment[0,:])):
                    average[s,ch] += segment[s,ch]/len(average)
        plt.plot(average[:,0])
        plt.show()

    def __del__(self):
        self.listening_to_eeg = False
        self.listening_to_markers = False
        if self.eeg_listen_thread.isAlive():
            self.eeg_listen_thread.join(1)
        if self.marker_listen_thread.isAlive:
            self.marker_listen_thread.join(1)

analysis = OnlineAnalysisBP()