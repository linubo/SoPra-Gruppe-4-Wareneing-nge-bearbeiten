/*
Benoetigte SQL-Server-Objekte fuer Modul Gruppe 04:
Wareneingaenge aus Lieferungen erstellen und Lieferantenrechnungen erfassen.

Quelle: Systemkonzept "Wareneingaenge und Lieferantenzahlungen"
Dieses Skript legt nur die View-Schicht aus dem Konzept an. Tabellen,
Constraints, T_CODE/T_CODE_NEXT-Werte und Stored Functions muessen separat
mit der Datenbankgruppe bzw. dem Prof abgestimmt werden.
*/


/* ============================================================
   SCHEMAS
   ============================================================ */

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'list_views')
    EXEC('CREATE SCHEMA list_views');
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'ins_views')
    EXEC('CREATE SCHEMA ins_views');
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'upd_views')
    EXEC('CREATE SCHEMA upd_views');
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'lov_views')
    EXEC('CREATE SCHEMA lov_views');
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'stored_func')
    EXEC('CREATE SCHEMA stored_func');
GO


/* ============================================================
   LIST-, INSERT- UND UPDATE-VIEWS
   ============================================================ */

CREATE OR ALTER VIEW ins_views.V_INS_GOODS_RECEIPT AS
SELECT * FROM dbo.T_GOODS_RECEIPT;
GO

CREATE OR ALTER VIEW upd_views.V_UPD_GOODS_RECEIPT AS
SELECT * FROM dbo.T_GOODS_RECEIPT;
GO

CREATE OR ALTER VIEW list_views.V_LIST_GOODS_RECEIPT AS
SELECT * FROM dbo.T_GOODS_RECEIPT;
GO

CREATE OR ALTER VIEW ins_views.V_INS_GOODS_RECEIPT_ITEM AS
SELECT * FROM dbo.T_GOODS_RECEIPT_ITEM;
GO

CREATE OR ALTER VIEW upd_views.V_UPD_GOODS_RECEIPT_ITEM AS
SELECT * FROM dbo.T_GOODS_RECEIPT_ITEM;
GO

CREATE OR ALTER VIEW list_views.V_LIST_GOODS_RECEIPT_ITEM AS
SELECT * FROM dbo.T_GOODS_RECEIPT_ITEM;
GO

CREATE OR ALTER VIEW ins_views.V_INS_SUPPLIER_INVOICE AS
SELECT * FROM dbo.T_SUPPLIER_INVOICE;
GO

CREATE OR ALTER VIEW upd_views.V_UPD_SUPPLIER_INVOICE AS
SELECT * FROM dbo.T_SUPPLIER_INVOICE;
GO

CREATE OR ALTER VIEW list_views.V_LIST_SUPPLIER_INVOICE AS
SELECT * FROM dbo.T_SUPPLIER_INVOICE;
GO

CREATE OR ALTER VIEW ins_views.V_INS_SUPPLIER_INVOICE_ITEM AS
SELECT * FROM dbo.T_SUPPLIER_INVOICE_ITEM;
GO

CREATE OR ALTER VIEW list_views.V_LIST_SUPPLIER_INVOICE_ITEM AS
SELECT * FROM dbo.T_SUPPLIER_INVOICE_ITEM;
GO

CREATE OR ALTER VIEW list_views.V_LIST_COMPONENTS_MOVEMENTS AS
SELECT * FROM dbo.T_COMPONENTS_MOVEMENTS;
GO


/* ============================================================
   LOV-VIEWS
   ============================================================ */

CREATE OR ALTER VIEW lov_views.LOV_STATUS_GOODS_RECEIPT
(
    CODE_ID,
    GOODS_RECEIPT_STATUS
) AS
SELECT
    ID_CODE AS CODE_ID,
    CODE_NAME
FROM dbo.T_CODE
WHERE CODE_TYPE = 'GOODS_RECEIPT';
GO

CREATE OR ALTER VIEW lov_views.LOV_GOODS_CONDITION
(
    CODE_ID,
    CONDITION_NAME
) AS
SELECT
    ID_CODE AS CODE_ID,
    CODE_NAME
FROM dbo.T_CODE
WHERE CODE_TYPE = 'CONDITION_ID';
GO

CREATE OR ALTER VIEW lov_views.LOV_STATUS_SUPPLIER_INVOICE
(
    CODE_ID,
    INVOICE_STATUS
) AS
SELECT
    ID_CODE AS CODE_ID,
    CODE_NAME
FROM dbo.T_CODE
WHERE CODE_TYPE = 'SUPPLIER_INVOICE';
GO

CREATE OR ALTER VIEW lov_views.LOV_MOVEMENT_TYPE
(
    CODE_ID,
    MOVEMENT_TYPE_NAME
) AS
SELECT
    ID_CODE AS CODE_ID,
    CODE_NAME
FROM dbo.T_CODE
WHERE CODE_TYPE = 'MOVEMENT_TYPE';
GO


/* ============================================================
   ERWARTETE STAMMDATEN AUS DEM SYSTEMKONZEPT
   ============================================================ */

/*
T_CODE / CODE_TYPE = GOODS_RECEIPT:
200 ERFASST
201 IN PRUEFUNG
202 WARENEINGANG GEBUCHT
203 MIT ABWEICHUNG
204 IN KLAERUNG
205 RETOURE VERANLASST

T_CODE / CODE_TYPE = CONDITION_ID:
401 BESCHAEDIGT
402 FALSCHLIEFERUNG
404 UNVOLLSTAENDIG
405 UEBERLIEFERUNG
406 KOMBINIERTE ABWEICHUNG
407 WARE OK
408 PRUEFUNG AUSSTEHEND

T_CODE / CODE_TYPE = SUPPLIER_INVOICE:
300 ERFASST
301 AN BUCHHALTUNG UEBERMITTELT

T_CODE / CODE_TYPE = MOVEMENT_TYPE:
500 IN
501 OUT
*/


/* ============================================================
   ERWARTETE STORED FUNCTIONS
   ============================================================ */

/*
Die Flask-App ruft diese Funktionen optional auf, sobald sie vorhanden sind:

stored_func.fn_g04_chk_GoodsReceipt
stored_func.fn_g04_chk_GoodsReceiptItem
stored_func.fn_g04_chk_GoodsReceiptBookingCondition
stored_func.fn_g04_chk_SupplierInvoice
stored_func.fn_g04_chk_SupplierInvoiceItem
stored_func.fn_g04_update_component_stock

Hinweis: Im Systemkonzept taucht fuer die Bestandserhoehung auch der Name
stored_func.fn_update_component_stock auf. Die App akzeptiert beide Namen.
*/
