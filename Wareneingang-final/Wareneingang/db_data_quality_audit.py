from app.db import fetch_all


MAX_SAMPLE_ROWS = 20


def print_rows(rows):
    if not rows:
        print("  OK")
        return

    for row in rows[:MAX_SAMPLE_ROWS]:
        print(f"  {row}")

    if len(rows) > MAX_SAMPLE_ROWS:
        print(f"  ... {len(rows) - MAX_SAMPLE_ROWS} weitere Zeilen")


def run_check(title, sql, params=None):
    print(f"\n=== {title} ===")

    try:
        rows = fetch_all(sql, params or [])
        print_rows(rows)

    except Exception as exc:
        print(f"  CHECK KANN NICHT AUSGEFUEHRT WERDEN: {exc}")


def has_column(schema, table, column):
    rows = fetch_all(
        """
            SELECT 1 AS FOUND
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = ?
              AND TABLE_NAME = ?
              AND COLUMN_NAME = ?
        """,
        [schema, table, column],
    )
    return len(rows) > 0


print("Datenqualitaets-Audit fuer das Wareneingang-Systemkonzept")


run_check(
    "T_CODE: Status- und Condition-Stammdaten",
    """
        SELECT ID_CODE, CODE_TYPE, CODE_NAME
        FROM dbo.T_CODE
        WHERE CODE_TYPE IN (
            'GOODS_RECEIPT',
            'CONDITION_ID',
            'GOODS_CONDITION',
            'SUPPLIER_INVOICE',
            'MOVEMENT_TYPE'
        )
        ORDER BY CODE_TYPE, ID_CODE
    """,
)


run_check(
    "Wareneingang: Status nicht im Konzept 200-205",
    """
        SELECT STATUS, COUNT(*) AS COUNT_ROWS
        FROM dbo.T_GOODS_RECEIPT
        WHERE STATUS NOT IN (200, 201, 202, 203, 204, 205)
        GROUP BY STATUS
        ORDER BY STATUS
    """,
)


run_check(
    "Wareneingang: Datum in der Zukunft",
    """
        SELECT GOODS_RECEIPT_ID, PO_ID, RECEIPT_DATE, STATUS
        FROM dbo.T_GOODS_RECEIPT
        WHERE CAST(RECEIPT_DATE AS date) > CAST(GETDATE() AS date)
        ORDER BY RECEIPT_DATE DESC
    """,
)


run_check(
    "Wareneingang: PO_ID existiert nicht in T_PO",
    """
        SELECT gr.GOODS_RECEIPT_ID, gr.PO_ID, gr.RECEIPT_DATE, gr.STATUS
        FROM dbo.T_GOODS_RECEIPT gr
        LEFT JOIN dbo.T_PO po
            ON po.PO_ID = gr.PO_ID
        WHERE po.PO_ID IS NULL
        ORDER BY gr.GOODS_RECEIPT_ID
    """,
)


run_check(
    "Bestellpositionen: QUANTITY <= 0 nach Art",
    """
        SELECT
            CASE
                WHEN QUANTITY < 0 THEN 'NEGATIV'
                WHEN QUANTITY = 0 THEN 'NULL'
            END AS PROBLEM,
            COUNT(*) AS COUNT_ROWS,
            MIN(QUANTITY) AS MIN_QUANTITY,
            MAX(QUANTITY) AS MAX_QUANTITY
        FROM dbo.T_PO_ITEMS
        WHERE QUANTITY <= 0
        GROUP BY
            CASE
                WHEN QUANTITY < 0 THEN 'NEGATIV'
                WHEN QUANTITY = 0 THEN 'NULL'
            END
        ORDER BY PROBLEM
    """,
)


run_check(
    "Bestellpositionen: QUANTITY <= 0 Beispiele",
    """
        SELECT
            po_item.PO_ID,
            po_item.PO_ITEM_ID,
            po_item.ID_COMPONENT,
            component.COMPONENT_NAME,
            po_item.QUANTITY,
            po_item.STATUS
        FROM dbo.T_PO_ITEMS po_item
        LEFT JOIN dbo.T_BIKE_COMPONENTS component
            ON component.COMPONENT_ID = po_item.ID_COMPONENT
        WHERE po_item.QUANTITY <= 0
        ORDER BY po_item.PO_ID, po_item.PO_ITEM_ID
    """,
)


run_check(
    "Bestellpositionen: Komponente existiert nicht",
    """
        SELECT po_item.PO_ID, po_item.PO_ITEM_ID, po_item.ID_COMPONENT
        FROM dbo.T_PO_ITEMS po_item
        LEFT JOIN dbo.T_BIKE_COMPONENTS component
            ON component.COMPONENT_ID = po_item.ID_COMPONENT
        WHERE component.COMPONENT_ID IS NULL
        ORDER BY po_item.PO_ID, po_item.PO_ITEM_ID
    """,
)


run_check(
    "Wareneingangsposition: Condition nicht im Konzept 401-408",
    """
        SELECT CONDITION_ID, COUNT(*) AS COUNT_ROWS
        FROM dbo.T_GOODS_RECEIPT_ITEM
        WHERE CONDITION_ID NOT IN (401, 402, 404, 405, 406, 407, 408)
        GROUP BY CONDITION_ID
        ORDER BY CONDITION_ID
    """,
)


run_check(
    "Wareneingangsposition: ORDERED_QTY <= 0 oder RECEIVED_QTY < 0",
    """
        SELECT
            GOODS_RECEIPT_ITEM_ID,
            GOODS_RECEIPT_ID,
            PO_ID,
            PO_ITEM_ID,
            ORDERED_QTY,
            RECEIVED_QTY,
            CONDITION_ID
        FROM dbo.T_GOODS_RECEIPT_ITEM
        WHERE ORDERED_QTY <= 0
           OR RECEIVED_QTY < 0
        ORDER BY GOODS_RECEIPT_ID, GOODS_RECEIPT_ITEM_ID
    """,
)


run_check(
    "Wareneingangsposition: PO_ID/PO_ITEM_ID passt nicht zu T_PO_ITEMS",
    """
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
        LEFT JOIN dbo.T_PO_ITEMS exact_po_item
            ON exact_po_item.PO_ID = item.PO_ID
           AND exact_po_item.PO_ITEM_ID = item.PO_ITEM_ID
        OUTER APPLY (
            SELECT TOP 1 possible_po_item.PO_ID
            FROM dbo.T_PO_ITEMS possible_po_item
            WHERE possible_po_item.PO_ITEM_ID = item.PO_ITEM_ID
            ORDER BY possible_po_item.PO_ID
        ) po_item
        WHERE exact_po_item.PO_ITEM_ID IS NULL
           OR receipt.PO_ID <> item.PO_ID
        ORDER BY item.GOODS_RECEIPT_ID, item.GOODS_RECEIPT_ITEM_ID
    """,
)


run_check(
    "Wareneingangsposition: gleiche PO_ITEM_ID doppelt im selben Wareneingang",
    """
        SELECT
            GOODS_RECEIPT_ID,
            PO_ITEM_ID,
            COUNT(*) AS COUNT_ROWS
        FROM dbo.T_GOODS_RECEIPT_ITEM
        GROUP BY GOODS_RECEIPT_ID, PO_ITEM_ID
        HAVING COUNT(*) > 1
        ORDER BY GOODS_RECEIPT_ID, PO_ITEM_ID
    """,
)


run_check(
    "Wareneingangsposition: Condition passt nicht zu Soll/Ist",
    """
        SELECT
            GOODS_RECEIPT_ITEM_ID,
            GOODS_RECEIPT_ID,
            PO_ID,
            PO_ITEM_ID,
            ORDERED_QTY,
            RECEIVED_QTY,
            CONDITION_ID
        FROM dbo.T_GOODS_RECEIPT_ITEM
        WHERE
            (
                RECEIVED_QTY < ORDERED_QTY
                AND CONDITION_ID NOT IN (402, 404, 406, 408)
            )
            OR
            (
                RECEIVED_QTY > ORDERED_QTY
                AND CONDITION_ID NOT IN (402, 405, 406, 408)
            )
            OR
            (
                RECEIVED_QTY = ORDERED_QTY
                AND CONDITION_ID NOT IN (401, 407, 408)
            )
        ORDER BY GOODS_RECEIPT_ID, GOODS_RECEIPT_ITEM_ID
    """,
)


run_check(
    "Lieferantenrechnung: Status nicht im Konzept 300-301",
    """
        SELECT INVOICE_STATUS, COUNT(*) AS COUNT_ROWS
        FROM dbo.T_SUPPLIER_INVOICE
        WHERE INVOICE_STATUS NOT IN (300, 301)
        GROUP BY INVOICE_STATUS
        ORDER BY INVOICE_STATUS
    """,
)


run_check(
    "Lieferantenrechnung: Datum/Faelligkeit ungueltig",
    """
        SELECT INVOICE_ID, PO_ID, SUPPLIER_ID, INVOICE_DATE, DUE_DATE
        FROM dbo.T_SUPPLIER_INVOICE
        WHERE CAST(INVOICE_DATE AS date) > CAST(GETDATE() AS date)
           OR DUE_DATE <= INVOICE_DATE
        ORDER BY INVOICE_ID
    """,
)


run_check(
    "Lieferantenrechnung: Brutto != Netto + MwSt",
    """
        SELECT
            INVOICE_ID,
            TOTAL_NET_AMOUNT,
            TOTAL_VAT_AMOUNT,
            TOTAL_GROSS_AMOUNT
        FROM dbo.T_SUPPLIER_INVOICE
        WHERE ROUND(TOTAL_NET_AMOUNT + TOTAL_VAT_AMOUNT, 2)
           <> ROUND(TOTAL_GROSS_AMOUNT, 2)
        ORDER BY INVOICE_ID
    """,
)


run_check(
    "Lieferantenrechnung: Supplier passt nicht zur Bestellung",
    """
        SELECT
            invoice.INVOICE_ID,
            invoice.PO_ID,
            invoice.SUPPLIER_ID AS INVOICE_SUPPLIER_ID,
            po.SUPPLIER_ID AS PO_SUPPLIER_ID
        FROM dbo.T_SUPPLIER_INVOICE invoice
        LEFT JOIN dbo.T_PO po
            ON po.PO_ID = invoice.PO_ID
        WHERE po.PO_ID IS NULL
           OR invoice.SUPPLIER_ID <> po.SUPPLIER_ID
        ORDER BY invoice.INVOICE_ID
    """,
)


run_check(
    "Lieferantenrechnung: keine gebuchte Lieferung zur PO",
    """
        SELECT invoice.INVOICE_ID, invoice.PO_ID, invoice.SUPPLIER_ID
        FROM dbo.T_SUPPLIER_INVOICE invoice
        WHERE NOT EXISTS (
            SELECT 1
            FROM dbo.T_GOODS_RECEIPT receipt
            WHERE receipt.PO_ID = invoice.PO_ID
              AND receipt.STATUS = 202
        )
        ORDER BY invoice.INVOICE_ID
    """,
)


if has_column("dbo", "T_SUPPLIER_INVOICE_ITEM", "QUANTITY"):
    run_check(
        "Lieferantenrechnungsposition: Quantity/Preis/Steuer ungueltig",
        """
            SELECT *
            FROM dbo.T_SUPPLIER_INVOICE_ITEM
            WHERE QUANTITY <= 0
               OR UNIT_PRICE < 0
               OR UNIT_VAT_PCT < 0
               OR UNIT_VAT_PCT > 30
               OR UNIT_DISCOUNT_PCT < 0
               OR UNIT_DISCOUNT_PCT > 100
        """,
    )

if (
    has_column("dbo", "T_SUPPLIER_INVOICE_ITEM", "COMPONENT_ID")
    and has_column("dbo", "T_SUPPLIER_INVOICE_ITEM", "MTB_COMPONENT_ID")
):
    run_check(
        "Lieferantenrechnungsposition: Komponenten-XOR verletzt",
        """
            SELECT *
            FROM dbo.T_SUPPLIER_INVOICE_ITEM
            WHERE
                (COMPONENT_ID IS NULL AND MTB_COMPONENT_ID IS NULL)
                OR
                (COMPONENT_ID IS NOT NULL AND MTB_COMPONENT_ID IS NOT NULL)
        """,
    )

if has_column("dbo", "T_COMPONENTS_MOVEMENTS", "QUANTITY"):
    run_check(
        "Bestandsbewegungen: Quantity <= 0 oder Movement-Type ungueltig",
        """
            SELECT *
            FROM dbo.T_COMPONENTS_MOVEMENTS
            WHERE QUANTITY <= 0
               OR MOVEMENT_TYPE NOT IN (500, 501)
        """,
    )
