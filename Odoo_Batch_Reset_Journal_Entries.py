# Odoo Server Action: Batch Reset Journal Entries to Draft
# Model: Journal Entry (account.move)
# Action To Do: Execute Python Code
#
# Usage:
# Select Journal Entries in the list view (Accounting > Journal Entries)
# and run this action from the Action menu.
# It only processes the specific entries you have selected.

# Configuration
BATCH_SIZE = 100

# Get selected IDs - Only works on specific selection as requested
active_ids = env.context.get('active_ids', [])

if not active_ids:
    raise UserError("Please select at least one Journal Entry to reset.")

# Filter for entries that can be reset to draft
all_eligible_ids = env['account.move'].search([
    ('id', 'in', active_ids),
    ('state', 'in', ('posted', 'cancel'))
]).ids

total_count = len(all_eligible_ids)
success_count = 0
failed_count = 0

log(f"Starting batch reset for {total_count} selected records...", level='info')

# Process in chunks
for i in range(0, total_count, BATCH_SIZE):
    batch_ids = all_eligible_ids[i:i + BATCH_SIZE]
    
    # Browse and filter again to be safe
    eligible_batch = env['account.move'].browse(batch_ids).filtered(lambda m: m.state in ('posted', 'cancel'))
    
    if not eligible_batch:
        continue
        
    try:
        # Attempt to process the whole batch
        eligible_batch.button_draft()
        success_count += len(eligible_batch)
    except Exception as e:
        # Fallback to individual processing if batch fails
        for move in eligible_batch:
            try:
                move.button_draft()
                success_count += 1
            except Exception:
                failed_count += 1
    
    # Commit to free up database locks
    env.cr.commit()
    
    # Notification for each batch
    progress = min(i + BATCH_SIZE, total_count)
    env['bus.bus']._sendone(env.user.partner_id, 'simple_notification', {
        'title': 'Batch Processing',
        'message': f'Processed {progress}/{total_count} entries...',
        'type': 'info',
        'sticky': False
    })

# Final summary notification
message = f"✅ {success_count} entries reset to draft"
if failed_count:
    message += f"\n❌ Failed: {failed_count} entries"

action = {
    'type': 'ir.actions.client',
    'tag': 'display_notification',
    'params': {
        'title': 'Batch Reset Complete',
        'message': f"Processed {total_count} selected entries.\n{message}",
        'type': 'success' if failed_count == 0 else 'warning',
        'sticky': True
    }
}

## Optimized for Selected Records
## Real-time Batch Notifications via Bus
## Powered By HSx Tech - Ali Muzafar
