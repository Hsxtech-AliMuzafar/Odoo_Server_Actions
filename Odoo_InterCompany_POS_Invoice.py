# Odoo Server Action: Inter-Company POS Invoice
# Model: Point of Sale Order (pos.order)
# Trigger: On Update (check for 'account_move' being set) or Manual
# Target Company ID: 12

# --- Context Recovery ---
to_process = env['pos.order']
if env.context.get('active_ids'):
    to_process |= env['pos.order'].browse(env.context.get('active_ids'))
elif env.context.get('active_id'):
    to_process |= env['pos.order'].browse(env.context.get('active_id'))
elif 'record' in globals() and record:
    to_process |= record

if not to_process:
    pass

# --- Configuration ---
TARGET_COMPANY_ID = 12

for order in to_process:
    # 1. Validation Criteria
    # - Must be invoiced (have an account_move)
    # - Must NOT be in the target company already (prevent loops)
    if not order.account_move:
        # Not invoiced yet, skip
        continue
    
    if order.company_id.id == TARGET_COMPANY_ID:
        # Already in target company, skip
        continue

    # 2. Get Data for New Invoice
    source_company = order.company_id
    customer_partner = source_company.partner_id # The company itself is the customer
    
    # Ensure we can access Target Company
    # Using sudo() to bypass record rules when switching companies
    target_company = env['res.company'].sudo().browse(TARGET_COMPANY_ID)
    
    if not target_company.exists():
        raise UserWarning(f"Target Company ID {TARGET_COMPANY_ID} not found!")

    # 3. Prepare Invoice Lines
    invoice_lines = []
    for line in order.lines:
        # We use the same product. 
        # Note: Product must be available in Target Company (shared or duplicated).
        product = line.product_id
        qty = line.qty
        price_unit = line.price_unit 
        
        # We need to compute taxes for the TARGET company.
        # If we copy tax_ids directly, they might belong to Source Company and fail.
        # We'll use the product's default taxes in the target company context.
        # However, for simplicity in Inter-Company, often we assume 1-1 mapping or no tax.
        # Let's try to get taxes for the Target Company.
        taxes = product.with_company(target_company).taxes_id.filtered(lambda t: t.company_id.id == TARGET_COMPANY_ID)
        
        line_vals = {
            'product_id': product.id,
            'quantity': qty,
            'price_unit': price_unit,
            'name': line.full_product_name or product.name,
            'tax_ids': [(6, 0, taxes.ids)],
        }
        invoice_lines.append((0, 0, line_vals))

    # 4. Create Invoice in Target Company
    # We use with_company(target_company) and sudo() to ensure creation validity.
    move_vals = {
        'move_type': 'out_invoice', # Customer Invoice
        'partner_id': customer_partner.id,
        'company_id': TARGET_COMPANY_ID,
        'invoice_line_ids': invoice_lines,
        'ref': f"Re-bill POS Order: {order.name}",
        'date': order.date_order.date(),
        'journal_id': env['account.journal'].with_company(target_company).search([('type', '=', 'sale'), ('company_id', '=', TARGET_COMPANY_ID)], limit=1).id
    }

    try:
        new_invoice = env['account.move'].sudo().with_company(target_company).create(move_vals)
        
        # Log success on source order
        order.message_post(body=f"Inter-Company: Created Draft Invoice {new_invoice.name} (ID: {new_invoice.id}) in Company {target_company.name}.")
        
    except Exception as e:
        order.message_post(body=f"Inter-Company Error: Failed to create invoice in Company {TARGET_COMPANY_ID}. Reason: {str(e)}")
