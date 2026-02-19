# Odoo_Server_Actions
Odoo Server Actions for Various Data Clean_Up and Redundant Tasks

# **Odoo BOM Cleanup Tools**  

**Automated Server Actions for Cleaning Bill of Materials (BOM) in Odoo**  

This repository contains Python scripts for Odoo server actions that help maintain clean and efficient Bill of Materials (BOM) by:  

- **Removing archived products** from BOM lines  
- **Detecting and removing duplicate products** in BOM components  
- **Combined cleanup action** for both archived and duplicate products  

## **Features**  

✔ **Easy Integration** – Works as an Odoo server action  
✔ **Studio-Compatible** – Can be implemented via Odoo Studio with minimal setup  
✔ **Multi-BOM Support** – Processes single or multiple BOMs at once  
✔ **User Notifications** – Provides clear feedback on cleanup results  
✔ **Efficient ORM Queries** – Optimized for performance  

## **Usage**  

1. **Remove Archived Products**  
   - Searches for BOM lines containing archived products and removes them.  

2. **Remove Duplicate Products**  
   - Detects multiple entries of the same product in a BOM and keeps only one.  

3. **Combined Cleanup (Archived + Duplicates)**  
   - Performs both actions in a single run for maximum efficiency.  

4. **Update Category Accounts (Income/Expense)**
   - Bulk updates `Income` and `Expense` accounts on Product Categories.
   - Uses a "Source" category from your selection as a template.
   - Processes in **incremental batches** of 1000 to handle large datasets safely.  

5. **Cancel Draft Vendor Bills**
   - Bulk cancels selected Vendor Bills that are in the `draft` state.
   - Filters selection to ensure only draft bills/refunds are processed.
   - Returns a success notification with the count of cancelled bills.

6. **Reset to Draft (Payments)**
   - Resets selected `account.payment` records to `draft` state.
   - Processes in batches for safety.

7. **Cancel Payments**
   - Cancels selected `account.payment` records.
   - Provides detailed feedback on success/failure counts.

8. **Sync POS Category**
   - Automatically finds a `pos.category` with the exact same name as the Product's `categ_id`.
   - Adds it to the Product's `pos_categ_ids`.
   - Robust context handling (works via Automation, "Run" button, or Action menu).
   - Silent logging to Chatter for audit trails.
   - **Trigger**: On Creation/Update or scheduled.

9. **Inter-Company POS Invoice**
   - **Target**: POS Orders (`pos.order`).
   - **Action**: When a POS Order is invoiced, it creates a corresponding *Customer Invoice* in **Company ID 12**.
   - **Customer**: The invoice is billed to the **Source Company** (the one that made the POS Order).
   - **Price Logic**: Items of type 'Storable Product' (Goods) are billed at **50% price**. Services retain full price.
   - **Notifications**: Provides real-time Client and Chatter feedback on success/failure.
   - **Use Case**: Re-billing or centralized accounting.

10. **Remove Empty Product Categories**
    - **Model**: `product.category`.
    - **Action**: Identifies and removes ALL categories that do not have any products associated with them (including their subcategories).
    - **Safety**: Uses hierarchical checks to ensure only truly empty branches are removed.

11. **Halve Product Sales Price**
    - **Model**: `product.template` or `product.product`.
    - **Action**: Bulk reduces the `list_price` (Sales Price) of selected products by 50%. Optimized for large datasets with batch processing.
    - **Notifications**: Provides a success notification with the update count.

12. **Auto Reconcile Bills with Payments**
    - **Model**: `account.move` (Journal Entry / Bills)
    - **Action**: Automatically reconciles selected open Vendor Bills with outstanding payments (credits) for the same partner.
    - **Matching Logic**:
        1. **Exact Match**: Matches if Amount is same AND Payment Memo/Ref matches Bill Ref/Name.
        2. **Amount Match**: Matches if Amount is same (secondary priority).
    - **Usage**: Select Bills in List View -> Actions -> Auto Reconcile.

13. **Archive and Reset Product Category**
    - **Model**: `product.template` or `product.product`.
    - **Action**: A combined batch-safe action that archives selected products AND resets their category to ID 1.
    - **Notifications**: Provides a success notification upon completion.

14. **Batch Add Taxes to All Invoice Lines**
    - **Model**: `account.move` (Invoices)
    - **Action**: Iterates over invoice lines and adds tax ID 315 to all lines in batches.
    - **Notifications**: Provides real-time progress notifications via Odoo's Bus system for each batch processed.
    - **Safety**: Ensures the tax is only added if not already present on the line.

15. **Batch Reset Journal Entries to Draft**
    - **Model**: `account.move` (Journal Entries)
    - **Action**: Resets selected Journal Entries to `draft` state in batches.
    - **Notifications**: Provides real-time progress notifications via Odoo's Bus system for each batch processed.
    - **Logic**: Only processes explicitly selected IDs, ensuring no accidental bulk resets beyond selection.

16. **Batch Remove Taxes from All Invoice Lines**
    - **Model**: `account.move` (Invoices)
    - **Action**: Clears all taxes from all lines of selected invoices in batches.
    - **Notifications**: Provides real-time progress notifications via Odoo's Bus system for each batch processed.

## **Implementation**  

- **Via Odoo Studio**:  
  - Create server actions and paste the provided Python code.  
  - Add buttons to BOM views for easy access.  

- **Manual XML Installation**:  
  - Deploy via custom module for better control.  

## **Why Use This?**  

✅ **Prevents Errors** – Ensures BOMs only contain active, non-duplicate components  
✅ **Improves Performance** – Clean BOMs load faster and avoid confusion  
✅ **Maintenance-Friendly** – Runs on demand or can be scheduled  

---  
**Powered by Hsx TECH** 🚀  

*(Need customization? Contact Hsx TECH for Odoo solutions!)*  

---  

### **Repository Structure**  
```
📂 odoo-bom-cleanup/  
├── README.md  
├── remove_archived_products.py  
├── remove_duplicate_products.py  
├── Odoo_auto_reconcile_bills_payments.py
├── combined_cleanup_action.py
├── Odoo_remove_zero_qty_products.py
├── Odoo_Reset_to_draft_Journal entries.py
├── Odoo_update_income_expense_accounts.py
├── Odoo_Cancel_Draft_Vendor_Bills.py
├── Odoo_Reset_to_draft_Payments.py
├── Odoo_Cancel_Payments.py
├── Odoo_Sync_POS_Category.py
├── Odoo_InterCompany_POS_Invoice.py
├── Odoo_remove_duplicate_empty_categories.py
├── Odoo_Halve_Product_Price.py
├── Odoo_archive_and_reset_category.py
├── Odoo_Add_Taxes_to_Invoices.py
├── Odoo_Batch_Reset_Journal_Entries.py
├── Odoo_Remove_Taxes_from_Invoices.py
```  

### **License**  
MIT License – Free to use and modify.  

---  
**Contribute or Report Issues**  
Feel free to fork, improve, or suggest enhancements!  


**Powered by Hsx TECH** – *Collaborate, Lead, Innovate* 
