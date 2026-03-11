# Odoo Server Action: Generic Master Batch Archiver
# Model: Any (Supports any model with an 'active' field)
# Action To Do: Execute Python Code
#
# Usage:
# Select records in any list view (e.g., Products, Contacts, etc.)
# and run this action from the Action menu.
# It archives the selected records in batches with real-time notifications.

# Configuration
BATCH_SIZE = 100

# Get selected IDs
all_selected_ids = records.ids
model_name = records._name

if not all_selected_ids:
    raise UserError(f"Please select at least one record from {model_name} to process.")

# Check if the model has an 'active' field
if 'active' not in env[model_name]._fields:
    raise UserError(f"The model '{model_name}' does not support archiving (missing 'active' field).")

total_records = len(all_selected_ids)
archived_count = 0
failed_count = 0

log(f"Starting Generic Master Batch Archiver for {total_records} records of model {model_name}...", level='info')

# Process in chunks
for i in range(0, total_records, BATCH_SIZE):
    batch_ids = all_selected_ids[i:i + BATCH_SIZE]
    batch_records = env[model_name].browse(batch_ids)
    
    # Filter for records that are currently active
    to_archive = batch_records.filtered(lambda r: r.active)
    
    if not to_archive:
        continue
        
    try:
        # Attempt to archive the whole batch
        to_archive.write({'active': False})
        archived_count += len(to_archive)
    except Exception as e:
        log(f"Batch archive failed for {model_name}, falling back to individual processing: {str(e)}", level='warning')
        # Fallback to individual processing if batch fails
        for record in to_archive:
            try:
                record.write({'active': False})
                archived_count += 1
            except Exception as ex:
                log(f"Failed to archive {model_name} record ID {record.id}: {str(ex)}", level='error')
                failed_count += 1
    
    # Commit to free up database locks and save progress
    env.cr.commit()
    
    # Notification for each batch
    progress = min(i + BATCH_SIZE, total_records)
    env['bus.bus']._sendone(env.user.partner_id, 'simple_notification', {
        'title': 'Master Batch Archiver',
        'message': f'Processed {progress}/{total_records} records...',
        'type': 'info',
        'sticky': False
    })

# Final summary notification
message = f"✅ {archived_count} records archived."
if failed_count:
    message += f"\n❌ Failed: {failed_count} records."

action = {
    'type': 'ir.actions.client',
    'tag': 'display_notification',
    'params': {
        'title': 'Batch Archiving Complete',
        'message': f"Processed {total_records} selected {model_name} records.\n{message}",
        'type': 'success' if failed_count == 0 else 'warning',
        'sticky': True
    }
}

## Generic Multi-Module Archiver
## Real-time Batch Notifications via Bus
## Powered By HSx Tech - Ali Muzafar
