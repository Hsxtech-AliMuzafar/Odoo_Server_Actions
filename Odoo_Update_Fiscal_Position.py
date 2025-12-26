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
# Tax IDs extracted from the provided image (Range 380 to 400 inclusive)
# 380: FR Eco Taxe Meubles de rangement
# ...
# 400: FR Eco Taxe Tout type
tax_ids_to_map = list(range(380, 401))

# Counters for reporting
fp_count = 0
mapping_count = 0

for fiscal_position in records:
    fp_count += 1
    
    for tax_id in tax_ids_to_map:
        # OPTIONAL: Verify tax exists before trying to map it
        # Ideally we check existence to avoid errors if ID is missing in this DB
        tax = env['account.tax'].browse(tax_id)
        if not tax.exists():
            log(f"Warning: Tax ID {tax_id} does not exist in the database. Skipping.", level='warning')
            continue

        # Check if a mapping for this source tax ALREADY exists in this fiscal position
        # We don't want to duplicate or overwrite existing custom mappings
        existing_mapping = env['account.fiscal.position.tax'].search([
            ('position_id', '=', fiscal_position.id),
            ('tax_src_id', '=', tax_id)
        ])
        
        if not existing_mapping:
            # Create the mapping
            # tax_src_id: The tax on the product (The Eco Tax)
            # tax_dest_id: False (Empty) -> This effectively removes the tax when this FP is applied
            env['account.fiscal.position.tax'].create({
                'position_id': fiscal_position.id,
                'tax_src_id': tax_id,
                'tax_dest_id': False
            })
            mapping_count += 1

# Notification
msg = f"Success: Processed {fp_count} Fiscal Positions. Added {mapping_count} new tax mappings (Source IDs 380-400 -> None)."
log(msg, level='info')

action = {
    'type': 'ir.actions.client',
    'tag': 'display_notification',
    'params': {
        'title': 'Fiscal Position Update',
        'message': msg,
        'type': 'success',
        'sticky': False,
    }
}