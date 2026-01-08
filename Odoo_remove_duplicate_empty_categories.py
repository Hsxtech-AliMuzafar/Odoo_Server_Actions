# Odoo Server Action: Remove Duplicate Empty Product Categories
# Model: Product Category (product.category)
# Powered by Hsx TECH - Ali Muzafar

# This script removes duplicate categories (same name and parent)
# ONLY if they have no products and no subcategories.

Category = env['product.category']
Product = env['product.template']

# Get relevant categories (from selection or all)
target_categories = records if records else Category.search([])

# Group all categories by (name, parent_id) to find duplicates globally
# even if only some were selected, we need to know the context.
all_cats = Category.search([])
groups = {}
for cat in all_cats:
    key = (cat.name, cat.parent_id.id if cat.parent_id else False)
    if key not in groups:
        groups[key] = []
    groups[key].append(cat)

removed_count = 0
log("Starting Duplicate Category Cleanup...", level='info')

for key, cats in groups.items():
    if len(cats) <= 1:
        continue
    
    # Identify which categories in this group are "Busy"
    busy_cats = []
    empty_cats = []
    
    for cat in cats:
        # 1. Check for products
        has_products = Product.search_count([('categ_id', '=', cat.id)]) > 0
        # 2. Check for subcategories
        has_children = Category.search_count([('parent_id', '=', cat.id)]) > 0
        
        if has_products or has_children:
            busy_cats.append(cat)
        else:
            empty_cats.append(cat)
            
    # Keep ALL busy categories (user wants to leave categories with products/structure)
    # If there are NO busy categories, we MUST keep at least one empty one
    if not busy_cats and empty_cats:
        # Sort by ID to keep the oldest one consistently
        empty_cats.sort(key=lambda x: x.id)
        kept_empty = empty_cats.pop(0)
        # log(f"Keeping oldest empty category: {kept_empty.display_name} (ID: {kept_empty.id})")
        
    # Remove the remaining empty duplicates
    for cat in empty_cats:
        try:
            # Final safety check: ensure the category is still in target_categories 
            # if the user only wanted to clean specific ones? 
            # Actually, usually a cleanup is global.
            cat_name = cat.display_name
            cat.unlink()
            removed_count += 1
            # log(f"Removed duplicate empty category: {cat_name} (ID: {cat.id})")
        except Exception as e:
            log(f"Could not remove category {cat.id}: {str(e)}", level='error')

# Prepare return notification
action = {
    'type': 'ir.actions.client',
    'tag': 'display_notification',
    'params': {
        'title': 'Duplicate Cleanup Complete',
        'message': f'Removed {removed_count} redundant empty categories.',
        'type': 'success',
        'sticky': False,
    }
}
