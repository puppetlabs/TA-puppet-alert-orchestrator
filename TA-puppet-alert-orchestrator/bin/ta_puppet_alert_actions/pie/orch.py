import json
import requests
import sys
import time
import urllib3


def _get(uri, headers, ssl_verify=False):
    if not ssl_verify:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    try:
        r = requests.get(uri, headers=headers, verify=ssl_verify)
    except Exception:
        print('Unexpected error:', sys.exc_info()[0])
        raise
    return r


def _post(endpoint, req, headers, ssl_verify=False):
    if not ssl_verify:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    try:
        r = requests.post(endpoint, json=req, headers=headers, verify=ssl_verify)
    except Exception:
        print('Unexpected error:', sys.exc_info()[0])
        raise
    return r


def post(endpoint, req, headers, ssl_verify=False):
    r = _post(endpoint, req, headers, ssl_verify)
    if r.status_code != 202:
        raise ValueError('Unable to submit task command', r.status_code, r.text)
    return json.loads(r.text)['job']


def post_plan(endpoint, req, headers, ssl_verify=False):
    r = _post(endpoint, req, headers, ssl_verify)
    if r.status_code != 202:
        raise ValueError('Unable to submit plan run', r.status_code, r.text)
    return json.loads(r.text)['name']


def reqtask(node, task, token, environment, url, parameters=None, ssl_verify=False):
    headers = {'X-Authentication': token}
    params = json.loads(parameters) if parameters else {}

    req = {
        'environment': environment,
        'task': task,
        'params': params,
        'scope': {'nodes': [node]},
    }

    return post('{}/command/task'.format(url), req, headers, ssl_verify)


def reqdeploy(node, noop, token, environment, url, ssl_verify=False):
    headers = {'X-Authentication': token}

    req = {
        'environment': environment,
        'noop': noop,
        'scope': {'nodes': [node]},
    }

    return post('{}/command/deploy'.format(url), req, headers, ssl_verify)


def reqplan(plan, token, environment, url, parameters=None, ssl_verify=False):
    headers = {'X-Authentication': token}
    params = json.loads(parameters) if parameters else {}

    req = {
        'environment': environment,
        'plan_name': plan,
        'params': params,
    }

    return post_plan('{}/command/plan_run'.format(url), req, headers, ssl_verify)


def get_tasklist(url, token, ssl_verify=False):
    uri = '{}:8143/orchestrator/v1/tasks'.format(url)
    headers = {'X-Authentication': token}
    r = _get(uri, headers, ssl_verify)

    if r.status_code != 200:
        raise ValueError('Unable to retrieve list of available Tasks:', uri, r.status_code, r.text)

    return json.loads(r.text)['items']


def get_planlist(url, token, ssl_verify=False):
    uri = '{}:8143/orchestrator/v1/plans'.format(url)
    headers = {'X-Authentication': token}
    r = _get(uri, headers, ssl_verify)

    if r.status_code != 200:
        raise ValueError('Unable to retrieve list of available Plans:', uri, r.status_code, r.text)

    return json.loads(r.text)['items']


def get_actionparams(action_id, token, ssl_verify=False):
    headers = {'X-Authentication': token}
    r = _get(action_id, headers, ssl_verify)

    if r.status_code == 200:
        return json.loads(r.text)


def getjobstate(joburl, token, ssl_verify=False):
    headers = {'X-Authentication': token}
    r = _get(joburl, headers, ssl_verify)

    if r.status_code != 200:
        raise ValueError('Unable to get job status endpoints:', joburl, r.status_code, r.text)

    return json.loads(r.text)['state']


def getjobresult(job, token, url, wait=10, timeout=360, ssl_verify=False):
    joburl = '{}/jobs/{}'.format(url, job)
    task_timeout = int(timeout)
    runtime = 0
    completed = ['stopped', 'finished', 'failed']

    while runtime < task_timeout:
        if getjobstate(joburl, token, ssl_verify) in completed:
            return getjobreport(job, token, url, ssl_verify)
        time.sleep(wait)
        runtime += wait

    raise ValueError('Timeout exceeded waiting for: {} timeout: {} seconds'.format(joburl, timeout))


def getplanresult(job, token, url, wait=10, timeout=900, ssl_verify=False):
    joburl = '{}/plan_jobs/{}'.format(url, job)
    headers = {'X-Authentication': token}
    plan_timeout = int(timeout)
    runtime = 0
    completed = ['stopped', 'success', 'failure']

    while runtime < plan_timeout:
        if getjobstate(joburl, token, ssl_verify) in completed:
            r = _get(joburl, headers, ssl_verify)
            return json.loads(r.text)
        time.sleep(wait)
        runtime += wait

    raise ValueError('Timeout exceeded waiting for: {} timeout: {} seconds'.format(joburl, timeout))


def getjobreport(job, token, url, ssl_verify=False):
    headers = {'X-Authentication': token}
    reporturl = '{}/jobs/{}/nodes'.format(url, job)
    r = _get(reporturl, headers, ssl_verify)

    if r.status_code == 200:
        return json.loads(r.text)

    raise ValueError('Unable to get job status for job name:', job, r.status_code, r.text)
