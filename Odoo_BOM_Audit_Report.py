# Odoo Server Action: Advanced BOM Quality Audit (Duplicates & Multiple BOMs)
# 1. Flags duplicate component entries inside single BOMs.
# 2. Flags Products that have more than one active BOM.
# 3. Creates a Detailed Summary Activity for the User.
# Part of HSx TECH BOM Cleanup Tools - Powered by Ali Muzafar

# ── Configuration ────────────────────────────────────────────────────────────
BATCH_SIZE = 50
# ─────────────────────────────────────────────────────────────────────────────

# Local Registry setup
active_ids = env.context.get('active_ids', [])
records = env['mrp.bom'].browse(active_ids)

if not records:
    action = {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
            'title': 'No BOMs Selected',
            'message': 'Please select Bill of Materials to audit.',
            'type': 'warning',
            'sticky': False,
        }
    }
else:
    total_records = len(records)
    
    # Audit tracking
    # {variant_display_name: {bom_name: {component_name: count}}}
    variant_audit_map = {}
    duplicate_line_total = 0

    for i in range(0, total_records, BATCH_SIZE):
        batch = records[i:i + BATCH_SIZE]
        
        for bom in batch:
            # Resolve Finished Good Name
            fg_name = bom.product_id.display_name if bom.product_id else bom.product_tmpl_id.display_name
            
            if fg_name not in variant_audit_map:
                variant_audit_map[fg_name] = {'boms': [], 'duplicates': {}}
            
            variant_audit_map[fg_name]['boms'].append(bom.display_name)

            # Audit Part 2: Duplicate Product entries inside this specific BOM
            line_counts = {}
            for line in bom.bom_line_ids:
                p_name = line.product_id.display_name
                line_counts[p_name] = line_counts.get(p_name, 0) + 1
            
            # Filter for duplicates
            dupes = {p: c for p, c in line_counts.items() if c > 1}
            if dupes:
                variant_audit_map[fg_name]['duplicates'][bom.display_name] = dupes
                duplicate_line_total += sum(dupes.values()) - len(dupes)

        # UI Progress
        progress = min(i + BATCH_SIZE, total_records)
        env['bus.bus']._sendone(env.user.partner_id, 'simple_notification', {
            'title': 'Audit Progress', 'message': f'Audited {progress}/{total_records} BOMs...', 'type': 'info'
        })

    # ── Report Generation (Finished Good Centric) ───────────────────────────
    note_html = "<h3>BOM Quality Audit Report</h3>"
    has_issues = False

    # Issue Type A: Multiple BOMs for same Finished Good
    multi_bom_variants = {fg: data for fg, data in variant_audit_map.items() if len(data['boms']) > 1}
    if multi_bom_variants:
        has_issues = True
        note_html += "<h4>⚠️ Multiple BOMs for One Finished Good</h4><ul>"
        for fg, data in multi_bom_variants.items():
            note_html += f"<li><b>{fg}</b> has {len(data['boms'])} BoMs: <i>({', '.join(data['boms'])})</i></li>"
        note_html += "</ul>"

    # Issue Type B: Duplicate Component Entries (Grouped by Finished Good)
    fg_with_dupes = {fg: data for fg, data in variant_audit_map.items() if data['duplicates']}
    if fg_with_dupes:
        has_issues = True
        note_html += "<h4>🛑 Duplicate Component Entries (By Finished Good)</h4>"
        note_html += "<table border='1' style='width:100%; border-collapse: collapse; font-size: 11px;'>"
        note_html += "<tr style='background: #f2f2f2;'><th>Finished Good</th><th>BOM Name</th><th>Duplicate Component</th><th>Count</th></tr>"
        
        for fg, data in fg_with_dupes.items():
            fg_first = True
            fg_rowspan = sum(len(d) for d in data['duplicates'].values())
            
            for bom_name, dupes in data['duplicates'].items():
                bom_first = True
                bom_rowspan = len(dupes)
                
                for p_name, count in dupes.items():
                    note_html += "<tr>"
                    if fg_first:
                        note_html += f"<td rowspan='{fg_rowspan}' style='padding:4px; vertical-align:top;'><b>{fg}</b></td>"
                        fg_first = False
                    if bom_first:
                        note_html += f"<td rowspan='{bom_rowspan}' style='padding:4px; vertical-align:top;'>{bom_name}</td>"
                        bom_first = False
                    note_html += f"<td style='padding:4px;'>{p_name}</td><td style='padding:4px;'><b>{count}</b></td></tr>"
        note_html += "</table>"

    if has_issues:
        # Create Single Summary Activity for User
        res_partner_model = env['ir.model'].search([('model', '=', 'res.partner')], limit=1)
        type_todo = env.ref('mail.mail_activity_data_todo', raise_if_not_found=False) or env['mail.activity.type'].search([], limit=1)
        
        env['mail.activity'].create({
            'res_id': env.user.partner_id.id,
            'res_model_id': res_partner_model.id,
            'activity_type_id': type_todo.id,
            'summary': f'BOM AUDIT: Issues found in {len(multi_bom_variants) + len(fg_with_dupes)} Finished Goods',
            'note': note_html,
            'user_id': env.user.id,
        })
        
        action = {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Audit Complete - Issues Found',
                'message': f'Found {len(multi_bom_variants)} multi-BOM variants and {duplicate_line_total} duplicate lines. Check your activity!',
                'type': 'danger',
                'sticky': True
            }
        }
    else:
        action = {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Audit Clean',
                'message': 'No duplicates or multiple BOM instances found in selected records.',
                'type': 'success',
                'sticky': False
            }
        }

## Dual-Core Audit: Lines and BOM Instances
## Activity Summary Report
## Powered By HSx Tech
## Ali Muzafar 
