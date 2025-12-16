# Available variables:
#  - env: Odoo Environment on which the action is triggered
#  - model: Odoo Model of the record on which the action is triggered; is a void recordset
#  - record: record on which the action is triggered; may be void
#  - records: recordset of all records on which the action is triggered in multi-mode
#  - time, datetime, dateutil, timezone: useful Python libraries
#  - float_compare: Odoo standard float comparison function
#  - log: log(message, level='info'): logging function to record debug information in IrLogging table
#  - UserError: Warning Exception to use with raise
#  - Command: x2Many commands namespace

# Requirement: Cancel Vendor Bills that are in draft state.

# 1. Filter Records
# Filter for Vendor Bills ('in_invoice') or Refunds ('in_refund') that are in 'draft' state.
bills_to_cancel = records.filtered(lambda r: r.move_type in ['in_invoice', 'in_refund'] and r.state == 'draft')

if not bills_to_cancel:
    raise UserError("No draft vendor bills found in the selection.")

count = len(bills_to_cancel)

# 2. Perform Action
# Call the standard Odoo button_cancel method
bills_to_cancel.button_cancel()

# 3. Notification
msg = f"Successfully cancelled {count} draft vendor bill(s)."
action = {
    'type': 'ir.actions.client',
    'tag': 'display_notification',
    'params': {
        'title': 'Cancelled Draft Bills',
        'message': msg,
        'sticky': False,
        'type': 'success',
    }
}
