
# Production Integration with RAST

```
Machine:         elm.mcs.anl.gov
Root directory:  /disks/arast/
Repository:      assembly/
Server scripts:  assembly/server/
Server logs:     deployment/var/log/
Client scripts:  deployment/bin/
```

### Clone assembly repository
```bash
cd /disks/arast
git clone git@github.com:kbase/assembly.git
```

### Deploy client scripts
```bash
cd /disks/arast/assembly
source env/client-env-for-rast.sh
DEPLOY_RUNTIME=$KB_RUNTIME TARGET=/disks/arast/deployment make -f Makefile.standalone
export PATH=/disks/arast/deployment/bin:$PATH
```

### Start/stop assembly servers

```bash
cd /disks/arast/assembly
source env/server-env-for-rast.sh
server/start_service
server/stop_service
```

### Start/stop individual servers

```
start_control_service
start_compute_service
stop_control_service
stop_compute_service
```


# Testing Environment

```
User directory:  /disks/arast/${USER}
Repository:      assembly/
Server scripts:  assembly/server/
Server logs:     assembly/deployment/var/log/
Client scripts:  assembly/deployment/bin/
```

### Clone user's forked assembly repository
```bash
cd /disks/arast/${USER}
git clone git@github.com:${USER_GITHUB_ID}/assembly.git
```

### Deploy client scripts in user directory
```bash
source /vol/kbase/deployment/user-env.sh
cd /disks/arast/${USER}/assembly
DEPLOY_RUNTIME=$KB_RUNTIME make -f Makefile.standalone
export PATH=/disks/arast/${USER}/assembly/deployment/bin:$PATH
```

### Start service from test server codes
```bash
# source runtime for python libraries
source /vol/kbase/deployment/user-env.sh
# add gcc-4.7 to library path
export LD_LIBRARY_PATH=/disks/gcc/gcc-4.7.4/lib64:$LD_LIBRARY_PATH

# customize server options
export ARAST_URL=localhost
export ARAST_DATA_DIR=/disks/arast/fangfang/ar-test-data
export ARAST_BIN_DIR=/disks/arast/fangfang/assembly/third_party
export ARAST_WORKER_THREADS=2

# start service from any path
/disks/arast/fangfang/assembly/server/start_service
```
```
ARAST control server started: pid = 351
ARAST compute server started: pid = 379
```

Additional customizable variables include: `ARAST_QUEUE`, `ARAST_VAR_DIR`, `ARAST_WORKER_THREADS`.

Log files will be generated in `$ARAST_VAR_DIR/log`:
```
ar_server.log
ar_compute.log
```

Here are the actual commands that `start_service` uses:
```bash
/disks/arast/fangfang/assembly/lib/assembly/arastd.py --config /disks/arast/fangfang/assembly/lib/assembly/arast.conf --logfile /disks/arast/fangfang/assembly/deployment/var/log/ar_server.log > /disks/arast/fangfang/assembly/deployment/var/log/ar_server.out 2>&1 &

/disks/arast/fangfang/assembly/lib/assembly/ar_computed.py --config /disks/arast/fangfang/assembly/lib/assembly/ar_compute.conf --server localhost --compute-bin /disks/arast/fangfang/assembly/third_party --compute-data /disks/arast/fangfang/ar-test-data >> /disks/arast/fangfang/assembly/deployment/var/log/ar_compute.log 2>&1 &
```

