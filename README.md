# python-hddtemp
hddtemp partially reimplemented in python.

```
usage: hddtemp.py [-h] [-D] [-d] [-p PORT] [-l LISTEN] [-s SEPARATOR]

options:
  -h, --help            show this help message and exit
  -D, --debug           Display various UDisks2 fields and their values.
  -d, --daemon          Execute hddtemp in TCP/IP daemon mode (port 7634 by
                        default). Always runs in foreground
  -p PORT, --port PORT  Port number to listen to (in TCP/IP daemon mode).
  -l LISTEN, --listen LISTEN
                        Listen on a specific address. Argument is a string
                        containing a host name or a numeric host address
                        string. The numeric host address string is a dotted-
                        decimal IPv4 address or an IPv6 hex address.
  -s SEPARATOR, --separator SEPARATOR
                        Separator to use between fields (in TCP/IP daemon
                        mode). The default separator is '|'.

```

Can use any of udisk2 daemon and drivetemp kernel module to get the drives' temperatures. Will report whether disks are spun down if run as
root.
