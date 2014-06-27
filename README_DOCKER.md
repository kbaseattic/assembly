# Deploying an Assembly Computer Server Docker Container

This will go through the steps of pulling and running a docker container.  Please note, the image is ~4GB, so ensure that /var/lib/docker has enough space.

### Install Docker
http://docs.docker.com/installation/

### As root, in GNU Screen (so we can stop the container from another shell)
```
screen
sudo su
```
### Pull Compute Image from Repository
```
$ docker pull 140.221.84.114:8000/assembly:compute
```

### Check if image pulled
```
$ docker images
REPOSITORY                     TAG                 IMAGE ID            CREATED             VIRTUAL SIZE
140.221.84.114:8000/assembly   compute             6974d25316ad        2 hours ago         3.943 GB
```

### Create temporary virtual /mnt/data in the image and run
```
$ docker run -v /mnt/data 6974d25316ad /bin/sh -c "cd /home/assembly/lib/assembly; ./ar_computed.py -s 10.0.28.15 -c ar_compute.conf"

 [.] Starting Assembly Service Compute Node
 [.] Retrieved Shock URL: 140.221.84.205:8000
 [.] AssemblyRAST host: 10.0.28.15
 [.] MongoDB port: 27017
 [.] RabbitMQ port: 5672
 [.] MongoDB connection successful.
 [.] Connecting to Shock server...
 [.] Shock connection successful
 [.] Storage path -- /mnt/data : OKAY
 [.] Binary path -- /home/assembly/third_party : OKAY
```

### Using a different location for compute data
```
$ docker run -v /path/to/local/dir:/mnt/data 6974d25316ad /bin/sh -c "cd /home/assembly/lib/assembly; ./ar_computed.py -s 10.0.28.15 -c ar_compute.conf"
```

### Managing running containers
```
$ sudo docker ps

CONTAINER ID
47585ba9d699
```

### Stop container
```
$ sudo docker stop 47585ba9d699
```
