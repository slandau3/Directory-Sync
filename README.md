Directory Sync
======
Directory sync is a program in which a daemon is created to watch over given directories. Every 2 minutes (default) the main program will run which will attempt to upload the given directories (and sub directories).

Usage:
```bash
python3 syncd.py
```

Upon activation, a log file named "syncd.log" will be created in /tmp/. The file will contain information about the daemon itself (including the pid which is used to kill it). Whenever the program performs a scan to upload files, information will be added to the log file. The information is in the form of X uploaded to Y. Where X is a directory path and Y is a server path, along with the time in which the upload took place.