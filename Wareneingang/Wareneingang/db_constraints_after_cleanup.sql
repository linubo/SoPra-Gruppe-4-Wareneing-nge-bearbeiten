/*
Constraints fuer das Systemkonzept.

Wichtig:
Dieses Skript erst ausfuehren, wenn db_data_quality_audit.py keine Treffer
mehr fuer die betroffenen Regeln meldet. Sonst scheitern die ALTER TABLE
Statements bewusst, weil bereits falsche Daten vorhanden sind.
*/


/* ============================================================
   WARENEINGANG
   ============================================================ */

ALTER TABLE dbo.T_GOODS_RECEIPT WITH CHECK
ADD CONSTRAINT CHK_T_GR_STATUS_SYSTEMKONZEPT
CHECK (STATUS IN (200, 201, 202, 203, 204, 205));
GO

ALTER TABLE dbo.T_GOODS_RECEIPT WITH CHECK
ADD CONSTRAINT CHK_T_GR_RECEIPT_DATE_NOT_FUTURE
CHECK (CAST(RECEIPT_DATE AS date) <= CAST(GETDATE() AS date));
GO


/* ============================================================
   BESTELLPOSITIONEN
   ============================================================ */

ALTER TABLE dbo.T_PO_ITEMS WITH CHECK
ADD CONSTRAINT CHK_T_PO_ITEMS_QUANTITY_POSITIVE
CHECK (QUANTITY > 0);
GO


/* ============================================================
   WARENEINGANGSPOSITIONEN
   ============================================================ */

ALTER TABLE dbo.T_GOODS_RECEIPT_ITEM WITH CHECK
ADD CONSTRAINT CHK_T_GR_ITEM_QUANTITY
CHECK (ORDERED_QTY > 0 AND RECEIVED_QTY >= 0);
GO

ALTER TABLE dbo.T_GOODS_RECEIPT_ITEM WITH CHECK
ADD CONSTRAINT CHK_T_GR_ITEM_CONDITION_SYSTEMKONZEPT
CHECK (CONDITION_ID IN (401, 402, 404, 405, 406, 407, 408));
GO

ALTER TABLE dbo.T_GOODS_RECEIPT_ITEM WITH CHECK
ADD CONSTRAINT FK_T_GR_ITEM_T_PO_ITEMS_SYSTEMKONZEPT
FOREIGN KEY (PO_ID, PO_ITEM_ID)
REFERENCES dbo.T_PO_ITEMS (PO_ID, PO_ITEM_ID);
GO

ALTER TABLE dbo.T_GOODS_RECEIPT_ITEM WITH CHECK
ADD CONSTRAINT CHK_T_GR_ITEM_CONDITION_QTY_MATCH
CHECK (
    (
        RECEIVED_QTY < ORDERED_QTY
        AND CONDITION_ID IN (402, 404, 406, 408)
    )
    OR
    (
        RECEIVED_QTY > ORDERED_QTY
        AND CONDITION_ID IN (402, 405, 406, 408)
    )
    OR
    (
        RECEIVED_QTY = ORDERED_QTY
        AND CONDITION_ID IN (401, 407, 408)
    )
);
GO


/* ============================================================
   LIEFERANTENRECHNUNGEN
   ============================================================ */

ALTER TABLE dbo.T_SUPPLIER_INVOICE WITH CHECK
ADD CONSTRAINT CHK_T_SI_STATUS_SYSTEMKONZEPT
CHECK (INVOICE_STATUS IN (300, 301));
GO

ALTER TABLE dbo.T_SUPPLIER_INVOICE WITH CHECK
ADD CONSTRAINT CHK_T_SI_DATES
CHECK (
    CAST(INVOICE_DATE AS date) <= CAST(GETDATE() AS date)
    AND DUE_DATE > INVOICE_DATE
);
GO

ALTER TABLE dbo.T_SUPPLIER_INVOICE WITH CHECK
ADD CONSTRAINT CHK_T_SI_TOTALS
CHECK (ROUND(TOTAL_NET_AMOUNT + TOTAL_VAT_AMOUNT, 2) = ROUND(TOTAL_GROSS_AMOUNT, 2));
GO
