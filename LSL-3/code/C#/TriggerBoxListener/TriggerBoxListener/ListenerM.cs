using LSL;
using System;
using System.IO.Ports;
using System.Globalization;

namespace TriggerBoxListener
{
    internal class ListenerM : IDisposable
    {
        private readonly SerialPort _triggerBox;
        private readonly StreamOutlet _outlet;
        private readonly string[] _outletBuffer = new string[1];
        private readonly Action<string> _updateText;
        private bool _firstTime = true;

        public ListenerM(int portNumber, Action<string> updateText)
        {
            _updateText = updateText;
            using StreamInfo info = new("TriggerBoxValues", "Markers", 1, 0, channel_format_t.cf_string, "asdfqwer!@#$");
            _outlet = new(info);
            try
            {
                _triggerBox = new(string.Format("COM{0}", portNumber, CultureInfo.InvariantCulture));
                _triggerBox.DataReceived += new(TriggerBoxDataReceived);
                _triggerBox.Open();
                _updateText(string.Format("Connected to TriggerBox on COM{0}\n", portNumber, CultureInfo.InvariantCulture));
            }
            catch (Exception ex)
            {
                throw new Exception(ex.Message);
            }
        }


        private void TriggerBoxDataReceived(object sender, SerialDataReceivedEventArgs e)
        {
            SerialPort sp = (SerialPort)sender;
            // get all available bytes from the input buffer 
            while (sp.BytesToRead > 0)
            {
                int value = 255 - sp.ReadByte();
                if (!_firstTime)
                {
                    _outletBuffer[0] = string.Format("{0}", value);
                    double timestamp = LSL.LSL.local_clock();
                    _outlet.push_sample(_outletBuffer, timestamp);
                    _updateText(string.Format("\nReceived Trigger: {0} at LSL time {1}", value, timestamp));
                }
                else
                    _firstTime = false;
            }
        }

        public void Dispose() => _triggerBox.DataReceived -= TriggerBoxDataReceived;
    }
}
