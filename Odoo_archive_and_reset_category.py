# Archive and Reset Product Category to ID 1
# Part of Odoo Inventory Tools - Powered by Hsx TECH

# Logic for Odoo Server Action (Python Code field)
# This script archives selected products AND sets their category to ID 1 (All)

if records:
    # Target category ID 1 (typically "All")
    category_id = 1
    total_count = len(records)
    
    # Batch processing for safety (chunks of 1000)
    batch_size = 1000
    for i in range(0, total_count, batch_size):
        batch = records[i : i + batch_size]
        # Combine both operations (Archive and Category Update)
        batch.write({
            'active': False,
            'categ_id': category_id
        })

    # Return success notification
    action = {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
            'title': 'Products Reset & Archived',
            'message': f'Successfully archived and updated category for {total_count} product(s).',
            'type': 'success',
            'sticky': False,
        }
    }

## Powered By HSx Tech
## Ali Muzafar
