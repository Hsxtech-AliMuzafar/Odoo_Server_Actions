# Available variables:
#  - env: Odoo Environment on which the action is triggered
#  - model: Odoo Model of the record on which the action is triggered; is a void recordset
#  - record: record on which the action is triggered; may be void
#  - records: recordset of all records on which the action is triggered in multi-mode; may be void
#  - time, datetime, dateutil, timezone: useful Python libraries
#  - log: log(message, level='info'): logging function to record debug information in IrLogging table
#  - UserError: Warning Exception to use with raise
# To return an action, assign: action = {...}

# Configuration
TAX_ID = 302
PRODUCT_IDS = [3, 7]

# Find the tax record to ensure it exists
tax = env['account.tax'].browse(TAX_ID)
if not tax.exists():
    raise UserError(f"Tax with ID {TAX_ID} not found.")

count_updated_invoices = 0
count_updated_lines = 0

# Loop through selected invoices (records)
for invoice in records:
    # Filter lines that have the target products and don't already have the tax
    lines_to_update = invoice.invoice_line_ids.filtered(
        lambda l: l.product_id.id in PRODUCT_IDS and TAX_ID not in l.tax_ids.ids
    )
    
    if lines_to_update:
        # Add the tax to the lines
        for line in lines_to_update:
            line.write({'tax_ids': [(4, TAX_ID)]})
            count_updated_lines += 1
        
        count_updated_invoices += 1

# Logging results
msg = f"Success: Updated {count_updated_lines} lines across {count_updated_invoices} invoices with tax ID {TAX_ID}."
log(msg, level='info')

# User notification
action = {
    'type': 'ir.actions.client',
    'tag': 'display_notification',
    'params': {
        'title': 'Invoice Taxes Updated',
        'message': msg,
        'type': 'success',
        'sticky': False,
    }
}
