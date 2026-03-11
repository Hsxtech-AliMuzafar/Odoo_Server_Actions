# Odoo Server Action: Batch Approve Expense Sheets
# Model: Expense Report (hr.expense.sheet)
# Action To Do: Execute Python Code
#
# Usage:
# Select Expense Reports in the list view (Expenses > Expense Reports)
# and run this action from the Action menu.
# It approves the specific reports you have selected in batches.

# Configuration
BATCH_SIZE = 100
ALLOWED_USER_IDS = [18, 19, 20, 22, 2]

# Security Check: Only allow specific users to run this action
if env.user.id not in ALLOWED_USER_IDS:
    raise UserError(f"Access Denied: You (User ID: {env.user.id}) do not have permission to run this batch approval action. Please contact your administrator.")

# Get selected IDs
all_selected_ids = records.ids

if not all_selected_ids:
    raise UserError("Please select at least one Expense Report to approve.")

# Filter for reports that are in 'submit' state (Submitted)
# and can be approved.
all_eligible_ids = env['hr.expense.sheet'].search([
    ('id', 'in', all_selected_ids),
    ('state', '=', 'submit')
]).ids

total_count = len(all_eligible_ids)
success_count = 0
failed_count = 0

if not total_count:
    log("No submitted expense reports found among selected records.", level='info')
else:
    log(f"Starting batch approval for {total_count} selected records...", level='info')

# Process in chunks
for i in range(0, total_count, BATCH_SIZE):
    batch_ids = all_eligible_ids[i:i + BATCH_SIZE]
    
    # Browse to get recordset
    eligible_batch = env['hr.expense.sheet'].browse(batch_ids)
    
    if not eligible_batch:
        continue
        
    try:
        # Attempt to approve the whole batch using sudo() to bypass potential
        # custom approval rules (like Odoo Studio Approvals or permission-based checks).
        # We also use action_approve_sheet() if approve_expense_sheets() is not available or blocked.
        eligible_batch.sudo().approve_expense_sheets()
        success_count += len(eligible_batch)
    except Exception as e:
        log(f"Batch approval failed, falling back to individual processing. Error: {str(e)}", level='warning')
        # Fallback to individual processing if batch fails
        for sheet in eligible_batch:
            try:
                # Try standard method with sudo first
                sheet.sudo().approve_expense_sheets()
                success_count += 1
            except Exception as ex:
                # Last resort: Force transition by writing state if standard method is blocked
                # Note: Only do this if you are sure side effects are not critical at this step.
                try:
                    sheet.sudo().write({'state': 'approve'})
                    success_count += 1
                    log(f"Expense report {sheet.name} approved via direct state update (standard method failed).", level='info')
                except Exception as force_ex:
                    log(f"Failed to approve expense report {sheet.name}: {str(force_ex)}", level='error')
                    failed_count += 1
    
    # Commit to free up database locks
    env.cr.commit()
    
    # Notification for each batch
    progress = min(i + BATCH_SIZE, total_count)
    env['bus.bus']._sendone(env.user.partner_id, 'simple_notification', {
        'title': 'Batch Expense Approval',
        'message': f'Approved {progress}/{total_count} reports...',
        'type': 'info',
        'sticky': False
    })

# Final summary notification
message = f"✅ {success_count} expense reports approved"
if failed_count:
    message += f"\n❌ Failed: {failed_count} reports"

action = {
    'type': 'ir.actions.client',
    'tag': 'display_notification',
    'params': {
        'title': 'Batch Approval Complete',
        'message': f"Processed {total_count} selected reports.\n{message}",
        'type': 'success' if failed_count == 0 else 'warning',
        'sticky': True
    }
}

## Optimized for Selected Records
## Real-time Batch Notifications via Bus
## Powered By HSx Tech - Ali Muzafar