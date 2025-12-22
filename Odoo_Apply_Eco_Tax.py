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
# The substring to search for in tax names
tax_search_string = 'FR Eco Taxe'

# Find the taxes
# We use 'ilike' for case-insensitive matching logic, though standard Odoo distinct search is usually case sensitive depending on db stats.
# 'ilike' in Odoo domain usually maps to ILIKE in Postgres which is case insensitive.
taxes = env['account.tax'].search([('name', 'ilike', tax_search_string)])

if len(taxes) > 0:
    # We found one or more taxes matching the criteria.
    # We will add ALL of them to the selected products.
    
    # 'records' is the global variable containing selected records (products)
    products_to_process = records
    
    # We want to avoid adding a tax if it's already there.
    # Since we might have multiple taxes to add, we can't do a simple "if not in" filter for a single tax.
    # Instead, we'll iterate or use a more complex write.
    # Simplest safe approach for server actions (considering performance vs complexity):
    # Iterate products and add missing taxes.
    
    count_updated = 0
    
    # Prepare the list of tax IDs to add
    tax_ids_to_add = taxes.ids
    
    for product in products_to_process:
        # Get current tax IDs on the product
        current_tax_ids = product.taxes_id.ids
        
        # Determine which of the found taxes are NOT yet required on this product
        new_tax_ids = [t_id for t_id in tax_ids_to_add if t_id not in current_tax_ids]
        
        if new_tax_ids:
            # Add the missing taxes
            # (4, id) adds a relationship to the record with id
            write_vals = [(4, t_id) for t_id in new_tax_ids]
            product.write({'taxes_id': write_vals})
            count_updated += 1
            
    # Adding notification to the user
    msg = f"Success: Found {len(taxes)} taxes matching '{tax_search_string}'. Updated {count_updated} products."
    log(msg, level='info')
    
    action = {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
            'title': 'Eco Tax Update Complete',
            'message': msg,
            'type': 'success',
            'sticky': False,
        }
    }

else:
    # No tax found
    msg = f"No tax found containing '{tax_search_string}'."
    raise UserError(msg)
