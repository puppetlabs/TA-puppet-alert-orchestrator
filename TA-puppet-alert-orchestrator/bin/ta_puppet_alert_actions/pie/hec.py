import json
import requests
import urllib3
from datetime import datetime


def post_report(detailed_report, hec_url, hec_token, ssl_verify=False):
    headers = {"Authorization": "Splunk {}".format(hec_token)}

    utc_time = datetime.strptime(detailed_report['start_time'], "%Y-%m-%dT%H:%M:%S.%fZ")
    epoch = (utc_time - datetime(1970, 1, 1)).total_seconds()

    report = {
        'host': detailed_report['certname'],
        'time': epoch,
        'sourcetype': 'puppet:detailed',
        'event': detailed_report,
    }

    if not ssl_verify:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    try:
        requests.post(hec_url, json=report, headers=headers, verify=ssl_verify)
    except Exception as e:
        raise Exception("HEC Error: {0}".format(e))


def post_action(message, host, hec_url, hec_token, ssl_verify=False):
    headers = {"Authorization": "Splunk {}".format(hec_token)}

    event = {
        'host': host,
        'sourcetype': 'puppet:action',
        'event': message,
    }

    if not ssl_verify:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    try:
        requests.post(hec_url, json=event, headers=headers, verify=ssl_verify)
    except Exception as e:
        raise Exception("HEC Error: {0}".format(e))
