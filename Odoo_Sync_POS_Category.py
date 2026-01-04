# Odoo Server Action: Sync POS Category
# Model: Product Template (product.template)

# --- Context Recovery ---
# Robustly find records to process without using 'globals()' which is blocked.

to_process = env['product.template']

# 1. Try 'active_ids' from Context (Manual 'Run' / Action Menu)
# This is the most reliable source for manual triggers.
if env.context.get('active_ids'):
    to_process |= env['product.template'].browse(env.context.get('active_ids'))

# 2. Try 'active_id' from Context
elif env.context.get('active_id'):
    to_process |= env['product.template'].browse(env.context.get('active_id'))

# 3. Try 'record' variable (Automated Actions)
# We know 'record' is defined in the scope (even if None), so checking 'if record' is safe.
elif record:
    to_process |= record

# --- Logic ---

if not to_process:
    # If we still have nothing, we can't do anything.
    # raise UserWarning("Run from Product View") # Optional: explicit warning
    pass

for product in to_process:
    if product.categ_id:
        target_name = product.categ_id.name
        
        # Search POS Category (Exact Match)
        pos_cat = env['pos.category'].search([('name', '=', target_name)], limit=1)
        
        if pos_cat:
            if pos_cat.id not in product.pos_categ_ids.ids:
                product.write({'pos_categ_ids': [(4, pos_cat.id)]})
                product.message_post(body=f"Auto-Sync: Linked POS Category '{pos_cat.name}'")
        else:
             product.message_post(body=f"Auto-Sync Warning: No POS Category found matching '{target_name}'")
