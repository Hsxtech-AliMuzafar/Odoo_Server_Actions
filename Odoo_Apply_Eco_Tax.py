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
tax_name = 'Eco Taxe 1 €'

# Find the tax
taxes = env['account.tax'].search([('name', '=', tax_name)])

if len(taxes) == 1:
    eco_tax = taxes[0]
    
    # OPTIMIZATION:
    # 1. Use 'records' (selected products) instead of searching all.
    # 2. Filter out products that already have this tax.
    
    # 'records' is the global variable containing selected records
    products_to_process = records
    
    # Filter: Only keep products that DON'T have the tax yet
    # This avoids unnecessary writes and "modified" dates changing
    products_to_update = products_to_process.filtered(lambda p: eco_tax.id not in p.taxes_id.ids)
    
    total_products = len(products_to_update)
    
    if total_products > 0:
        # Write directly. For selected records (usually <1000), direct write is fine.
        # If massive selection is expected, we could batch, but standard actions usually handle selection well.
        products_to_update.write({'taxes_id': [(4, eco_tax.id)]})
        
        processed_count = total_products
    else:
        processed_count = 0
        log("No selected products needed update (all already had the tax).", level='info')

    # Adding notification to the user
    msg = f"Success: Added '{tax_name}' to {processed_count} products."
    log(msg, level='info')
    
    action = {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
            'title': 'Tax Update Complete',
            'message': msg,
            'type': 'success',
            'sticky': False,  # Set to True if you want it to stay until closed
        }
    }

elif len(taxes) == 0:
    raise UserError(f"Tax '{tax_name}' not found. Please check the tax name.")
else:
    raise UserError(f"Found {len(taxes)} taxes with the name '{tax_name}'. Please rename one to be unique or use an ID.")
