"""
Settings and constants
"""

RABBITMQ_HOST = '140.221.84.108'
DEFAULT_UPLOAD='null_upload_url'
DEFAULT_ROUTING_KEY = "medium.simple"
JOB_MEDIUM = "medium.simple"

## MongoDB ##
MONGO_HOST = 'localhost'
MONGO_PORT = 27017
DB_NAME = 'arast'
COLLECTION = 'jobs'


## Shock ##
ARASTURL = '140.221.84.110:8000'
ARASTUSER = 'cbun'
ARASTPASSWORD = '1234'

## Available Assemblers ##
assemblers = [
{
        'name' : 'Kiki',
        'aliases' : ['kiki', 'ki'],
        'command' : 'kiki'
},
{
        'name' : 'Velvet',
        'aliases' : ['velvet',],
        'command' : 'velvet'
},
{
        'name' : 'SOAPdenovo',
        'aliases' : ['soap'],
        'command' : 'soapdenovo'
}
]



"""
Example routing keys:
  medium.parallel
  small.simple
  large.parallel
"""
