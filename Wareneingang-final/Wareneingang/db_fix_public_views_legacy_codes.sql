/*
Nicht-destruktiver Fix fuer die offiziellen list_views.

Ziel:
- Andere Gruppen sehen ueber unsere list_views die Codes aus dem Systemkonzept.
- Die Basistabellen dbo.T_GOODS_RECEIPT und dbo.T_GOODS_RECEIPT_ITEM
  werden dabei nicht veraendert.

Mapping:
- GOODS_RECEIPT.STATUS 130 -> 200, 131 -> 203, 132 -> 202
- GOODS_RECEIPT_ITEM.CONDITION_ID 140 -> 407, 141 -> 401, 142 -> 404
*/

CREATE OR ALTER VIEW list_views.V_LIST_GOODS_RECEIPT AS
SELECT
    gr.GOODS_RECEIPT_ID,
    gr.PO_ID,
    po.SUPPLIER_ID,
    gr.RECEIPT_DATE,
    gr.DELIVERY_NOTE_NUMBER AS DELIVERY_NOTE_NO,
    CASE gr.STATUS
        WHEN 130 THEN 200
        WHEN 131 THEN 203
        WHEN 132 THEN 202
        ELSE gr.STATUS
    END AS STATUS,
    status_code.CODE_NAME AS STATUS_NAME,
    gr.INS_USER,
    gr.INS_DATE,
    gr.UPD_USER,
    gr.UPD_DATE
FROM dbo.T_GOODS_RECEIPT gr
LEFT JOIN dbo.T_PO po
    ON po.PO_ID = gr.PO_ID
LEFT JOIN dbo.T_CODE status_code
    ON status_code.ID_CODE = CASE gr.STATUS
        WHEN 130 THEN 200
        WHEN 131 THEN 203
        WHEN 132 THEN 202
        ELSE gr.STATUS
    END
   AND status_code.CODE_TYPE = 'GOODS_RECEIPT';
GO

CREATE OR ALTER VIEW list_views.V_LIST_GOODS_RECEIPT_ITEM AS
SELECT
    item.GOODS_RECEIPT_ITEM_ID,
    item.GOODS_RECEIPT_ID,
    item.PO_ID,
    item.PO_ITEM_ID,
    component.COMPONENT_NAME AS ARTICLE,
    item.ORDERED_QTY,
    item.RECEIVED_QTY,
    CASE item.CONDITION_ID
        WHEN 140 THEN 407
        WHEN 141 THEN 401
        WHEN 142 THEN 404
        ELSE item.CONDITION_ID
    END AS CONDITION_ID,
    condition_code.CODE_NAME AS CONDITION_NAME,
    item.INS_USER,
    item.INS_DATE,
    item.UPD_USER,
    item.UPD_DATE
FROM dbo.T_GOODS_RECEIPT_ITEM item
LEFT JOIN dbo.T_PO_ITEMS po_item
    ON po_item.PO_ID = item.PO_ID
   AND po_item.PO_ITEM_ID = item.PO_ITEM_ID
LEFT JOIN dbo.T_BIKE_COMPONENTS component
    ON component.COMPONENT_ID = po_item.ID_COMPONENT
LEFT JOIN dbo.T_CODE condition_code
    ON condition_code.ID_CODE = CASE item.CONDITION_ID
        WHEN 140 THEN 407
        WHEN 141 THEN 401
        WHEN 142 THEN 404
        ELSE item.CONDITION_ID
    END
   AND condition_code.CODE_TYPE = 'CONDITION_ID';
GO
