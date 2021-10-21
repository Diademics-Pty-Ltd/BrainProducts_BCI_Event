using System.Windows.Input;
using System.Globalization;
using System;

namespace TriggerBoxListener
{
    internal sealed class ViewModel : Notifier
    {
        // status messages
        private const string Idle = "Idle";
        private const string Connected = "Connected";
        private const string Connecting = "Connecting";
        
        // button texts
        private const string Connect = "Connect";
        private const string Disconnect = "Disconnect";

        // internal fields
        private ListenerM _listener;

        // private fields for GUI
        private string _comPortNumber = "3";
        private string _connectText = Connect;
        private bool _isConnected = false;
        private bool _connectEnabled = true;
        private string _consoleOutput = "";
        private string _statusState = Idle;
        private bool _runProgressBar;

        // public properties for GUI
        public string ComPortNumber
        {
            get => _comPortNumber;
            set => Update(ref _comPortNumber, value);
        }

        public string ConnectText
        {
            get => _connectText;
            set => Update(ref _connectText, value);
        }
        public bool ConnectEnabled
        {
            get => _connectEnabled;
            set => Update(ref _connectEnabled, value);
        }
        public string ConsoleOutput
        {
            get => _consoleOutput;
            set => Update(ref _consoleOutput, value);
        }
        public string StatusState
        {
            get => _statusState;
            set => Update(ref _statusState, value);
        }
        public bool RunProgressBar
        {
            get => _runProgressBar;
            set => Update(ref _runProgressBar, value);
        }

        // commands for GUI
        public ICommand ConnectToTriggerBox => new Command(_ => OnConnectToTriggerBox());

        // delegates
        public Action<string> UpdateConsoleAction => (x) => UpdateConsole(x);

        public ViewModel()
        { }

        private void OnConnectToTriggerBox()
        {
            if (_isConnected)
            {
                _listener.Dispose();
                StatusState = Idle;
                ConnectText = Connect;
                _isConnected = false;
            }
            else
            {
                try
                {
                    StatusState = Connecting;
                    RunProgressBar = true;
                    _listener = new(int.Parse(_comPortNumber, CultureInfo.InvariantCulture), UpdateConsoleAction);
                    StatusState = Connected;
                    RunProgressBar = false;
                    ConnectText = Disconnect;
                    _isConnected = true;
                }
                catch (Exception ex)
                {
                    UpdateConsole(ex.Message + "\n");
                    StatusState = Idle;
                    RunProgressBar = false;
                }

            }
        }
        private void UpdateConsole(string str) => ConsoleOutput += str;
    }
}
