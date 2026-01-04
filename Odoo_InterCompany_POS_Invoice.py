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

for order in to_process:
    # 1. Validation Criteria
    if not order.account_move:
        continue
    
    if order.company_id.id == TARGET_COMPANY_ID:
        continue

    # 2. Get Data for New Invoice
    source_company = order.company_id
    customer_partner = source_company.partner_id 
    
    target_company = env['res.company'].sudo().browse(TARGET_COMPANY_ID)
    
    if not target_company.exists():
        raise UserWarning(f"Target Company ID {TARGET_COMPANY_ID} not found!")

    # 3. Prepare Invoice Lines
    invoice_lines = []
    for line in order.lines:
        product = line.product_id
        qty = line.qty
        
        # --- NEW LOGIC: Price Halving for Goods ---
        # Compatibility: Odoo 15+ use 'detailed_type', older versions use 'type'
        p_type = product.detailed_type if 'detailed_type' in product else product.type
        
        # If product type is 'product' (Storable Product), halve the price.
        if p_type == 'product':
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

    try:
        new_invoice = env['account.move'].sudo().with_company(target_company).create(move_vals)
        
        msg = f"Inter-Company: Created Draft Invoice {new_invoice.name} (ID: {new_invoice.id}) in Company {target_company.name}."
        order.message_post(body=msg)
        
        # Notify Success
        send_notification(env, env.user, "Inter-Company Invoice", msg, 'success')
        
        # Fallback Action
        action = {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {'title': 'Invoice Created', 'message': msg, 'type': 'success', 'sticky': False}}
        
    except Exception as e:
        error_msg = f"Inter-Company Error: Failed to create invoice in Company {TARGET_COMPANY_ID}. Reason: {str(e)}"
        order.message_post(body=error_msg)
        
        # Notify Failure
        send_notification(env, env.user, "Inter-Company Failed", error_msg, 'warning', sticky=True)
        action = {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {'title': 'Invoice Failed', 'message': error_msg, 'type': 'warning', 'sticky': True}}
