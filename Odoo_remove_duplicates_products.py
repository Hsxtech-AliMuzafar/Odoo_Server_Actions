# Remove Duplicate Products from BOM Lines
# Part of Odoo BOM Cleanup Tools - Powered by Hsx TECH

# ── Configuration ────────────────────────────────────────────────────────────
BATCH_SIZE = 50
# ─────────────────────────────────────────────────────────────────────────────

# Detect selection context (Model and IDs)
active_model = env.context.get('active_model')
active_ids = env.context.get('active_ids', [])

if not active_ids:
    # If no active_ids, try 'record' or 'records' which are sometimes injected
    if 'record' in locals():
        active_ids = [record.id]
        active_model = record._name
    elif 'records' in locals():
        active_ids = records.ids
        active_model = records._name

if not active_ids:
    action = {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
            'title': 'No Records Selected',
            'message': 'Please select at least one record to process.',
            'type': 'warning',
            'sticky': False,
        }
    }
else:
    # Resolve to BOM records
    if active_model == 'mrp.bom':
        boms = env['mrp.bom'].browse(active_ids)
    elif active_model == 'mrp.bom.line':
        lines = env['mrp.bom.line'].browse(active_ids)
        boms = lines.mapped('bom_id')
    else:
        # Default to mrp.bom if model is unknown
        boms = env['mrp.bom'].browse(active_ids)

    total_boms = len(boms)
    duplicate_count = 0
    unique_bom_ids = set()

    for i in range(0, total_boms, BATCH_SIZE):
        batch = boms[i:i + BATCH_SIZE]
        
        for bom in batch:
            seen = set()
            duplicates = []
            # We use sorted line IDs to ensure consistent 'first occurrence' preservation
            for line in bom.bom_line_ids:
                pid = line.product_id.id
                if pid in seen:
                    duplicates.append(line.id)
                else:
                    seen.add(pid)
            
            if duplicates:
                duplicate_count += len(duplicates)
                unique_bom_ids.add(bom.id)
                # (3, ID) deletes the O2M record
                bom.write({'bom_line_ids': [(3, d) for d in duplicates]})
                
        # Commit to save progress and release locks
        env.cr.commit()
        
        # Real-time progress bus notification
        progress = min(i + BATCH_SIZE, total_boms)
        env['bus.bus']._sendone(env.user.partner_id, 'simple_notification', {
            'title': 'Duplicate Removal Progress',
            'message': f'Processed {progress}/{total_boms} BOM(s)...',
            'type': 'info',
            'sticky': False
        })

    message = f'Removed {duplicate_count} duplicate lines from {total_boms} processed BOM(s).'

    if unique_bom_ids:
        # Create a single summary activity for the user containing the grand total
        type_todo = env.ref('mail.mail_activity_data_todo', raise_if_not_found=False) or env['mail.activity.type'].search([], limit=1)
        res_partner_model = env['ir.model'].search([('model', '=', 'res.partner')], limit=1)
        
        note_html = "<p><b>Batch Duplicate BOM Lines Removal Report</b></p>"
        note_html += "<ul>"
        note_html += f"<li>Total BOMs Processed: <b>{total_boms}</b></li>"
        note_html += f"<li>BOMs Modified: <b>{len(unique_bom_ids)}</b></li>"
        note_html += f"<li>Total Duplicate Lines Removed: <b>{duplicate_count}</b></li>"
        note_html += "</ul>"
        note_html += "<p><i>Processed via HSx Tech BOM Cleanup Tools.</i></p>"
        
        env['mail.activity'].create({
            'res_id': env.user.partner_id.id,
            'res_model_id': res_partner_model.id,
            'activity_type_id': type_todo.id,
            'summary': f'Batch Duplicate Removal: {duplicate_count} lines removed',
            'note': note_html,
            'user_id': env.user.id,
        })
        
        message += "\n\nA summary Activity has been created for your user."

    action = {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
            'title': 'Duplicates Batch Removed',
            'message': message,
            'type': 'success',
            'sticky': True,
        }
    }

## Optimized for Batch Processing
## Real-time Notifications & Activity Summary
## Powered By HSx Tech
## Ali 
