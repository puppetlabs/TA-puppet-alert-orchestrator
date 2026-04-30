# $SPUNK_HOME/etc/apps/TA-puppet-alert-orchestrator/bin/inputs/orchestrator_actions.py
#
import sys
import os
import time
from requests.exceptions import ConnectionError as RequestsConnectionError
#
#
# If Splunk was installed in a custom location, change SPLUNK_APPS to the path where apps are installed.
APP_NAME = 'TA-puppet-alert-orchestrator'
if os.name == 'nt':
  SPLUNK_APPS = 'C:\Program Files\Splunk\etc\/apps\/'
else:
  SPLUNK_APPS = '/opt/splunk/etc/apps'
PIE_LIB = os.path.join(SPLUNK_APPS, APP_NAME, 'bin', 'ta_puppet_alert_actions')
#
#
# Here we modify the system path for Python to find the required helper libs.
try:
  LIB_DIR = os.path.join(SPLUNK_APPS, APP_NAME, 'lib')
  PATHS = [PIE_LIB, LIB_DIR]
  for path in PATHS:
    sys.path.append(path)
  import pie
  from splunktaucclib.splunk_aoblib.setup_util import Setup_Util
except Exception as e:
  sys.stderr.write("TA-puppet-alert-orchestrator: Failed to import required libs - {}".format(e))
#
#
# Define Splunk URI and session key.
uri = "https://localhost:8089"
session_key = sys.stdin.readline().strip()
#
#
# Configure the AOB Helper (Setup_Util) to access the settings configured in the add-on.
# This also takes a custom logger as a third attribute. Currently we are utilizing the default behaviour of input scripts logging stderr to splunkd.log.
# Retry up to 5 times with a 30s delay to handle the case where the script runs before
# Splunk's REST API is ready (e.g. at startup).
MAX_RETRIES = 5
RETRY_DELAY = 30
for attempt in range(1, MAX_RETRIES + 1):
  try:
    helper = Setup_Util(uri,session_key)
    inputs = {}
    inputs['hec_token'] = helper.get_customized_setting("splunk_hec_token").strip()
    inputs['hec_url'] = helper.get_customized_setting("splunk_hec_url").strip()
    inputs['pe_console'] = helper.get_customized_setting("puppet_enterprise_console").strip()
    inputs['timeout'] = helper.get_customized_setting("timeout")
    break
  except RequestsConnectionError as e:
    if attempt < MAX_RETRIES:
      sys.stderr.write("TA-puppet-alert-orchestrator: Splunk REST API not available, retrying in {}s (attempt {}/{}) - {}\n".format(RETRY_DELAY, attempt, MAX_RETRIES, e))
      time.sleep(RETRY_DELAY)
    else:
      sys.stderr.write("TA-puppet-alert-orchestrator: Splunk REST API unavailable after {} attempts, exiting - {}\n".format(MAX_RETRIES, e))
      sys.exit(0)
#
#
# Check if there is a configured timeout.
if inputs['timeout'] is not None and inputs['timeout'] != '':
  timeout = inputs['timeout']
else:
  timeout = 360
#
#
try:
  #
  # Retrieve any user accounts configured within the add-on.
  config_file = os.path.join(SPLUNK_APPS, APP_NAME, 'local/ta_puppet_alert_actions_account.conf')
  account_list = pie.util.list_accounts(config_file)
  for user in account_list:
    inputs['account'] = helper.get_credential_by_username(user)
    #
    # Check if the user is configured with an RBAC token or Password:
    _token = bool(int(inputs['account']['pe_token']))
    if _token:
      token = inputs['account']['password']
    else:
      user = inputs['account']['username']
      upass = inputs['account']['password']
      endpoints = pie.util.getendpoints(inputs['pe_console'])
      rbac_url = endpoints['rbac']
      token = pie.rbac.genauthtoken(user,upass,'TA-puppet-alert-orchestrator',rbac_url,timeout)
    try:
      #
      # Build event message for available Tasks by user.
      tasklist = pie.orch.get_tasklist(inputs['pe_console'],token)
      for task in tasklist:
        t_id = task['id']
        task_parameter = pie.orch.get_actionparams(t_id,token)
        tmessage = {
          'permitted': task['permitted'],
          'task_meta': None,
          'task_name': task['name'],
          'task_params': [],
          'user': user,
        }
        #
        # Add any task parameters to the event message.
        try:
          tmessage['task_meta'] = task_parameter['metadata'].get('parameters', {})
          for param in tmessage['task_meta']:
            tmessage['task_params'].append(param)
          #
          # Post Tasks via HEC endpoint
          try:
            host = inputs['pe_console'].replace("https://", "")
            hec_url = inputs['hec_url']
            hec_token = inputs['hec_token']
            post_tasks = pie.hec.post_action(tmessage,host,hec_url,hec_token)
          except Exception as e:
            sys.stderr.write("TA-puppet-alert-orchestrator: Failed to post task data to Splunk - {}".format(e))
        except Exception as e:
          sys.stderr.write("TA-puppet-alert-orchestrator: Failed to retrieve task parameters for {} - {} raw response: {}\n".format(task['name'], e, task_parameter))
      #
      # Build event message for available Plans by user.
      planlist = pie.orch.get_planlist(inputs['pe_console'],token)
      for plan in planlist:
        p_id = plan['id']
        plan_parameter = pie.orch.get_actionparams(p_id,token)
        pmessage = {
          'permitted': plan['permitted'],
          'plan_meta': None,
          'plan_name': plan['name'],
          'plan_params': [],
          'user': user,
        }
        #
        # Add any plan parameters to the event.
        try:
          pmessage['plan_meta'] = plan_parameter['metadata'].get('parameters', {})
          for param in pmessage['plan_meta']:
            pmessage['plan_params'].append(param)
          #
          # Post Plans via HEC endpoint
          try:
            host = inputs['pe_console'].replace("https://", "")
            hec_url = inputs['hec_url']
            hec_token = inputs['hec_token']
            post_plans = pie.hec.post_action(pmessage,host,hec_url,hec_token)
          except Exception as e:
            sys.stderr.write("TA-puppet-alert-orchestrator: Failed to post plan data to Splunk - {}".format(e))
        except Exception as e:
          sys.stderr.write("TA-puppet-alert-orchestrator: Failed to retrieve plan parameters for {} - {} raw response: {}\n".format(plan['name'], e, plan_parameter))
    except Exception as e:
      sys.stderr.write("TA-puppet-alert-orchestrator: Failed to build event message - {}".format(e))
except Exception as e:
  sys.stderr.write("TA-puppet-alert-orchestrator: Empty Account List - {}".format(e))
