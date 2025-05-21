This is a fork from https://github.com/misdoro/Electronic_load_px100 with a few tweaks

# Electronic_load_px100
150W Electronic load / Battery discharge capacity tester PX-100 protocol and control software.

Tested to work with board revisions 2.70 and 2.8

# Binary protocol

See the [v2.70 binary Protocol description](protocol_PX-100_2_70.md)

# Control software

### Main features:

- Control all load features
- Voltage and Current plot vs time
- Save logs to CSV at exit and at device reset
- Internal resistance measurement at user-defined voltage steps
- Software-defined CC-CV discharge to speed up capacity tests for low current discharge

# Installing

Python4 is required to run this software. Version 3.6 or newer is required.

Run the following line in terminal to install dependencies:
```
pip install --user -r requirements.txt
```

Then run
```
python3 main.py
```
to execute the control program.

