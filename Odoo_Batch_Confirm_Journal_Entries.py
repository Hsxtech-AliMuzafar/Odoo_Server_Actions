# Odoo Server Action: Batch Confirm Journal Entries
# Model: Journal Entry (account.move)
# Action To Do: Execute Python Code
#
# Usage:
# Select Journal Entries in the list view (Accounting > Journal Entries)
# and run this action from the Action menu.
# It confirms (posts) the specific entries you have selected in batches.

# Configuration
BATCH_SIZE = 100

# Get selected IDs
all_eligible_ids = records.ids

if not all_eligible_ids:
    raise UserError("Please select at least one Journal Entry to confirm.")

# Filter for entries that can be posted
all_eligible_ids = env['account.move'].search([
    ('id', 'in', all_eligible_ids),
    ('state', '=', 'draft')
]).ids

total_count = len(all_eligible_ids)
success_count = 0
failed_count = 0

log(f"Starting batch confirmation for {total_count} selected records...", level='info')

# Process in chunks
for i in range(0, total_count, BATCH_SIZE):
    batch_ids = all_eligible_ids[i:i + BATCH_SIZE]
    
    # Browse and filter again to be safe
    eligible_batch = env['account.move'].browse(batch_ids).filtered(lambda m: m.state == 'draft')
    
    if not eligible_batch:
        continue
        
    try:
        # Attempt to confirm the whole batch
        # action_post() is the standard method for posting in newer Odoo versions
        eligible_batch.action_post()
        success_count += len(eligible_batch)
    except Exception as e:
        # Fallback to individual processing if batch fails
        for move in eligible_batch:
            try:
                move.action_post()
                success_count += 1
            except Exception as ex:
                log(f"Failed to confirm entry {move.name}: {str(ex)}", level='error')
                failed_count += 1
    
    # Commit to free up database locks
    env.cr.commit()
    
    # Notification for each batch
    progress = min(i + BATCH_SIZE, total_count)
    env['bus.bus']._sendone(env.user.partner_id, 'simple_notification', {
        'title': 'Batch Confirmation',
        'message': f'Confirmed {progress}/{total_count} entries...',
        'type': 'info',
        'sticky': False
    })

# Final summary notification
message = f"✅ {success_count} entries confirmed"
if failed_count:
    message += f"\n❌ Failed: {failed_count} entries"

action = {
    'type': 'ir.actions.client',
    'tag': 'display_notification',
    'params': {
        'title': 'Batch Confirmation Complete',
        'message': f"Processed {total_count} selected entries.\n{message}",
        'type': 'success' if failed_count == 0 else 'warning',
        'sticky': True
    }
}

## Optimized for Selected Records
## Real-time Batch Notifications via Bus
## Powered By HSx Tech - Ali Muzafar
