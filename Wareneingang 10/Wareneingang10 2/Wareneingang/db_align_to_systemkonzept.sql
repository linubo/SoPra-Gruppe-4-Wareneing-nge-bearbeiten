/*
Konzept-Angleichung fuer Gruppe 04.

Ziel:
- alte Wareneingangsstatus 130/131/132 auf Konzeptstatus 200-205 umstellen
- alte Condition-Codes 140/141/142 auf Konzept-Codes 401-408 umstellen
- Views mit den Spaltennamen aus dem Systemkonzept bereitstellen
- Bestellpositionen inkl. Artikelname fuer das UI-Dropdown bereitstellen

Bitte vor dem Ausfuehren pruefen, ob keine andere Gruppe noch auf die
alten Codes 130/131/132 oder 140/141/142 angewiesen ist.
*/


BEGIN TRANSACTION;

/* ============================================================
   1) ALT-CODES AUF SYSTEMKONZEPT-CODES MIGRIEREN
   ============================================================ */

UPDATE dbo.T_GOODS_RECEIPT
SET STATUS =
    CASE STATUS
        WHEN 130 THEN 200 -- RECEIVED -> ERFASST
        WHEN 131 THEN 203 -- PARTIALLY RECEIVED -> MIT ABWEICHUNG
        WHEN 132 THEN 202 -- FULLY RECEIVED -> WARENEINGANG GEBUCHT
        ELSE STATUS
    END
WHERE STATUS IN (130, 131, 132);

UPDATE dbo.T_GOODS_RECEIPT_ITEM
SET CONDITION_ID =
    CASE CONDITION_ID
        WHEN 140 THEN 407 -- NO ISSUES -> WARE OK
        WHEN 141 THEN 401 -- DAMAGED -> BESCHAEDIGT
        WHEN 142 THEN 404 -- PARTS MISSING -> UNVOLLSTAENDIG
        ELSE CONDITION_ID
    END
WHERE CONDITION_ID IN (140, 141, 142);

COMMIT TRANSACTION;
GO


/* ============================================================
   2) WARENEINGANG-VIEWS MIT KONZEPT-SPALTENNAMEN
   ============================================================ */

CREATE OR ALTER VIEW list_views.V_LIST_GOODS_RECEIPT AS
SELECT
    gr.GOODS_RECEIPT_ID,
    gr.PO_ID,
    po.SUPPLIER_ID,
    gr.RECEIPT_DATE,
    gr.DELIVERY_NOTE_NUMBER AS DELIVERY_NOTE_NO,
    gr.STATUS,
    status_code.CODE_NAME AS STATUS_NAME,
    gr.INS_USER,
    gr.INS_DATE,
    gr.UPD_USER,
    gr.UPD_DATE
FROM dbo.T_GOODS_RECEIPT gr
LEFT JOIN dbo.T_PO po
    ON po.PO_ID = gr.PO_ID
LEFT JOIN dbo.T_CODE status_code
    ON status_code.ID_CODE = gr.STATUS
   AND status_code.CODE_TYPE = 'GOODS_RECEIPT';
GO

CREATE OR ALTER VIEW ins_views.V_INS_GOODS_RECEIPT AS
SELECT
    GOODS_RECEIPT_ID,
    PO_ID,
    RECEIPT_DATE,
    DELIVERY_NOTE_NUMBER AS DELIVERY_NOTE_NO,
    STATUS,
    INS_USER,
    INS_DATE,
    UPD_USER,
    UPD_DATE
FROM dbo.T_GOODS_RECEIPT;
GO

CREATE OR ALTER VIEW upd_views.V_UPD_GOODS_RECEIPT AS
SELECT
    GOODS_RECEIPT_ID,
    PO_ID,
    RECEIPT_DATE,
    DELIVERY_NOTE_NUMBER AS DELIVERY_NOTE_NO,
    STATUS,
    INS_USER,
    INS_DATE,
    UPD_USER,
    UPD_DATE
FROM dbo.T_GOODS_RECEIPT;
GO


/* ============================================================
   3) WARENEINGANGSPOSITIONS-VIEWS MIT ARTIKELNAME
   ============================================================ */

CREATE OR ALTER VIEW list_views.V_LIST_GOODS_RECEIPT_ITEM AS
SELECT
    item.GOODS_RECEIPT_ITEM_ID,
    item.GOODS_RECEIPT_ID,
    item.PO_ID,
    item.PO_ITEM_ID,
    component.COMPONENT_NAME AS ARTICLE,
    item.ORDERED_QTY,
    item.RECEIVED_QTY,
    item.CONDITION_ID,
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
    ON condition_code.ID_CODE = item.CONDITION_ID
   AND condition_code.CODE_TYPE = 'CONDITION_ID';
GO

CREATE OR ALTER VIEW ins_views.V_INS_GOODS_RECEIPT_ITEM AS
SELECT
    GOODS_RECEIPT_ITEM_ID,
    GOODS_RECEIPT_ID,
    PO_ID,
    PO_ITEM_ID,
    ORDERED_QTY,
    RECEIVED_QTY,
    CONDITION_ID,
    INS_USER,
    INS_DATE,
    UPD_USER,
    UPD_DATE
FROM dbo.T_GOODS_RECEIPT_ITEM;
GO

CREATE OR ALTER VIEW upd_views.V_UPD_GOODS_RECEIPT_ITEM AS
SELECT
    GOODS_RECEIPT_ITEM_ID,
    GOODS_RECEIPT_ID,
    PO_ID,
    PO_ITEM_ID,
    ORDERED_QTY,
    RECEIVED_QTY,
    CONDITION_ID,
    INS_USER,
    INS_DATE,
    UPD_USER,
    UPD_DATE
FROM dbo.T_GOODS_RECEIPT_ITEM;
GO


/* ============================================================
   4) DROPDOWN-VIEW FUER BESTELLPOSITIONEN
   ============================================================ */

CREATE OR ALTER VIEW list_views.V_LIST_PO_ITEM_FOR_GOODS_RECEIPT AS
SELECT
    po_item.PO_ID,
    po_item.PO_ITEM_ID,
    po_item.ID_COMPONENT AS COMPONENT_ID,
    component.COMPONENT_NAME AS ARTICLE,
    po_item.QUANTITY AS ORDERED_QTY,
    po_item.STATUS AS PO_ITEM_STATUS,
    po_item.DELIVERY_DATE,
    po_item.COMPONENT_PRICE,
    po_item.TOTAL_PRICE
FROM dbo.T_PO_ITEMS po_item
LEFT JOIN dbo.T_BIKE_COMPONENTS component
    ON component.COMPONENT_ID = po_item.ID_COMPONENT
WHERE po_item.QUANTITY > 0;
GO


/* ============================================================
   5) DATENQUALITAETSPRUEFUNG FUER PO_ITEM_ID-ZUORDNUNG
   ============================================================ */

/*
Diese Abfrage muss 0 Zeilen liefern, bevor ein Foreign Key auf
(PO_ID, PO_ITEM_ID) fachlich sauber aktiviert werden kann.

Beispiel fuer einen Fehler:
Ein Wareneingang gehoert zu PO_ID 502871, aber eine Position verweist auf
eine PO_ITEM_ID, die in T_PO_ITEMS zu einer anderen PO_ID gehoert.
*/

SELECT
    item.GOODS_RECEIPT_ITEM_ID,
    item.GOODS_RECEIPT_ID,
    receipt.PO_ID AS RECEIPT_PO_ID,
    item.PO_ID AS ITEM_PO_ID,
    item.PO_ITEM_ID,
    po_item.PO_ID AS REAL_PO_ID_FOR_ITEM
FROM dbo.T_GOODS_RECEIPT_ITEM item
LEFT JOIN dbo.T_GOODS_RECEIPT receipt
    ON receipt.GOODS_RECEIPT_ID = item.GOODS_RECEIPT_ID
LEFT JOIN dbo.T_PO_ITEMS po_item
    ON po_item.PO_ITEM_ID = item.PO_ITEM_ID
WHERE po_item.PO_ID IS NULL
   OR item.PO_ID <> po_item.PO_ID
   OR receipt.PO_ID <> item.PO_ID;

/*
Erst wenn die obige Pruefung keine Zeilen liefert:

ALTER TABLE dbo.T_GOODS_RECEIPT_ITEM WITH CHECK
ADD CONSTRAINT FK_T_GR_ITEM_T_PO_ITEMS
FOREIGN KEY (PO_ID, PO_ITEM_ID)
REFERENCES dbo.T_PO_ITEMS (PO_ID, PO_ITEM_ID);
*/


/* ============================================================
   6) DATENQUALITAETSPRUEFUNG FUER BESTELLMENGEN
   ============================================================ */

/*
Nach Systemkonzept muss ORDERED_QTY groesser als 0 sein.
Diese Abfrage zeigt Bestellpositionen, die noch nicht konzeptkonform sind.
*/

SELECT
    po_item.PO_ID,
    po_item.PO_ITEM_ID,
    po_item.ID_COMPONENT,
    component.COMPONENT_NAME,
    po_item.QUANTITY
FROM dbo.T_PO_ITEMS po_item
LEFT JOIN dbo.T_BIKE_COMPONENTS component
    ON component.COMPONENT_ID = po_item.ID_COMPONENT
WHERE po_item.QUANTITY <= 0
ORDER BY po_item.PO_ID, po_item.PO_ITEM_ID;

/*
Erst wenn die obige Pruefung keine Zeilen liefert:

ALTER TABLE dbo.T_PO_ITEMS WITH CHECK
ADD CONSTRAINT CHK_T_PO_ITEMS_QUANTITY_POSITIVE
CHECK (QUANTITY > 0);
*/
