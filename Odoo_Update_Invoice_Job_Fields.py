# Odoo Server Action: Update Invoice Job Fields from Sales Order
# Model: Journal Entry (account.move)
# Action To Do: Execute Python Code
#
# Usage:
# Select Invoices in the list view (Accounting > Invoices)
# and run this action from the Action menu.
# It updates job-related fields on invoices based on their linked sales orders.

# Configuration
BATCH_SIZE = 50

# Get selected IDs from 'records' (standard for Server Actions)
all_selected_ids = records.ids

if not all_selected_ids:
    raise UserError("Please select at least one Invoice to process.")

total_invoices = len(all_selected_ids)
updated_count = 0

log(f"Starting batch job field update for {total_invoices} records...", level='info')

# Process in chunks of invoice IDs
for i in range(0, total_invoices, BATCH_SIZE):
    batch_invoice_ids = all_selected_ids[i:i + BATCH_SIZE]
    batch_records = env['account.move'].browse(batch_invoice_ids)
    
    for record in batch_records:
        try:
            # Map sales orders via invoice lines
            sale_orders = record.invoice_line_ids.mapped('sale_line_ids.order_id')
            
            if sale_orders:
                # Use the first related sales order
                so = sale_orders[0]
                record.write({
                    'x_studio_job_installation_date_1': so.x_studio_related_installation,
                    'x_studio_job_unit_location': so.x_studio_related_unit_location,
                    'x_studio_job_unit_number': so.x_studio_related_unit_number,
                    'x_studio_job_unit_name': so.x_studio_related_job_name,
                })
                updated_count += 1
            else:
                # Clear fields if no sales order is linked
                record.write({
                    'x_studio_job_installation_date_1': False,
                    'x_studio_job_unit_location': False,
                    'x_studio_job_unit_number': False,
                    'x_studio_job_unit_name': False,
                })
        except Exception as e:
            log(f"Error updating invoice {record.name or record.id}: {str(e)}", level='error')

    # Commit to free up database locks and save progress
    env.cr.commit()
    
    # Progress notification via Bus system
    progress = min(i + BATCH_SIZE, total_invoices)
    env['bus.bus']._sendone(env.user.partner_id, 'simple_notification', {
        'title': 'Invoice Job Update',
        'message': f'Processed {progress}/{total_invoices} invoices...',
        'type': 'info',
        'sticky': False
    })

# Final summary notification
action = {
    'type': 'ir.actions.client',
    'tag': 'display_notification',
    'params': {
        'title': 'Update Complete',
        'message': f"Processed {total_invoices} selected invoices.\n✅ Updated {updated_count} records.",
        'type': 'success',
        'sticky': True
    }
}

## Optimized for Selected Records
## Real-time Batch Notifications via Bus
## Pulls fields: Installation Date, Unit Location, Unit Number, Job Name
## Powered By HSx Tech - Ali Muzafar
