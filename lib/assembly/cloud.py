import socket
import shutil
import uuid
import logging
import os

import metadata
from novaclient.v1_1 import client
from ConfigParser import SafeConfigParser

class CloudMonitor(client.Client):
    def __init__(self, os_user, os_pass, os_tenant, os_auth_url, 
                 config_file):
        super(CloudMonitor, self).__init__(os_user, os_pass, os_tenant, 
                                           os_auth_url, service_type='compute', insecure=True)

        p = SafeConfigParser()
        p.read(config_file)
        self.default_flavor = p.get('cloud', 'flavor.default')
        self.default_keypair = p.get('cloud', 'keypair.default')
        self.default_image = p.get('cloud', 'image.kbase_compute')
        self.compute_init = p.get('cloud', 'compute_init')
        self.secgroup = p.get('cloud', 'sec_group')
        self.active_nodes = p.get('cloud', 'active.collection')
        self.all_nodes = p.get('cloud', 'history.collection')
        self.mongo = p.get('meta', 'mongo.host')
        self.metadata = metadata.MetadataConnection(config_file, self.mongo)

    def list_ids(self):
        servers = self.servers.list()
        print "#### Servers ####"
        for s in servers:
            print "%s : %s" % (s.name, s.id)

        flavors = self.flavors.list()
        print "\n\n#### Flavors ####"
        for f in flavors:
            print "%s : %s" % (f.name, f.id)

        keypairs = self.keypairs.list()
        print "\n\n#### KeyPairs ####"
        for k in keypairs:
            print "%s : %s" % (k.name, k.id)

        images = self.images.list()
        print "\n\n#### Images ####"
        for i in images:
            print "%s : %s" % (i.name, i.id)

    def launch_node(self, image_id=None, flavor_id=None, keypair=None):
        if image_id is None:
            image_id = self.default_image
        if flavor_id is None:
            flavor_id = self.default_flavor
        if keypair is None:
            keypair = self.default_keypair

        # Pass data to node
            #control_ip = socket.gethostbyname(socket.gethostname())
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('google.com', 0))
        control_ip = s.getsockname()[0]
        logging.info("My IP: %s" % control_ip)
        tmp_script = "tmp.txt"
        shutil.copyfile(self.compute_init, tmp_script)
        startup_script = open(tmp_script, 'a')
        startup_script.write("\npython ar_computed.py -c ar_compute.conf -s %s\n" %
                             control_ip)
        startup_script.write("\nend script")
        startup_script.close()
        startup_script = open(tmp_script, 'r')

        node = self.servers.create('assembly_' + str(uuid.uuid4()), image_id, 
                                   flavor_id, key_name=keypair, userdata=startup_script)
        #node.add_security_group(self.secgroup)
        

        logging.info("Launching compute node: %s" % node.id)
        data = {}
        data['server_id'] = node.id
        data['server_name'] = node.name

        self.metadata.insert_doc(self.active_nodes, data)

        return node

    def add_node_to_pool():
        pass

    def list_nodes(self):
        nodes =  self.metadata.list(self.active_nodes)
        return nodes

    def terminate_all_nodes(self):
        for node in self.list_nodes():
            sid = node['server_id']
            try:
                id = self.servers.get(node['server_id'])
                logging.info("Terminating server %s" % id)
                self.servers.delete(id)
                self.metadata.remove_doc(self.active_nodes, 'server_id', sid)
            except:
                print ("Unable to find node %s. Removing from db." % sid)
                self.metadata.remove_doc(self.active_nodes, 'server_id', sid)
        

    

    
