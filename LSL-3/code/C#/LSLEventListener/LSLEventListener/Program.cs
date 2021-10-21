using System;
using LSL;
using System.Threading;

namespace LSLEventListener
{
    class LslMarkerListener : IDisposable
    {
        private readonly StreamInlet _inlet;
        private readonly Action<double, string> _onMarker;
        private readonly Thread _thread;
        private bool _isRunning = true;

        public LslMarkerListener(Action<double, string> onMarker)
        {
            _onMarker = onMarker;
            StreamInfo[] streamInfos = LSL.LSL.resolve_stream("type", "Markers");
            _inlet = new(streamInfos[0]);
            _thread = new(Listen);
            _thread.Start();
        }

        private void Listen()
        {
            string[] markerContainer = new string[1];
            while(_isRunning)
            {
                double timestamp = _inlet.pull_sample(markerContainer);
                _onMarker(timestamp, markerContainer[0]);
            }
        }

        public void Dispose()
        {
            _isRunning = false;
            if (_thread.IsAlive)
                _thread.Join();
        }
    }

    class Program
    {
        public static Action<double, string> PrintIt => (x, y) =>
            Console.WriteLine(string.Format("Received marker {0} at time {1}", y, x));

        static void Main()
        {
            LslMarkerListener lslMarkerListener = new(PrintIt);
            Console.WriteLine("Enter anything to exit...");
            while (!System.Console.KeyAvailable)
            {
                Thread.Sleep(100);
            }
        }
    }
}
