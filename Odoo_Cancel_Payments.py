BATCH_SIZE = 500
# Process all selected records
eligible_payments = records
success_count = 0
failed_messages = []

# Process in chunks of 500
for i in range(0, len(eligible_payments), BATCH_SIZE):
    batch = eligible_payments[i:i + BATCH_SIZE]
    try:
        batch.action_cancel()
        success_count += len(batch)
    except Exception:
        for payment in batch:
            try:
                payment.action_cancel()
                success_count += 1
            except Exception as e:
                failed_messages.append(f"{payment.name or payment.id}: {str(e)}")

# Build notification message
message = f"Selected: {len(records)}\n✅ Cancelled: {success_count}"
if failed_messages:
    message += f"\n❌ Failed: {len(failed_messages)}"
    detailed_errors = ', '.join(failed_messages[:3])
    message += f"\nDetails: {detailed_errors}"

action = {
    'type': 'ir.actions.client',
    'tag': 'display_notification',
    'params': {
        'title': 'Cancel Results',
        'message': message,
        'type': 'success' if not failed_messages else 'warning',
        'sticky': bool(failed_messages)
    }
}
## Powered By HSx Tech
## Ali Muzafar
