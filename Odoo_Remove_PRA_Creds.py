# Model: pos.config
# Action Type: Execute Python Code

cleared = []

for record in records:
    # check if any of the fields had data or were enabled
    if (record.pra_production_api_url 
        or record.pra_production_pos_id 
        or record.pra_production_api_key 
        or record.pra_production_access_code 
        or record.pra_sync_enabled 
        or record.pra_integration_enabled
        or record.srb_enabled
        or record.srb_username
        or record.srb_password
        or record.srb_api_url
        or record.srb_sync_enabled):

        record.write({
            'pra_production_api_url': False,
            'pra_production_pos_id': False,
            'pra_production_api_key': False,
            'pra_production_access_code': False,
            'pra_sync_enabled': False,
            'pra_integration_enabled': False,
            'srb_enabled': False,
            'srb_username': False,
            'srb_password': False,
            'srb_api_url': False,
            'srb_sync_enabled': False,
        })
        cleared.append(record.display_name)

if cleared:
    message = "Cleared credentials for:\n- " + "\n- ".join(cleared)
else:
    message = "No POS Configs required clearing."

action = {
    "type": "ir.actions.client",
    "tag": "display_notification",
    "params": {
        "title": "POS Credentials Cleanup",
        "message": message,
        "sticky": False,
        "type": "success",
    }
}
action
