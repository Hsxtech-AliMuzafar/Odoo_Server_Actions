# Available variables:
#  - env: Odoo Environment on which the action is triggered
#  - model: Odoo Model of the record on which the action is triggered; is a void recordset
#  - record: record on which the action is triggered; may be void
#  - records: recordset of all records on which the action is triggered in multi-mode
#  - time, datetime, dateutil, timezone: useful Python libraries
#  - float_compare: Odoo standard float comparison function
#  - log: log(message, level='info'): logging function to record debug information in IrLogging table
#  - UserError: Warning Exception to use with raise
#  - Command: x2Many commands namespace

# Requirement: Update property_account_income_categ_id and property_account_expense_categ_id
# From the already present accounts on one Category in the selection.

# 1. Identify the Source (Template)
# We look for a category in the selected 'records' that has both accounts set.
sources = records.filtered(lambda r: r.property_account_income_categ_id and r.property_account_expense_categ_id)

if not sources:
    raise UserError("No Category with both Income and Expense accounts found in the selection to use as a template.")

# 2. Validate Uniqueness
# We must ensure all sources point to the SAME accounts, otherwise it's ambiguous.
first_source = sources[0]
ref_income = first_source.property_account_income_categ_id
ref_expense = first_source.property_account_expense_categ_id

for source in sources[1:]:
    if source.property_account_income_categ_id != ref_income or source.property_account_expense_categ_id != ref_expense:
        raise UserError("Ambiguous selection: You have selected categories with DIFFERENT existing accounts. Please select only one 'source' type or ensure all sources match.")

# 3. Update Targets
# Optimization: Filter records that actually need changes and perform a SINGLE batch write.
# This prevents N+1 queries and makes it much faster for large datasets.

# 3. Update Targets
# Optimization: Filter records that actually need changes and perform updates in BATCHES.
# This prevents timeouts and memory issues on massive datasets by committing incrementally.

records_to_update = records.filtered(lambda r: r.property_account_income_categ_id != ref_income or r.property_account_expense_categ_id != ref_expense)
total_len = len(records_to_update)
BATCH_SIZE = 1000

# Loop through records in chunks
for i in range(0, total_len, BATCH_SIZE):
    batch = records_to_update[i:i + BATCH_SIZE]
    batch.write({
        'property_account_income_categ_id': ref_income.id,
        'property_account_expense_categ_id': ref_expense.id,
    })
    # Commit after each batch to save progress and release locks
    env.cr.commit()
    log("Updated batch {}/{}".format(i + len(batch), total_len), level='info')

count = total_len

# 4. Notification
# Odoo Server Actions don't return a view action by default unless assigned to 'action' variable.
# We will show a notification.

msg = f"Success! properties updated for {count} categories based on template '{first_source.name}'."
action = {
    'type': 'ir.actions.client',
    'tag': 'display_notification',
    'params': {
        'title': 'Accounts Updated',
        'message': msg,
        'sticky': False,
        'type': 'success',
    }
}
