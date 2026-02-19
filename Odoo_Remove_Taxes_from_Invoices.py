# Odoo Server Action: Batch Remove Taxes from All Invoice Lines
# Model: Journal Entry (account.move)
# Action To Do: Execute Python Code
#
# Usage:
# Select Invoices in the list view (Accounting > Invoices)
# and run this action from the Action menu.
# It clears all taxes from the selected invoices in batches.

# Configuration
BATCH_SIZE = 100

# Get selected IDs
all_eligible_ids = records.ids

if not all_eligible_ids:
    raise UserError("Please select at least one Invoice to update.")

total_count = len(all_eligible_ids)
success_count = 0
removed_lines_count = 0

log(f"Starting batch tax removal for {total_count} selected invoices...", level='info')

# Process in chunks
for i in range(0, total_count, BATCH_SIZE):
    batch_ids = all_eligible_ids[i:i + BATCH_SIZE]
    
    # Browse current batch
    invoice_batch = env['account.move'].browse(batch_ids)
    
    batch_updated_invoices = 0
    for invoice in invoice_batch:
        # Get lines that have any taxes
        lines_with_taxes = invoice.invoice_line_ids.filtered(lambda l: l.tax_ids)
        
        if lines_with_taxes:
            # Clear all taxes from the lines
            for line in lines_with_taxes:
                line.write({'tax_ids': [(5, 0, 0)]})
                removed_lines_count += 1
            batch_updated_invoices += 1
    
    success_count += batch_updated_invoices
    
    # Commit to free up database locks
    env.cr.commit()
    
    # Notification for each batch
    progress = min(i + BATCH_SIZE, total_count)
    env['bus.bus']._sendone(env.user.partner_id, 'simple_notification', {
        'title': 'Batch Processing',
        'message': f'Tax Removal Progress: {progress}/{total_count} invoices...',
        'type': 'warning',
        'sticky': False
    })

# Final summary notification
message = f"✅ {success_count} invoices updated"
message += f"\n🗑 {removed_lines_count} lines cleared of taxes"

action = {
    'type': 'ir.actions.client',
    'tag': 'display_notification',
    'params': {
        'title': 'Batch Tax Removal Complete',
        'message': f"Processed {total_count} selected invoices.\n{message}",
        'type': 'success',
        'sticky': True
    }
}

## Optimized for Selected Records
## Real-time Batch Notifications via Bus
## Powered By HSx Tech - Ali Muzafar
