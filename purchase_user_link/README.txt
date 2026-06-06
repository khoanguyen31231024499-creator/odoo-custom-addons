INSTALL THIS AS A NEW MODULE, DO NOT UPDATE purchase_user_link.

1. Copy the whole folder po_approval_fix into custom_addons:
   custom_addons/po_approval_fix/

2. Stop Odoo completely.

3. Install this new module:
   python odoo-bin -d odoocom --addons-path=addons,custom_addons --db_host=localhost --db_port=5432 --db_user=nhatkhanh --db_password=210605 -i po_approval_fix --stop-after-init

4. Start Odoo normally:
   python odoo-bin -d odoocom --addons-path=addons,custom_addons --db_host=localhost --db_port=5432 --db_user=nhatkhanh --db_password=210605

5. Create a new RFQ with Total > 20,000,000 VND and click Confirm.

Expected log:
[PO_APPROVAL_FIX] custom button_confirm called
[PO_APPROVAL_FIX] running: po=...

Expected result:
RFQ -> To Approve, not Purchase Order.

If it still does not work, another module loaded after this one overrides button_confirm without calling super().
