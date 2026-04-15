# Odoo Server Action: Batch Inventory Adjustment
# Model: Product Template (product.template) or Product Variant (product.product)
# Action To Do: Execute Python Code
#
# Usage:
# Select products in the list view (Inventory > Products)
# and run this action from the Action menu.
# It sets the inventoried quantity to a target value (default 0) in batches.

# Configuration
TARGET_QTY = 0.0  # Set this to the desired quantity
BATCH_SIZE = 50   # Number of products to process in one transaction

# Get selected IDs and Model
all_selected_ids = records.ids
active_model = records._name

if not all_selected_ids:
    raise UserError("Please select at least one Product to adjust.")

# Resolve products (handle both template and product models)
if active_model == 'product.template':
    products = env['product.product'].search([('product_tmpl_id', 'in', all_selected_ids)])
else:
    products = records

total_products = len(products)
processed_count = 0
quants_adjusted = 0

log(f"Starting Batch Inventory Adjustment for {total_products} products...", level='info')

# Process in chunks
for i in range(0, total_products, BATCH_SIZE):
    batch_products = products[i:i + BATCH_SIZE]
    
    # Find active quants for these products in internal locations
    # We only adjust 'Internal' locations to avoid affecting transit/scrap/suppliers
    quants = env['stock.quant'].search([
        ('product_id', 'in', batch_products.ids),
        ('location_id.usage', '=', 'internal')
    ])
    
    if quants:
        for quant in quants:
            # Set the counted quantity
            # Note: inventory_quantity is the Odoo 15-18 field for adjustment
            quant.inventory_quantity = TARGET_QTY
            quants_adjusted += 1
        
        # Apply the adjustment for the batch
        # This creates the stock.move and updates quantity on hand
        quants.action_apply_inventory()
    
    processed_count += len(batch_products)
    
    # Commit to save progress and release DB locks
    env.cr.commit()
    
    # Real-time progress notification
    progress = min(i + BATCH_SIZE, total_products)
    env['bus.bus']._sendone(env.user.partner_id, 'simple_notification', {
        'title': 'Inventory Adjustment Progress',
        'message': f'Processed {progress}/{total_products} products...',
        'type': 'info',
        'sticky': False
    })

# Final summary notification
action = {
    'type': 'ir.actions.client',
    'tag': 'display_notification',
    'params': {
        'title': 'Batch Adjustment Complete',
        'message': f"Successfully adjusted {quants_adjusted} stock levels for {processed_count} products.",
        'type': 'success',
        'sticky': True
    }
}

## Optimized for Odoo 15-18 Inventory Logic
## Real-time Batch Notifications via Bus
## Powered By HSx Tech - Ali Muzafar
