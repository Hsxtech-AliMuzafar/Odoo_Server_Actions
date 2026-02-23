# Odoo Server Action: Batch Remove Invoice Attachments
# Model: Journal Entry (account.move)
# Action To Do: Execute Python Code
#
# Usage:
# Select Invoices in the list view (Accounting > Invoices)
# and run this action from the Action menu.
# It removes all attachments linked to the specific invoices you have selected in batches.

# Configuration
BATCH_SIZE = 50

# Get selected IDs
all_selected_ids = records.ids

if not all_selected_ids:
    raise UserError("Please select at least one Invoice to process.")

total_invoices = len(all_selected_ids)
total_attachments_removed = 0

log(f"Starting batch attachment removal for {total_invoices} selected records of model {records._name}...", level='info')

# Process in chunks of invoice IDs
for i in range(0, total_invoices, BATCH_SIZE):
    batch_invoice_ids = all_selected_ids[i:i + BATCH_SIZE]
    
    # Find all attachments linked to these specific records
    # 1. Direct attachments (current model)
    # 2. Legacy model attachments (account.invoice for move)
    # 3. Related fields (attachment_ids, document_ids)
    # 4. Chatter attachments (mail.message)
    
    # Get related IDs from fields if they exist
    rel_attachment_ids = []
    batch_records = env[records._name].browse(batch_invoice_ids)
    for field in ['attachment_ids', 'document_ids']:
        if field in batch_records._fields:
            rel_attachment_ids += batch_records.mapped(field).ids
            
    # Get message IDs linked to these records
    messages = env['mail.message'].search([
        ('model', '=', records._name),
        ('res_id', 'in', batch_invoice_ids)
    ])
    message_ids = messages.ids
    log(f"Found {len(message_ids)} messages for batch of {len(batch_invoice_ids)} records", level='info')
    
    # Build a broad domain
    attachments_to_remove = env['ir.attachment'].search([
        '|', '|', '|',
        '&', ('res_model', '=', records._name), ('res_id', 'in', batch_invoice_ids),
        '&', ('res_model', '=', 'account.invoice'), ('res_id', 'in', batch_invoice_ids),
        '&', ('res_model', '=', 'mail.message'), ('res_id', 'in', message_ids),
        ('id', 'in', rel_attachment_ids)
    ])
    log(f"Found {len(attachments_to_remove)} attachments to remove in this batch", level='info')
    
    if attachments_to_remove:
        count = len(attachments_to_remove)
        try:
            attachments_to_remove.unlink()
            total_attachments_removed += count
        except Exception as e:
            log(f"Failed to remove some attachments for invoices {batch_invoice_ids}: {str(e)}", level='error')
    
    # Commit to free up database locks and save progress
    env.cr.commit()
    
    # Notification for each batch
    progress = min(i + BATCH_SIZE, total_invoices)
    env['bus.bus']._sendone(env.user.partner_id, 'simple_notification', {
        'title': 'Attachment Removal',
        'message': f'Processed {progress}/{total_invoices} invoices...',
        'type': 'info',
        'sticky': False
    })

# Final summary notification
action = {
    'type': 'ir.actions.client',
    'tag': 'display_notification',
    'params': {
        'title': 'Attachment Removal Complete',
        'message': f"Processed {total_invoices} selected invoices.\n✅ Removed {total_attachments_removed} attachments.",
        'type': 'success',
        'sticky': True
    }
}

## Optimized for Selected Records
## Real-time Batch Notifications via Bus
## Powered By HSx Tech - Ali Muzafar
