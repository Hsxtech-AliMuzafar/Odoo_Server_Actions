# Server Action (Python Code) for res.partner
# Updates property_account_receivable_id and property_account_payable_id
# in batches of 1000 records to avoid performance issues.

# Get account references using External IDs
# Customers (POS)
receivable = env.ref("account.12_a4001")
# Fournisseurs
payable = env.ref("account.12_a440")

# Safety check
if not receivable or not payable:
    raise UserError("Receivable or Payable account not found. Please check external IDs.")

# Search all partners that need update
partners = env['res.partner'].search([])  # <-- adjust domain if needed
total = len(partners)

batch_size = 1000
for i in range(0, total, batch_size):
    batch = partners[i:i+batch_size]
    batch.write({
        'property_account_receivable_id': receivable.id,
        'property_account_payable_id': payable.id,
    })

# Optional log message
action = {
    'type': 'ir.actions.client',
    'tag': 'display_notification',
    'params': {
        'title': 'Batch Update Complete',
        'message': f'Updated {total} partners successfully.',
        'sticky': False,
    }
}
