using System;
using LSL;
using System.Threading;

namespace LSLOnlineSyncDemo
{
    public class SyncDemo : IDisposable
    {
        private readonly StreamInlet _streamInlet;
        private readonly Thread _readThread;
        private readonly int _channelCount;
        public bool _isReading = false;

        public SyncDemo(bool sync)
        {
            processing_options_t options = processing_options_t.proc_none;
            if (sync)
            {
                options = processing_options_t.proc_clocksync | processing_options_t.proc_dejitter | processing_options_t.proc_monotonize;
            }
            StreamInfo[] results = LSL.LSL.resolve_stream("type", "EEG");
            _streamInlet = new(results[0], postproc_flags: options);
            _channelCount = results[0].channel_count();
            _readThread = new(ReadSamples);
                                                                                                                 
        }

        public void LaunchReader()
        {
            if(_readThread.IsAlive)
            {
                _isReading = false;
                _readThread.Join();
            }
            _isReading = true;
            _readThread.Start();
        }

        private void ReadSamples()
        {
            double lastTimeStamp, currentTimeStamp, timeStampDiff, timeNow, firstTime;
            lastTimeStamp = LSL.LSL.local_clock();
            timeNow = LSL.LSL.local_clock();
            firstTime = LSL.LSL.local_clock();
            float[] sample = new float[_channelCount];
            Console.WriteLine("ReadSamples launched.");
            while(_isReading)
            {
                currentTimeStamp = _streamInlet.pull_sample(sample);
                timeStampDiff = currentTimeStamp - lastTimeStamp;
                lastTimeStamp = currentTimeStamp;
                double localNow = LSL.LSL.local_clock();
                if (localNow > timeNow+1)
                {
                    Console.WriteLine(string.Format("Time Elapsed = {0}\tSuccessive timestamp diff = {1}", localNow - firstTime, timeStampDiff));
                    timeNow = localNow;
                }
            }
        }

        public void Dispose()
        {
            if (_readThread.IsAlive)
            {
                _isReading = false;
                _readThread.Join();
            }
        }

        static void Main()
        {
            Console.WriteLine("Initializing");
            SyncDemo syncDemo = new(true);
            syncDemo.LaunchReader();
        }
    }
}
