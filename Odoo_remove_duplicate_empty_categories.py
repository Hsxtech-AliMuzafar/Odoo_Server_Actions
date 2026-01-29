# Odoo Server Action: Remove Empty Product Categories
# Model: Product Category (product.category)
# Powered by Hsx TECH - Ali Muzafar

# This script removes ALL categories that have no products
# and no subcategories with products.

Category = env['product.category']
Product = env['product.template']

# 1. Identify "Needed" Categories (those with products or variants)
log("Gathering used categories...", level='info')
all_used_cat_ids = set()

# Get directly used categories from product.template
# Using SQL for speed on large datasets
env.cr.execute("SELECT DISTINCT categ_id FROM product_template WHERE categ_id IS NOT NULL")
all_used_cat_ids.update(r[0] for r in env.cr.fetchall())

# Expand to all parents recursively to keep the hierarchy intact
log("Calculating hierarchy protection...", level='info')
to_check = list(all_used_cat_ids)
needed_ids = set(to_check)
while to_check:
    # Process in batches to avoid OOM or expression depth issues
    current_batch = to_check[:1000]
    to_check = to_check[1000:]
    parents = env['product.category'].browse(current_batch).mapped('parent_id').ids
    new_parents = [p for p in parents if p and p not in needed_ids]
    needed_ids.update(new_parents)
    to_check.extend(new_parents)

# 2. Identify categories to delete
to_delete_ids = env['product.category'].search([('id', 'not in', list(needed_ids))]).ids
total_to_delete = len(to_delete_ids)
log(f"Found {total_to_delete} empty categories to remove.", level='info')

removed_count = 0
error_count = 0

# 3. Safe Deletion inside Savepoints
# Sort descending by ID to handle children before parents
to_delete_ids.sort(reverse=True)

BATCH_SIZE = 500
for i in range(0, total_to_delete, BATCH_SIZE):
    batch_ids = to_delete_ids[i:i + BATCH_SIZE]
    for cat_id in batch_ids:
        cat = env['product.category'].browse(cat_id)
        if not cat.exists():
            continue
            
        # Avoid 'with' as it's often restricted (forbidden opcodes)
        # Use manual savepoints via SQL to protect the transaction
        try:
            env.cr.execute('SAVEPOINT cleanup_sp')
            cat.unlink()
            env.cr.execute('RELEASE SAVEPOINT cleanup_sp')
            removed_count += 1
        except Exception:
            # If unlink fails, rollback to savepoint to keep transaction alive
            env.cr.execute('ROLLBACK TO SAVEPOINT cleanup_sp')
            error_count += 1
            continue
            
    # Regular commit to save progress and release locks
    env.cr.commit()
    log(f"Cleaned {i + len(batch_ids)}/{total_to_delete}...", level='info')

# Final Notification
msg = f"Success: Removed {removed_count} empty categories. ({error_count} skipped due to system constraints)."
log(msg, level='info')

# Prepare return notification
action = {
    'type': 'ir.actions.client',
    'tag': 'display_notification',
    'params': {
        'title': 'Empty Category Cleanup Complete',
        'message': f'Removed {removed_count} categories that had no products.',
        'type': 'success',
        'sticky': False,
    }
}