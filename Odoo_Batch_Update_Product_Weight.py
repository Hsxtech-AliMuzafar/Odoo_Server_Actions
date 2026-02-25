# Odoo Server Action: Batch Update Product Weight
# Model: Product Template (product.template)
# Action To Do: Execute Python Code
#
# Usage:
# Select products in the list view (Inventory > Products)
# and run this action from the Action menu.
# It updates the weight of the selected products to 1 in batches.

# Configuration
BATCH_SIZE = 100

# Get selected IDs
all_selected_ids = env.context.get('active_ids', [])

if not all_selected_ids:
    raise UserError("Please select at least one Product to update.")

# Filter for products that actually need an update (where weight is not 1)
# This reduces unnecessary database writes.
to_update_ids = env['product.template'].search([
    ('id', 'in', all_selected_ids),
    ('weight', '!=', 1)
]).ids

total_count = len(to_update_ids)
updated_count = 0

if total_count == 0:
    action = {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
            'title': 'No Update Needed',
            'message': 'All selected products already have a weight of 1.',
            'type': 'info',
            'sticky': False
        }
    }
else:
    log(f"Starting batch weight update for {total_count} products...", level='info')

    # Process in chunks
    for i in range(0, total_count, BATCH_SIZE):
        batch_ids = to_update_ids[i:i + BATCH_SIZE]
        
        # Batch write is more efficient than individual writes
        batch_records = env['product.template'].browse(batch_ids)
        batch_records.write({'weight': 1.0})
        
        updated_count += len(batch_records)
        
        # Commit to free up database locks and save progress
        env.cr.commit()
        
        # Real-time progress notification
        progress = min(i + BATCH_SIZE, total_count)
        env['bus.bus']._sendone(env.user.partner_id, 'simple_notification', {
            'title': 'Weight Update Progress',
            'message': f'Updated {progress}/{total_count} products...',
            'type': 'info',
            'sticky': False
        })

    # Final summary notification
    action = {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
            'title': 'Batch Weight Update Complete',
            'message': f"Successfully updated weight to 1 for {updated_count} products.",
            'type': 'success',
            'sticky': True
        }
    }

## Optimized for Batch Efficiency
## Real-time Batch Notifications via Bus
## Powered By HSx Tech - Ali Muzafar