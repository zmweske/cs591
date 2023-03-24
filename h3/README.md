# cs591 Homework 3

Multithreaded client & server with SSL/TLS: see the [project documentation](HomeWork3.pdf) for more information

<br/>

### This application now uses redis, which must be running before starting the server. With docker & docker compose installed, run `docker-compose up -d` in this directory to start redis in the pre-configured state. 

<br/>

## Usage: server.py

Run `python3 server.py --help` to get the same information

- `-p` and `--port` define the initial connection port. Default is `8888`
- The default subsequent port range is set with the variable PORT_RANGE and is by default set inclusively to `9001-9999`
- `-r` and `--redis_host` define the redis host. Default is `localhost`
- `-rp` and `--redis_port` define the redis host. Default is `6379`
- `-rpwd` and `--redis_pwd` define the redis host. Default is found in [`server.py`](server.py) and [`docker-compose.yaml`](docker-compose.yaml)


## Usage: client.py

Run `python3 client.py --help` to get the same information

- `-a` and `--address` define the IP address to connect to. Default is `localhost`
- `-p` and `--port` define the initial connection port. Default is `8888`
- `-u` and `--user` and `--username` define the username to log in with. The default is the UUID generated at runtime. 
- The `-c` option is used for testing to allow the user to attempt to connect to another client's connection. 

