
import httplib2
import json
import base64

NEXUS_URL="https://nexus.api.globusonline.org/goauth/token?grant_type=client_credentials"

def get_token(username, password, auth_svc=NEXUS_URL):
    h = httplib2.Http()
    
    auth = base64.encodestring( username + ':' + password )
    headers = { 'Authorization' : 'Basic ' + auth }
    
    h.add_credentials(username, password)
    h.follow_all_redirects = True
    url = auth_svc
    
    resp, content = h.request(url, 'GET', headers=headers)
    status = int(resp['status'])
    if status>=200 and status<=299:
        tok = json.loads(content)
    else: 
        raise Exception(str(resp))
        
    return tok