# Odoo Server Action
# Target Model: product.pricelist OR product.pricelist.item
# Description: Checks product-level rules in pricelist, and automatically adds 
#              corresponding variant-level rules for each product variant.

added_count = 0

if model._name == 'product.pricelist':
    for pricelist in records:
        # Find rules applied on 'Product'
        items_to_process = []
        for i in pricelist.item_ids:
            if i.applied_on == '1_product' and i.product_tmpl_id:
                items_to_process.append(i)
                
        for item in items_to_process:
            for variant in item.product_tmpl_id.product_variant_ids:
                # Check if a similar rule already exists for this variant
                existing = False
                for rule in pricelist.item_ids:
                    if rule.applied_on == '0_product_variant' and \
                       rule.product_id == variant and \
                       rule.min_quantity == item.min_quantity and \
                       rule.date_start == item.date_start and \
                       rule.date_end == item.date_end:
                        existing = True
                        break
                
                if not existing:
                    # Copy the rule and apply it to the specific variant
                    item.copy({
                        'applied_on': '0_product_variant',
                        'product_id': variant.id,
                        'product_tmpl_id': item.product_tmpl_id.id,
                    })
                    added_count += 1
            
elif model._name == 'product.pricelist.item':
    # Process selected rules directly
    items_to_process = []
    for i in records:
        if i.applied_on == '1_product' and i.product_tmpl_id:
            items_to_process.append(i)
            
    for item in items_to_process:
        pricelist = item.pricelist_id
        for variant in item.product_tmpl_id.product_variant_ids:
            existing = False
            for rule in pricelist.item_ids:
                if rule.applied_on == '0_product_variant' and \
                   rule.product_id == variant and \
                   rule.min_quantity == item.min_quantity and \
                   rule.date_start == item.date_start and \
                   rule.date_end == item.date_end:
                    existing = True
                    break
            
            if not existing:
                item.copy({
                    'applied_on': '0_product_variant',
                    'product_id': variant.id,
                    'product_tmpl_id': item.product_tmpl_id.id,
                })
                added_count += 1

if added_count > 0:
    action = {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
            'title': 'Success',
            'message': f'Successfully added {added_count} variant-specific rules.',
            'type': 'success',
            'sticky': False,
        }
    }
else:
    action = {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
            'title': 'No Actions Taken',
            'message': 'No new variant-specific rules were added. They may already exist or no product-level rules were found.',
            'type': 'info',
            'sticky': False,
        }
    }
