import json
import requests
import sys
import urllib3


def genauthtoken(username, password, label, url, timeout=360, ssl_verify=False):
    lifetime = "{}s".format(timeout)

    req = {
        'login': username,
        'password': password,
        'lifetime': lifetime,
        'label': label,
    }

    if not ssl_verify:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    try:
        r = requests.post('{}/auth/token'.format(url), json=req, verify=ssl_verify)
    except Exception:
        print('Unexpected error:', sys.exc_info()[0])
        raise

    if r.status_code != 200:
        raise ValueError('Unable to get PE auth token', r.status_code, r.text)

    return json.loads(r.text)['token']
