
# encoding = utf-8
import json
from puppet_report_generation import run_report_generation

# given a setting, check to see if the alert is configured with default override
def override(setting_name, helper):
    alert_setting = helper.get_param(setting_name)
    global_setting = helper.get_global_setting(setting_name)

    if alert_setting is not None and alert_setting != '':
        final_value = alert_setting
        helper.log_debug("Alert value present for '{}' it is '{}'".format(setting_name, final_value))
    elif global_setting is not None and global_setting != '':
        final_value = global_setting
        helper.log_debug("Alert value NOT present for '{}', using Global value '{}'".format(setting_name,final_value))
    else:
        helper.log_debug("There is no value, None returned")
        final_value = None
    
    return final_value

# function to make sure we only set values we know aren't None
def notnone(default_value, possible_none, helper):
    if possible_none is not None and possible_none != '':
        helper.log_debug("notnone: True")
        return possible_none
    else:
        helper.log_debug("notnone: False")
        return default_value



def process_event(helper, *args, **kwargs):
    """
    # IMPORTANT
    # Do not remove the anchor macro:start and macro:end lines.
    # These lines are used to generate sample code. If they are
    # removed, the sample code will not be updated when configurations
    # are updated.

    [sample_code_macro:start]

    # The following example gets and sets the log level
    helper.set_log_level(helper.log_level)

    # The following example gets account information
    user_account = helper.get_user_credential("<account_name>")

    # The following example gets the setup parameters and prints them to the log
    puppet_enterprise_console = helper.get_global_setting("puppet_enterprise_console")
    helper.log_info("puppet_enterprise_console={}".format(puppet_enterprise_console))
    puppet_default_user = helper.get_global_setting("puppet_default_user")
    helper.log_info("puppet_default_user={}".format(puppet_default_user))
    splunk_hec_url = helper.get_global_setting("splunk_hec_url")
    helper.log_info("splunk_hec_url={}".format(splunk_hec_url))
    splunk_hec_token = helper.get_global_setting("splunk_hec_token")
    helper.log_info("splunk_hec_token={}".format(splunk_hec_token))
    bolt_user = helper.get_global_setting("bolt_user")
    helper.log_info("bolt_user={}".format(bolt_user))
    puppet_action_hec_token = helper.get_global_setting("puppet_action_hec_token")
    helper.log_info("puppet_action_hec_token={}".format(puppet_action_hec_token))
    puppet_bolt_server = helper.get_global_setting("puppet_bolt_server")
    helper.log_info("puppet_bolt_server={}".format(puppet_bolt_server))
    puppet_db_url = helper.get_global_setting("puppet_db_url")
    helper.log_info("puppet_db_url={}".format(puppet_db_url))
    timeout = helper.get_global_setting("timeout")
    helper.log_info("timeout={}".format(timeout))
    pe_console = helper.get_global_setting("pe_console")
    helper.log_info("pe_console={}".format(pe_console))

    # The following example gets the alert action parameters and prints them to the log
    puppet_enterprise_console = helper.get_param("puppet_enterprise_console")
    helper.log_info("puppet_enterprise_console={}".format(puppet_enterprise_console))

    puppet_default_user = helper.get_param("puppet_default_user")
    helper.log_info("puppet_default_user={}".format(puppet_default_user))

    splunk_hec_url = helper.get_param("splunk_hec_url")
    helper.log_info("splunk_hec_url={}".format(splunk_hec_url))

    splunk_hec_token = helper.get_param("splunk_hec_token")
    helper.log_info("splunk_hec_token={}".format(splunk_hec_token))

    puppet_action_hec_token = helper.get_param("puppet_action_hec_token")
    helper.log_info("puppet_action_hec_token={}".format(puppet_action_hec_token))

    puppet_db_url = helper.get_param("puppet_db_url")
    helper.log_info("puppet_db_url={}".format(puppet_db_url))

    timeout = helper.get_param("timeout")
    helper.log_info("timeout={}".format(timeout))

    pe_console = helper.get_param("pe_console")
    helper.log_info("pe_console={}".format(pe_console))


    # The following example adds two sample events ("hello", "world")
    # and writes them to Splunk
    # NOTE: Call helper.writeevents() only once after all events
    # have been added
    helper.addevent("hello", sourcetype="sample_sourcetype")
    helper.addevent("world", sourcetype="sample_sourcetype")
    helper.writeevents(index="summary", host="localhost", source="localhost")

    # The following example gets the events that trigger the alert
    events = helper.get_events()
    for event in events:
        helper.log_info("event={}".format(event))

    # helper.settings is a dict that includes environment configuration
    # Example usage: helper.settings["server_uri"]
    helper.log_info("server_uri={}".format(helper.settings["server_uri"]))
    [sample_code_macro:end]
    """
    
    helper.set_log_level(helper.log_level)

    helper.log_info("Alert action puppet_generate_detailed_report started.")
    
    helper.log_info("Log_level: {}".format(helper.log_level))
    
    # we use the override function to ensure we always use the alert value over the global if one exists
    helper.log_info("Credential lookup")
    user_name = override('puppet_default_user', helper)

    # get_user_credential gives us the user_name, unfortunately we can't search by ID even though inputs can
    puppet_read_account = helper.get_user_credential(user_name)
    puppet_read_user = puppet_read_account["username"]
    puppet_read_user_pass = puppet_read_account["password"]

    # Check if users are utilizing RBAC tokens instead of Passwords.
    # This setting is passed in as a string; so we are converting it to boolean here:
    rbac_token = bool(int(puppet_read_account["pe_token"]))

    helper.log_debug("username={}".format(puppet_read_user))
    
    # load the rest of the settings
    helper.log_info("Retrieving settings")
    # Get PE Console, this doesn't set pe_console value, that is from the alert itself
    puppet_enterprise_console = override("puppet_enterprise_console", helper)
    helper.log_debug("puppet_enterprise_console={}".format(puppet_enterprise_console))
    
    # get the URL that we are sending the new event to
    splunk_hec_url = override("splunk_hec_url", helper)
    helper.log_debug("splunk_hec_url={}".format(splunk_hec_url))
    
    # get the token we are using for the event
    splunk_hec_token = override("splunk_hec_token", helper)
    helper.log_debug("splunk_hec_token={}".format(splunk_hec_token))

    # we like to be chatty about it
    puppet_action_hec_token = override("puppet_action_hec_token", helper)
    helper.log_debug("puppet_action_hec_token={}".format(puppet_action_hec_token))
    
    # if we have standalone pdb server, this is who we talk to
    puppet_db_url = override("puppet_db_url", helper)
    helper.log_debug("puppet_db_url={}".format(puppet_db_url))

    # this is the timeout we use, rarely an issue for pdb lookup
    timeout = override("timeout", helper)
    helper.log_debug("timeout={}".format(timeout))

    # create our alert object to build the actual report
    helper.log_info("Assembling alert data")
    alert = {}
    alert['global'] = {}
    alert['param'] = {}
    
    alert['global']['puppet_enterprise_console'] = puppet_enterprise_console
    alert['global']['puppet_read_user'] = puppet_read_user
    alert['global']['puppet_read_user_pass'] = puppet_read_user_pass
    alert['global']['splunk_hec_url'] = splunk_hec_url
    alert['global']['splunk_hec_token'] = splunk_hec_token
    alert['global']['timeout'] = timeout
    alert['global']['pe_token'] = rbac_token
    
    # we're using the notnone function to ensure we always have a value, even if it's duplicate
    # we call it with notnone(default_value, possible_none, helper) - default_value is returned if possible_none is None
    alert['global']['puppet_action_hec_token'] = notnone(splunk_hec_token, puppet_action_hec_token, helper)
    alert['global']['puppet_db_url'] = notnone(puppet_enterprise_console, puppet_db_url, helper)


    helper.log_debug("Getting event data")
    # we're going to strip out the three things we need from every event
    # we're also not going to assume we are sent one event
    events = helper.get_events()

    # these are the reports we need to retrieve
    transaction_uuids = []

    for event_raw in events:
        event = json.loads(event_raw["_raw"])
        helper.log_debug("Event Data Raw: {}".format(event))
        # copy the needed data to a new dictionary
        temp_dict = {
            'pe_console': event['pe_console'],
            'transaction_uuid': event['transaction_uuid'],
            'host': event['certname'],
        }
        transaction_uuids.append(temp_dict.copy())

    helper.log_debug("Events: {}".format(transaction_uuids))
    run_report_generation(alert, transaction_uuids, helper)

    helper.log_info("Alert action puppet_generate_detailed_report completed.")

    return 0
