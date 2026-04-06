# Odoo Server Action: Archive Duplicate BoMs for Product Variants
# Model: Product Variant (product.product)
# Action To Do: Execute Python Code
#
# Usage:
# Select Product Variants in the list view (Manufacturing > Products > Product Variants)
# and run this action from the Action menu.
# It checks if a variant has multiple BoMs specifically assigned to it,
# keeps the first one (based on sequence/ID), and archives the rest.

BATCH_SIZE = 100

active_ids = env.context.get('active_ids', [])
if not active_ids and records:
    active_ids = records.ids

if not active_ids:
    raise UserError("Please select at least one Product Variant to process.")

total_variants = len(active_ids)
success_count = 0
archived_bom_count = 0
failed_count = 0

archived_variant_names = []

log(f"Starting batch duplicate BoM archival for {total_variants} selected variants...", level='info')

# Process in chunks to avoid timeouts on large selections
for i in range(0, total_variants, BATCH_SIZE):
    batch_ids = active_ids[i:i + BATCH_SIZE]
    variants = env['product.product'].browse(batch_ids)
    
    for variant in variants:
        try:
            # Find Active BoMs specifically assigned to this variant
            # (If product_id is set, it specifically belongs to this variant)
            boms = env['mrp.bom'].search([
                ('product_id', '=', variant.id),
                ('active', '=', True)
            ], order='sequence asc, id asc')
            
            if len(boms) > 1:
                # Keep the first one found (highest priority based on sequence/id)
                # Archive the duplicates
                duplicates = boms[1:]
                duplicates.write({'active': False})
                archived_bom_count += len(duplicates)
                if variant.display_name not in archived_variant_names:
                    archived_variant_names.append(variant.display_name)
                
            success_count += 1
        except Exception:
            failed_count += 1
            
    # Commit to free up database locks
    env.cr.commit()
    
    # Send a bus notification for each batch indicating progress
    progress = min(i + BATCH_SIZE, total_variants)
    try:
        env['bus.bus']._sendone(env.user.partner_id, 'simple_notification', {
            'title': 'Batch Processing',
            'message': f'Processed {progress}/{total_variants} variants (Archived {archived_bom_count} BoMs)...',
            'type': 'info',
            'sticky': False
        })
    except Exception:
        pass # Ignore failure if bus notifications are not fully set up

# Final summary bus notification
message = f"✅ Processed {success_count} variants\n"
message += f"🗑️ Archived {archived_bom_count} duplicate BoMs"

if archived_variant_names:
    # Truncate to avoid making the notification excessively long
    if len(archived_variant_names) > 10:
        names_str = ", ".join(archived_variant_names[:10]) + f" and {len(archived_variant_names) - 10} more"
    else:
        names_str = ", ".join(archived_variant_names)
    message += f"\n\nVariants Updated:\n{names_str}"

if failed_count:
    message += f"\n❌ Failed to process {failed_count} variants"

action = {
    'type': 'ir.actions.client',
    'tag': 'display_notification',
    'params': {
        'title': 'BoM Deduplication Complete',
        'message': message,
        'type': 'success' if failed_count == 0 else 'warning',
        'sticky': True
    }
}

## Optimized for Selected Records
## Real-time Batch Notifications via Bus
## Powered By HSx Tech - Ali Muzafar
