# Configuration
BATCH_SIZE = 1000

# Odoo often limits 'active_ids' to 20,000 for performance.
# To process 278,000, we use the 'active_domain' if it's a "Select All" operation.
active_ids = env.context.get('active_ids', [])
active_domain = env.context.get('active_domain')

if active_domain is not None:
    # Use the domain from the current view/filter to find ALL eligible moves
    # This bypasses the 20k limit completely.
    search_domain = active_domain + [('state', 'in', ('posted', 'cancel'))]
    all_eligible_ids = env['account.move'].search(search_domain).ids
else:
    # If no domain, fallback to the specific selected IDs
    all_eligible_ids = env['account.move'].search([
        ('id', 'in', active_ids),
        ('state', 'in', ('posted', 'cancel'))
    ]).ids

total_count = len(all_eligible_ids)
success_count = 0
failed_count = 0

log(f"Starting batch reset for {total_count} records...", level='info')

# Process in chunks and commit to avoid long-running transaction issues
for i in range(0, total_count, BATCH_SIZE):
    batch_ids = all_eligible_ids[i:i + BATCH_SIZE]
    
    # Re-verify eligibility within the batch to avoid race conditions
    eligible_batch = env['account.move'].browse(batch_ids).filtered(lambda m: m.state in ('posted', 'cancel'))
    
    if not eligible_batch:
        continue
        
    try:
        # Attempt to process the whole batch for speed
        eligible_batch.button_draft()
        success_count += len(eligible_batch)
    except Exception:
        # Fallback to individual processing if batch fails
        for move in eligible_batch:
            try:
                move.button_draft()
                success_count += 1
            except Exception:
                failed_count += 1
    
    # CRITICAL: Commit to free up database locks and recover memory
    env.cr.commit()
    
    # Progress logging every 5000 records
    if (i + BATCH_SIZE) % 5000 == 0 or (i + BATCH_SIZE) >= total_count:
        log(f"Reset to Draft Progress: {min(i + BATCH_SIZE, total_count)}/{total_count} processed", level='info')

# Build final notification message
message = f"✅ {success_count} entries reset to draft"
if failed_count:
    message += f"\n❌ Failed: {failed_count} entries"

action = {
    'type': 'ir.actions.client',
    'tag': 'display_notification',
    'params': {
        'title': 'Batch Reset Complete',
        'message': f"Processed {total_count} entries.\n{message}",
        'type': 'success' if failed_count == 0 else 'warning',
        'sticky': True
    }
}

## Optimized for Ultra High Volume (278k+)
## Bypasses 20k Selection Limit
## Powered By HSx Tech - Ali Muzafar


