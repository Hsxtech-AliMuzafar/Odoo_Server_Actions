# Odoo 18 Server Action: Batch Approve Expense Sheets (FIXED)
# Model: hr.expense.sheet
# Action To Do: Execute Python Code
#
# Key fixes vs the original:
#   1. approve_expense_sheets() doesn't exist in Odoo 18 - uses _do_approve() instead
#      (action_approve_expense_sheets silently no-ops when env.user isn't the assigned
#       approver on each sheet, even under sudo)
#   2. Exceptions are LOGGED, not silently swallowed
#   3. State is re-read after approval to verify it actually transitioned
#   4. Notification title and message reflect actual outcome

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------
BATCH_SIZE = 100
ALLOWED_USER_IDS = [18, 19, 20, 22, 2]

# ------------------------------------------------------------
# Security
# ------------------------------------------------------------
if env.user.id not in ALLOWED_USER_IDS:
    raise UserError(
        f"Access Denied: You (User ID: {env.user.id}) do not have permission to run "
        "this batch approval action. Please contact your administrator."
    )

all_selected_ids = records.ids
if not all_selected_ids:
    raise UserError("Please select at least one Expense Report to validate.")

Sheet = env['hr.expense.sheet'].sudo()
all_selected = Sheet.browse(all_selected_ids)

# ------------------------------------------------------------
# Pre-flight: show the user what will and won't be processed
# ------------------------------------------------------------
state_counts = {}
for s in all_selected:
    state_counts[s.state] = state_counts.get(s.state, 0) + 1

selected_sheets = all_selected.filtered(lambda s: s.state == 'submit')
skipped_non_submit = len(all_selected) - len(selected_sheets)

# ------------------------------------------------------------
# Phase 1: Duplicate validation (blocking)
# ------------------------------------------------------------
flagged_details = []
seen_in_selection = {}

for sheet in selected_sheets:
    amount = 0.0
    if 'amount_total' in sheet._fields:
        amount = sheet.amount_total
    elif 'total_amount' in sheet._fields:
        amount = sheet.total_amount

    name = sheet.name or ''
    employee_id = sheet.employee_id.id
    key = (name, amount, employee_id)

    existing_dup = Sheet.search([
        ('id', '!=', sheet.id),
        ('name', '=', name),
        ('total_amount', '=', amount),
        ('employee_id', '=', employee_id),
        ('state', 'in', ['approve', 'done', 'post']),
    ], limit=1)

    is_selection_dup = key in seen_in_selection

    if existing_dup or is_selection_dup:
        reason = "System Match (Already Approved)" if existing_dup else "Selection Match (Duplicate in Batch)"
        flagged_details.append(f"  - {sheet.name or 'Unnamed'} | Amt: {amount} | {reason}")

    seen_in_selection[key] = True

if flagged_details:
    raise UserError(
        "VALIDATION FAILED: Potential Duplicates Detected\n\n"
        + "\n".join(flagged_details)
        + "\n\nOperation cancelled. Please review/correct these records before retrying."
    )

# ------------------------------------------------------------
# Phase 2: Batch approval via _do_approve() with verification
# ------------------------------------------------------------
total_to_approve = len(selected_sheets)
success_count = 0
failed_count = 0
no_change_count = 0
error_samples = []  # keep first few error messages for the notification

if total_to_approve:
    log(f"Batch approving {total_to_approve} expense reports via _do_approve()", level='info')

    for i in range(0, total_to_approve, BATCH_SIZE):
        batch = selected_sheets[i:i + BATCH_SIZE]
        try:
            batch._do_approve()
            batch.invalidate_recordset()
            approved = batch.filtered(lambda s: s.state == 'approve')
            stuck = batch - approved
            success_count += len(approved)
            if stuck:
                no_change_count += len(stuck)
                for s in stuck:
                    msg = f"Sheet {s.id} ({s.name}): _do_approve ran but state is still '{s.state}'"
                    log(msg, level='warning')
                    if len(error_samples) < 5:
                        error_samples.append(msg)
        except Exception as batch_err:
            log(f"Batch _do_approve failed: {str(batch_err)}. Falling back to per-record.", level='warning')
            for sheet in batch:
                try:
                    sheet._do_approve()
                    sheet.invalidate_recordset()
                    if sheet.state == 'approve':
                        success_count += 1
                    else:
                        no_change_count += 1
                        msg = f"Sheet {sheet.id} ({sheet.name}): method ran but state is '{sheet.state}'"
                        log(msg, level='warning')
                        if len(error_samples) < 5:
                            error_samples.append(msg)
                except Exception as sheet_err:
                    failed_count += 1
                    msg = f"Sheet {sheet.id} ({sheet.name}): {str(sheet_err)}"
                    log(msg, level='warning')
                    if len(error_samples) < 5:
                        error_samples.append(msg)

        env.cr.commit()
else:
    log("No eligible 'submit' state reports found in selection.", level='info')

# ------------------------------------------------------------
# Phase 3: Honest notification
# ------------------------------------------------------------
lines = []
lines.append(f"Selected: {len(all_selected)} reports")

state_parts = []
for st, cnt in sorted(state_counts.items()):
    state_parts.append(f"{st}={cnt}")
lines.append(f"Breakdown: {', '.join(state_parts)}")

if skipped_non_submit:
    lines.append(f"Skipped (not in 'submit' state): {skipped_non_submit}")

lines.append(f"Approved: {success_count} / {total_to_approve}")

if no_change_count:
    lines.append(f"Ran without error but state did NOT change: {no_change_count}")
if failed_count:
    lines.append(f"Raised exceptions: {failed_count}")

if error_samples:
    lines.append("")
    lines.append("First errors (see server log for full list):")
    for m in error_samples:
        lines.append(f"  - {m}")

# Determine title and type honestly
if success_count == total_to_approve and total_to_approve > 0:
    notif_title = "Batch Approval: All Approved"
    notif_type = 'success'
elif success_count > 0:
    notif_title = "Batch Approval: Partial Success"
    notif_type = 'warning'
else:
    notif_title = "Batch Approval: Nothing Approved"
    notif_type = 'danger'

action = {
    'type': 'ir.actions.client',
    'tag': 'display_notification',
    'params': {
        'title': notif_title,
        'message': "\n".join(lines),
        'type': notif_type,
        'sticky': True,  # sticky so you can actually read multi-line output
    }
}

# Powered By HSx Tech - Ali Muzafar (Odoo 18 fix)