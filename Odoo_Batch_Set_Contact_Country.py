# Odoo Server Action: Batch Set Country on Contacts
# Model: Contact (res.partner)
# Action To Do: Execute Python Code
#
# Usage:
# Select contacts in the list view (Contacts > Contacts)
# and run this action from the Action menu.
# It sets the country (and optionally state/province) on all selected contacts.
#
# Setup:
# 1. Find the Country ID from Settings > Technical > Countries (or use search below)
# 2. Set COUNTRY_ID to the numeric database ID of the target country
# 3. Optionally set STATE_ID to the numeric database ID of a state/province (0 = skip)
# 4. Set OVERWRITE_EXISTING to True to replace already-set countries, or False to skip them

# ── Configuration ────────────────────────────────────────────────────────────

# Target country database ID  (e.g. 233 = United States, 75 = France, 108 = Pakistan)
COUNTRY_ID = 233

# Target state/province database ID — set to 0 to leave state unchanged
STATE_ID = 0

# If True  → overwrite contacts that already have a country set
# If False → only update contacts where country is currently empty
OVERWRITE_EXISTING = False

# Number of records to write per database transaction
BATCH_SIZE = 100

# ── End Configuration ─────────────────────────────────────────────────────────

# Validate the configured country
country = env['res.country'].browse(COUNTRY_ID)
if not country.exists():
    raise UserError(
        f"Country ID {COUNTRY_ID} does not exist. "
        "Please check the ID in Settings > Technical > Countries and update COUNTRY_ID."
    )

# Validate state if provided
state = None
if STATE_ID:
    state = env['res.country.state'].browse(STATE_ID)
    if not state.exists():
        raise UserError(
            f"State ID {STATE_ID} does not exist. "
            "Please check the ID and update STATE_ID, or set STATE_ID = 0 to skip."
        )
    if state.country_id.id != COUNTRY_ID:
        raise UserError(
            f"State '{state.name}' (ID {STATE_ID}) does not belong to "
            f"country '{country.name}' (ID {COUNTRY_ID}). Please fix the configuration."
        )

# Gather selected record IDs
all_selected_ids = env.context.get('active_ids', [])

if not all_selected_ids:
    raise UserError("Please select at least one Contact to update.")

# Filter based on OVERWRITE_EXISTING setting
domain = [('id', 'in', all_selected_ids)]
if not OVERWRITE_EXISTING:
    domain.append(('country_id', '=', False))

to_update_ids = env['res.partner'].search(domain).ids

skipped_count = len(all_selected_ids) - len(to_update_ids)
total_count   = len(to_update_ids)

if total_count == 0:
    already_msg = (
        f"All {len(all_selected_ids)} selected contacts already have a country set. "
        "Set OVERWRITE_EXISTING = True to overwrite them."
        if not OVERWRITE_EXISTING
        else "No matching contacts found to update."
    )
    action = {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
            'title': 'No Update Needed',
            'message': already_msg,
            'type': 'info',
            'sticky': False,
        }
    }
else:
    log(
        f"Starting batch country update → '{country.name}'"
        + (f" / '{state.name}'" if state else "")
        + f" for {total_count} contacts (skipping {skipped_count} already set)...",
        level='info'
    )

    updated_count = 0
    state_set_count = 0

    for i in range(0, total_count, BATCH_SIZE):
        batch_ids     = to_update_ids[i:i + BATCH_SIZE]
        batch_records = env['res.partner'].browse(batch_ids)

        # Always update the country on all records in the batch
        batch_records.write({'country_id': COUNTRY_ID})
        updated_count += len(batch_records)

        # Only set state on contacts that do NOT already have a state
        if state:
            no_state_records = batch_records.filtered(lambda p: not p.state_id)
            if no_state_records:
                no_state_records.write({'state_id': STATE_ID})
                state_set_count += len(no_state_records)

        # Commit to release locks and persist progress
        env.cr.commit()

        # Real-time progress notification
        progress = min(i + BATCH_SIZE, total_count)
        env['bus.bus']._sendone(env.user.partner_id, 'simple_notification', {
            'title': 'Country Update Progress',
            'message': f'Updated {progress}/{total_count} contacts...',
            'type': 'info',
            'sticky': False,
        })

    state_skipped = (updated_count - state_set_count) if state else 0
    summary = (
        f"Successfully set country to '{country.name}' on {updated_count} contact(s)."
        + (
            f" Set state '{state.name}' on {state_set_count} contact(s)"
            + (f"; skipped {state_skipped} that already had a state." if state_skipped else ".")
            if state else ""
        )
        + (f" Skipped {skipped_count} contact(s) that already had a country." if skipped_count else "")
    )

    log(summary, level='info')

    action = {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
            'title': 'Batch Country Update Complete',
            'message': summary,
            'type': 'success',
            'sticky': True,
        }
    }

## Optimized for Batch Efficiency
## Real-time Batch Notifications via Bus
## Powered By HSx Tech - Ali Muzafar
