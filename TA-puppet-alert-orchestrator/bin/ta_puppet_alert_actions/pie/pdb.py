import json
import requests
import sys
import urllib3


def getpuppetreport(uuid, url, token, ssl_verify=False):
    query_string = {'query': 'reports[] {{ transaction_uuid = "{}" }}'.format(uuid)}

    if not ssl_verify:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    try:
        r = requests.post(url, json=query_string, headers={'X-Authentication': token}, verify=ssl_verify)
    except Exception:
        print('Unexpected error:', sys.exc_info()[0])
        raise

    if r.status_code != 200:
        raise ValueError('Unable to get report for transaction uuid:', uuid, r.status_code, r.text)

    return json.loads(r.text)


def query(pql, url, token, ssl_verify=False):
    if not ssl_verify:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    try:
        r = requests.post(url, json=pql, headers={'X-Authentication': token}, verify=ssl_verify)
    except Exception:
        print('Unexpected error:', sys.exc_info()[0])
        raise

    if r.status_code != 200:
        raise ValueError('Unable run query:', pql, r.status_code, r.text)

    return json.loads(r.text)
