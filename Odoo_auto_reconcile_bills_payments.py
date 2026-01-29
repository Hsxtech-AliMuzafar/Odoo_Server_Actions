# Server Action: Auto Reconcile Bills with Payments
# Model: Journal Entry (account.move)
# Action To Do: Execute Python Code

# Usage:
# Select Vendor Bills in the list view (Account > Vendors > Bills) and run this action.
# The script will look for outstanding payments (credits) for the same partner.
# It prioritizes matches in this order:
# 1. Exact Amount Match AND Memo/Ref Match (Highest Priority)
# 2. Exact Amount Match (Secondary Priority)

def get_outstanding_credits(partner_id, account_id):
    """
    Fetch outstanding credit lines for the partner and account.
    Returns a recordset of account.move.line.
    """
    domain = [
        ('parent_state', '=', 'posted'),
        ('account_id', '=', account_id),
        ('partner_id', '=', partner_id),
        ('reconciled', '=', False),
        ('balance', '<', 0),  # credit > debit (negative balance for payable)
        ('amount_residual', '!=', 0),
    ]
    # Search for lines (credit side, usually payments or refunds)
    lines = env['account.move.line'].search(domain)
    return lines

def is_memo_match(bill, credit_line):
    """
    Check if the Payment Ref/Memo matches the Bill Ref/Name.
    Case insensitive containment check.
    """
    bill_ref = (bill.ref or '').strip().lower()
    bill_name = (bill.name or '').strip().lower()
    
    # Credit line often has 'name' or related payment 'ref'
    # We check the move line name (e.g. "INV/2023/001") or the move's ref
    credit_ref = (credit_line.ref or '').strip().lower()
    credit_name = (credit_line.name or '').strip().lower()
    credit_move_name = (credit_line.move_id.name or '').strip().lower()
    
    # Gather all potential identifiers from the credit line side
    credit_identifiers = [credit_ref, credit_name, credit_move_name]
    
    # Search for Bill Ref in Credit Identifiers
    if bill_ref:
        for ident in credit_identifiers:
            if bill_ref in ident:
                return True
                
    # Search for Bill Name (__name__ is the sequence like INV/2023/001) in Credit Identifiers
    if bill_name:
         for ident in credit_identifiers:
            if bill_name in ident:
                return True
                
    return False

# Iterate over selected records (Bills)
# Ensure we only process open Bills (posted, not paid)
bills_to_process = records.filtered(lambda r: r.move_type == 'in_invoice' and r.state == 'posted' and r.payment_state != 'paid')

reconciled_count = 0

for bill in bills_to_process:
    # 1. Get Outstanding Credits (Payments)
    # Use the bill's payable account (usually on the partner or set on the line)
    # Getting the payable line from the bill to know the account
    payable_line = bill.line_ids.filtered(lambda l: l.account_id.account_type == 'liability_payable' and l.balance < 0)
    
    if not payable_line:
        # Fallback or weird state, maybe not a standard bill
        continue
        
    # There could be multiple payable lines, but usually one main one. 
    # Validating against the partner and account of the bill.
    account_id = payable_line[0].account_id.id
    partner_id = bill.partner_id.id
    
    outstanding_credits = get_outstanding_credits(partner_id, account_id)
    
    if not outstanding_credits:
        continue

    # 2. Find Best Match
    best_match = None
    
    # Strategy 1: Exact Amount AND Memo Match
    for credit in outstanding_credits:
        # amount_residual is positive for the remaining amount to reconcile
        # credit line balance is negative. amount_residual_currency or amount_residual depends on currency.
        # We compare absolute values of residual.
        
        # Note: amount_residual on credit line is usually negative if it's a credit (liability)? 
        # Actually in Odoo 14+ amount_residual is the amount left to pay/receive. 
        # For a Payment (credit side on payable), amount_residual is negative.
        # For a Bill (credit side on payable for the invoice amount), wait...
        # Bill: Credit Payables (Balance < 0). 
        # Payment: Debit Payables (Balance > 0) to offset the Bill.
        
        # WAIT. A Vendor Bill (in_invoice) creates a CREDIT on Payable Account.
        # A Vendor Payment (outbound) creates a DEBIT on Payable Account.
        
        # So we need to look for outstanding DEBITS (Payments) to match the Bill (Credit).
        # My helper function `get_outstanding_credits` searched for `balance < 0`. 
        # That would be credits (like Refunds).
        # Vendor Payments are DEBITS on the payable account.
        
        # Correction: 
        # Vendor Bill -> CREDIT on Payable.
        # Payment -> DEBIT on Payable.
        # So we look for lines with `balance > 0` (Debits) on the payable account.
        
        # However, `outstanding_credits` implies we are looking for available money.
        # Let's fix the search domain logic.
    
        pass # Placeholder for thought correction

    # REDO Search Domain Logic inline correctly:
    # Vendor Bill (in_invoice) has a Payable Line with Negative Balance (Credit).
    # We want to match it with a Payment (Debit) on the Payable Account.
    # The Payment line will have Positive Balance (Debit) and Reconciled=False.
    
    # What if it's a Vendor Refund? (in_refund). It has a Debit on Payable.
    # We match it with a Bill? No, we reconcile Bill with Refund.
    # User said "Reconcile payments with bills listed in outstanding credits".
    # In Odoo UI these are called "Outstanding Debits" if it's a Vendor Bill we are looking at? 
    # Or "Outstanding Credits" if we are looking at a Customer Invoice?
    
    # Actually, Odoo's widget usually shows "Outstanding Debits" for Vendor Bills.
    # Because you "have a debt" (Bill), and you apply a "Debit" (Payment) to reduce it.
    
    # Let's assume standard Vendor Bill Reconcile flow.
    # We look for lines with `debit > 0` (or balance > 0) on the same account.
    
    potential_matches = []
    
    # Re-fetching with correct domain
    domain = [
        ('parent_state', '=', 'posted'),
        ('account_id', '=', account_id),
        ('partner_id', '=', partner_id),
        ('reconciled', '=', False),
        ('balance', '>', 0), # Debits (Payments)
        ('move_id.move_type', '!=', 'in_invoice'), # Don't match other bills (though they are credits usually)
    ]
    available_lines = env['account.move.line'].search(domain)
    
    # Filter for candidates
    # We need to match the Bill's residual amount
    bill_residual = abs(bill.amount_residual)
    
    candidates = []
    for line in available_lines:
        line_residual = abs(line.amount_residual)
        
        if float_compare(line_residual, bill_residual, precision_digits=2) == 0:
            candidates.append(line)
            
    if not candidates:
        continue
        
    # We have candidates with MATCHING AMOUNT.
    # Now check for Memo/Ref Match (Priority 1)
    
    match_found = None
    
    # Priority 1: Check Memo
    for cand in candidates:
        if is_memo_match(bill, cand):
            match_found = cand
            break
            
    # Priority 2: If no memo match, pick the first amount match
    if not match_found and candidates:
        match_found = candidates[0]
        
    if match_found:
        # Perform Reconciliation
        # Only assign the single matching line
        try:
            bill.js_assign_outstanding_line(match_found.id)
            reconciled_count += 1
        except Exception as e:
            # Prevent blocking other bills if one fails
            log("Error reconciling Bill %s: %s" % (bill.name, str(e)))
            
# Optional: Raise a notification summary
action = {
    'type': 'ir.actions.client',
    'tag': 'display_notification',
    'params': {
        'title': 'Reconciliation Complete',
        'message': f'Reconciled {reconciled_count} bills successfully.',
        'sticky': False,
    }
}
