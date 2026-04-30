# encoding = utf-8

import pie
import json

def run_puppet_plan(alert, helper):
  # Load our URLs; we generate possible ones assuming the console hostname is valid
  # however if a user provides their own URL it goes here
  # this also allows for us to add an int_proxy feature in the future.
  endpoints = pie.util.getendpoints(alert['global']['puppet_enterprise_console'])
  rbac_url = endpoints['rbac']
  orch_url = endpoints['bolt']
  pe_console = endpoints['console_hostname']

  puppet_environment = alert['param']['puppet_environment']
  splunk_hec_url = alert['global']['splunk_hec_url']
  puppet_action_hec_token = alert['global']['puppet_action_hec_token']
  plan_name = alert['param']['plan_name']
  plan_parameters = alert['param']['plan_parameters']

  message = {
    'message': 'Running plan {} on {} '.format(plan_name,pe_console),
    'action_type': 'plan',
    'action_name': plan_name,
    'action_parameters': plan_parameters,
    'action_state': 'starting',
    'pe_console': pe_console,
  }

  helper.log_debug(message)
  pie.hec.post_action(message, pe_console, splunk_hec_url, puppet_action_hec_token)

  rbac_user = alert['global']['puppet_user']
  rbac_user_pass = alert['global']['puppet_user_pass']

  if alert['global']['timeout'] is not None and alert['global']['timeout'] != '':
    plan_timeout = alert['global']['timeout']
  else:
    plan_timeout = 600

  try:
    token_lifetime = int(plan_timeout) * 2
  except Exception as e:
    helper.log_error("Timeout must be an integer, '{}' was provided instead".format(plan_timeout))

 # Check if the user is configured with an RBAC token or Password:
  if alert['global']['pe_token']:
    auth_token = rbac_user_pass
  else:
    auth_token = pie.rbac.genauthtoken(rbac_user,rbac_user_pass,'TA-puppet-alert-orchestrator',rbac_url, timeout=token_lifetime)

  # Note: Parameters are expected as a text string, not JSON, so when building a sample alert the JSON must be represented as:
  # alert['param']['plan_parameters'] = "{ \"target\": \"puppet-agent.example.com\", \"service\": \"puppet\"}"

  try:
    jobid = pie.orch.reqplan(plan_name,auth_token,puppet_environment,orch_url,parameters=plan_parameters)
    helper.log_debug('Puppet plan successfully requested with ID of {}'.format(jobid))
  except Exception as e:
    helper.log_error('Unable to request Puppet plan before {}'.format(e))

  try:
    jobresults = pie.orch.getplanresult(jobid, auth_token, orch_url, timeout=plan_timeout)
  except Exception as e:
    helper.log_error('Plan failed before {}'.format(e))

  # While plans can be run against multiple targets the TargetSpec is typically a parameter named either 'target(s)' or 'nodes'.
  # Although it can be named something entirely different. As such, we are currently reporting on the overall status of the Plan
  # (i.e. If it succeeds on 2 nodes and fails on 1 it will be considered a 'failure').
  # This also means that rmessage['message'] will include the PE Console hostname as opposed to each target the Plan was ran against.
  rmessage = message
  rmessage['action_state'] = jobresults['state']
  rmessage['joburl'] = 'https://{}/#/orchestration/plans/plan/{}'.format(pe_console,jobid)
  rmessage['pe_console'] = pe_console
  rmessage['result'] = jobresults['result']
  rmessage['start_timestamp'] = jobresults['created_timestamp']
  rmessage['duration'] = jobresults['duration']
  rmessage['finish_timestamp'] = jobresults['finished_timestamp']

  if rmessage['action_state'] == 'success':
    rmessage['message'] = 'Successfully ran plan {} on {} '.format(plan_name,pe_console)
    helper.log_debug(rmessage['message'])
  elif jobresults['state'] == 'failure':
    rmessage['message'] = 'Failed to run plan {} on {} '.format(plan_name,pe_console)
    helper.log_error(rmessage['message'])
  else:
    rmessage['message'] = 'Something happened to plan {} on {} that we have no idea about'.format(plan_name,pe_console)
    helper.log_error(rmessage['message'])

  pie.hec.post_action(rmessage, pe_console, splunk_hec_url, puppet_action_hec_token)

# Below are example steps for testing this function.
#
# test_file.py
#
# from puppet_plan_action import run_puppet_plan
#
# helper = {}
# alert = {}
# alert['global'] = {}
# alert['param'] = {}
# alert['global']['puppet_enterprise_console'] = "puppet_enterprise_console"
# alert['global']['splunk_hec_url'] = "splunk_hec_url"
# alert['global']['puppet_user'] = "puppet_rbac_user"
# alert['global']['puppet_user_pass'] = "puppet_rbac_user_pass"
# alert['global']['pe_token'] = ''
# alert['global']['puppet_action_hec_token'] = "puppet_action_hec_token"
# alert['global']['timeout'] = ''
# 
# alert['param']['plan_name'] = "plan_name"
# alert['param']['plan_parameters'] = "plan_parameters"
# alert['param']['puppet_environment'] = "puppet_environment"
#
# run_puppet_plan(alert, helper)
#
# From command line run the below command:
#
# /opt/splunk/bin/splunk cmd python test_file.py
#
