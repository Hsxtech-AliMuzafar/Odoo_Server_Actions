# Odoo Server Action: Advanced BOM Product Replacer
# Model: Bill of Materials (mrp.bom), BOM Line (mrp.bom.line), Product (product.template) OR Product Variant (product.product)
# Action To Do: Execute Python Code
#
# Usage:
# 1. Select records in any of the supported list views.
# 2. Update REPLACEMENT_MAP below with {OLD_ID: NEW_ID} pairs.
# 3. Run this action from the Action menu.

# ── Configuration ────────────────────────────────────────────────────────────

# Replace internal IDs with your own database IDs.
# Format: {OLD_ID: NEW_ID, ...}
REPLACEMENT_MAP = {
    # 0: 0, 
}

# Number of records to process per database transaction
BATCH_SIZE = 100

# ── End Configuration ─────────────────────────────────────────────────────────

if not REPLACEMENT_MAP:
    raise UserError("Please configure REPLACEMENT_MAP in the script.")

# Helper to resolve IDs (Template or Variant) to Variant Records
def resolve_products(input_ids):
    return env['product.product'].with_context(active_test=False).search([
        '|', ('id', 'in', list(input_ids)), ('product_tmpl_id', 'in', list(input_ids))
    ])

# Resolve all products involved in the mappings
all_v = resolve_products(set(REPLACEMENT_MAP.keys()) | set(REPLACEMENT_MAP.values()))

# Create a mapping of [Old Variant ID] -> [New Variant Record]
final_mapping = {}
for old_id, new_id in REPLACEMENT_MAP.items():
    match_old = all_v.filtered(lambda p: p.id == old_id or p.product_tmpl_id.id == old_id)
    match_new = all_v.filtered(lambda p: p.id == new_id or p.product_tmpl_id.id == new_id)
    
    if not match_new:
        raise UserError(f"Target Product ID {new_id} not found as a Variant or Template.")
    
    target_new = match_new[0]
    for ov in match_old:
        final_mapping[ov.id] = target_new

if not final_mapping:
    raise UserError("Could not resolve any IDs from REPLACEMENT_MAP to valid products.")

# Detect selection context (Model and IDs)
active_model = env.context.get('active_model')
active_ids = env.context.get('active_ids', [])

if not active_ids:
    raise UserError("Please select at least one record to update.")

# Build search domain for BOM lines
line_domain = []

if active_model == 'mrp.bom':
    line_domain = [('bom_id', 'in', active_ids), ('product_id', 'in', list(final_mapping.keys()))]
elif active_model == 'mrp.bom.line':
    line_domain = [('id', 'in', active_ids), ('product_id', 'in', list(final_mapping.keys()))]
elif active_model in ['product.product', 'product.template']:
    selected_variants = resolve_products(active_ids)
    target_variant_ids = [v.id for v in selected_variants if v.id in final_mapping]
    if not target_variant_ids:
        raise UserError("None of the selected products/variants are in your REPLACEMENT_MAP.")
    line_domain = [('product_id', 'in', target_variant_ids)]
else:
    line_domain = [('id', 'in', active_ids), ('product_id', 'in', list(final_mapping.keys()))]

# Search for relevant lines
to_update_lines = env['mrp.bom.line'].with_context(active_test=False).search(line_domain)

total_lines = len(to_update_lines)
if total_lines == 0:
    action = {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
            'title': 'No Matching Lines Found',
            'message': f"The selection does not contain any matching products in the BOM lines.",
            'type': 'warning',
            'sticky': True,
        }
    }
else:
    log(f"Starting advanced replacement on {active_model} for {total_lines} lines...", level='info')

    updated_count = 0
    # Grouping to track which BOMs were updated for which replacement
    # Format: {(old_v_id, new_v_id): set(bom_names)}
    group_report = {}

    for i in range(0, total_lines, BATCH_SIZE):
        batch = to_update_lines[i:i + BATCH_SIZE]
        groups = {}
        for line in batch:
            old_p_id = line.product_id.id
            new_p = final_mapping.get(old_p_id)
            if new_p:
                # Track for reporting
                pair = (old_p_id, new_p.id)
                if pair not in group_report:
                    group_report[pair] = set()
                
                # Store the Parent BOM ID for reporting
                group_report[pair].add(line.bom_id.id)

                # Batch write grouping
                if new_p.id not in groups:
                    groups[new_p.id] = {'record': new_p, 'ids': []}
                groups[new_p.id]['ids'].append(line.id)

        for p_id, info in groups.items():
            env['mrp.bom.line'].browse(info['ids']).write({
                'product_id': p_id,
                'product_uom_id': info['record'].uom_id.id
            })
            updated_count += len(info['ids'])

        env.cr.commit()

        # Real-time progress progress via bus
        progress = min(i + BATCH_SIZE, total_lines)
        env['bus.bus']._sendone(env.user.partner_id, 'simple_notification', {
            'title': 'Replacement Progress',
            'message': f'Processed {progress}/{total_lines} lines...',
            'type': 'info',
            'sticky': False,
        })

    # Prepare Detailed Grouped Summary and Activity Note
    summary_parts = [f"Successfully updated {updated_count} line(s).\n"]
    note_html_parts = [f"<p>Successfully updated <b>{updated_count}</b> line(s).</p>"]
    
    unique_boms_all = set()

    for (old_id, new_id), b_ids in group_report.items():
        old_prod = env['product.product'].browse(old_id)
        new_prod = env['product.product'].browse(new_id)
        unique_boms_all.update(b_ids)
        
        # Resolve BOM names for this group
        boms_in_group = env['mrp.bom'].browse(list(b_ids))
        # Use our variant-aware naming logic
        bom_names_in_group = []
        for b in boms_in_group:
            bom_names_in_group.append(b.product_id.display_name if b.product_id else b.product_tmpl_id.display_name)
        
        bom_names_in_group = sorted(list(set(bom_names_in_group)))
        
        # Build text summary
        summary_parts.append(f"{old_prod.display_name} ➔ {new_prod.display_name}")
        summary_parts.extend([f"  • {n}" for n in bom_names_in_group[:5]])
        if len(bom_names_in_group) > 5:
            summary_parts.append(f"  ... and {len(bom_names_in_group)-5} more")
        summary_parts.append("") # Blank line
        
        # Build HTML activity note
        bom_list_html = "".join([f"<li>{n}</li>" for n in bom_names_in_group])
        note_html_parts.append(
            f"<h4>{old_prod.display_name} ➔ {new_prod.display_name}</h4>"
            f"<ul>{bom_list_html}</ul>"
        )

    summary = "\n".join(summary_parts)
    note_html = "".join(note_html_parts) + f"<p><i>Processed via HST Advanced BOM Replacer on {active_model}.</i></p>"

    # Activity Creation
    if unique_boms_all:
        type_todo = env.ref('mail.mail_activity_data_todo', raise_if_not_found=False) or env['mail.activity.type'].search([], limit=1)
        mrp_bom_model = env['ir.model'].search([('model', '=', 'mrp.bom')], limit=1)
        
        # Attach activity to the first found BOM ID in the entire process
        first_bom_id = list(unique_boms_all)[0]
        target_bom = env['mrp.bom'].browse(first_bom_id)
        
        if target_bom:
            env['mail.activity'].create({
                'res_id': target_bom.id,
                'res_model_id': mrp_bom_model.id,
                'activity_type_id': type_todo.id,
                'summary': 'BOM Product Replacement Grouped Summary',
                'note': note_html,
                'user_id': env.user.id,
            })
            summary += "\n\nAn Activity has been created with the full grouped report."
    
    log(summary, level='info')

    action = { 'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {
        'title': 'Replacement Complete', 'message': summary, 'type': 'success', 'sticky': True,
    }}

## Model Context Support (BOM/Lines/Product/Variants)
## Automatic Template-to-Variant Resolution
## Grouped Multi-Product Reporting Summary
## Real-time Bus Progress & User Activities
## Powered By HSx Tech - Ali Muzafar
