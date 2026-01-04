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

# --- Helper: Send Notification ---
def send_notification(env, user, title, message, type='success', sticky=False):
    try:
        env['bus.bus']._sendone(
            user.partner_id,
            'simple_notification',
            {
                'type': type,
                'title': title,
                'message': message,
                'sticky': sticky,
                'warning': type == 'warning',
            }
        )
    except Exception:
        pass

# --- Configuration ---
TARGET_COMPANY_ID = 12

# Statistics
stats = {
    'created': 0,
    'skipped': 0,
    'errors': 0,
    'companies': set()
}

if not to_process:
    pass

for order in to_process:
    # 1. Validation Criteria
    if not order.account_move:
        stats['skipped'] += 1
        continue
    
    if order.company_id.id == TARGET_COMPANY_ID:
        stats['skipped'] += 1
        continue

    # 2. Check overlap logic (Optional: Check if already billed to target?)
    # For now, we rely on the user or previous logic. 
    # If we want to prevent duplicates, we might check 'ref' on target company.
    # ref = f"Re-bill POS Order: {order.name}"
    
    source_company = order.company_id
    customer_partner = source_company.partner_id 
    
    target_company = env['res.company'].sudo().browse(TARGET_COMPANY_ID)
    
    if not target_company.exists():
        # Critical failure
        order.message_post(body=f"Inter-Company Error: Target Company {TARGET_COMPANY_ID} not found.")
        stats['errors'] += 1
        continue

    # 3. Prepare Invoice Lines
    invoice_lines = []
    try:
        for line in order.lines:
            product = line.product_id
            qty = line.qty
            
            # --- Price Halving Logic ---
            # Compatibility: Odoo 15+ use 'detailed_type', older versions use 'type'
            p_type = product.detailed_type if 'detailed_type' in product else product.type
            
            # Reduce price for Storable (product) AND Consumable (consu)
            if p_type in ['product', 'consu']:
                price_unit = line.price_unit / 2.0
            else:
                price_unit = line.price_unit
            
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
        move_vals = {
            'move_type': 'out_invoice', 
            'partner_id': customer_partner.id,
            'company_id': TARGET_COMPANY_ID,
            'invoice_line_ids': invoice_lines,
            'ref': f"Re-bill POS Order: {order.name}",
            'date': order.date_order.date(),
            'journal_id': env['account.journal'].with_company(target_company).search([('type', '=', 'sale'), ('company_id', '=', TARGET_COMPANY_ID)], limit=1).id
        }

        new_invoice = env['account.move'].sudo().with_company(target_company).create(move_vals)
        
        # Log success on source order
        order.message_post(body=f"Inter-Company: Created Draft Invoice {new_invoice.name} (ID: {new_invoice.id}) in Company {target_company.name}.")
        
        stats['created'] += 1
        stats['companies'].add(source_company.name)
        
    except Exception as e:
        error_msg = f"Inter-Company Error: {str(e)}"
        order.message_post(body=error_msg)
        stats['errors'] += 1

# --- Final Summary Notification ---
# Only show if something actually happened or if manually run
if len(to_process) > 0:
    company_list = ", ".join(stats['companies'])
    if not company_list:
        company_list = "None"

    title = "Inter-Company Batch Complete"
    msg = (f"Result:\n"
           f"- Invoices Created: {stats['created']}\n"
           f"- Skipped: {stats['skipped']}\n"
           f"- Errors: {stats['errors']}\n"
           f"- Source Companies: {company_list}")
    
    msg_type = 'warning' if stats['errors'] > 0 else 'success'
    
    send_notification(env, env.user, title, msg, msg_type, sticky=False)

    # Return action for manual runs
    action = {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {'title': title, 'message': msg, 'type': msg_type, 'sticky': False}}
