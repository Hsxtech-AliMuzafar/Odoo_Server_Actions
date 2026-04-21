# Odoo Server Action: Batch Inventory Adjustment
# Model: Product Template (product.template) or Product Variant (product.product)
# Action To Do: Execute Python Code
#
# Usage:
# Select products in the list view (Inventory > Products)
# and run this action from the Action menu.
# It sets the inventoried quantity to a target value (default 0) in batches.

# Configuration
TARGET_QTY = 1.0  # Set this to the desired quantity
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

# Find a default internal location (WH/Stock) for products with no existing stock records
default_location = env['stock.warehouse'].search([('company_id', '=', env.company.id)], limit=1).lot_stock_id
if not default_location:
    default_location = env['stock.location'].search([('usage', '=', 'internal')], limit=1)

if not default_location:
    raise UserError("No Internal Location found. Please ensure a Warehouse is configured.")

# Process in chunks
for i in range(0, total_products, BATCH_SIZE):
    batch_products = products[i:i + BATCH_SIZE]
    
    # Use inventory_mode context mandated by Odoo 15-18 for programmatic adjustments
    Quant = env['stock.quant'].with_context(inventory_mode=True)
    
    # 1. Update Existing Quants
    existing_quants = Quant.search([
        ('product_id', 'in', batch_products.ids),
        ('location_id.usage', '=', 'internal')
    ])
    
    if existing_quants:
        existing_quants.write({'inventory_quantity': TARGET_QTY})
        existing_quants.action_apply_inventory()
        quants_adjusted += len(existing_quants)
    
    # 2. Handle Products with 0 existing stock (no quants)
    products_with_stock = existing_quants.mapped('product_id')
    missing_products = batch_products - products_with_stock
    
    if missing_products:
        for product in missing_products:
            new_quant = Quant.create({
                'product_id': product.id,
                'location_id': default_location.id,
                'inventory_quantity': TARGET_QTY,
            })
            new_quant.action_apply_inventory()
            quants_adjusted += 1
    
    processed_count += len(batch_products)
    
    # Force DB write and commit
    env.flush_all()
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
