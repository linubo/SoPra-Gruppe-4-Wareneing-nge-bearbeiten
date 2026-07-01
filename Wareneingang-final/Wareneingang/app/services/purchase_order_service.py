from app.db import fetch_all, fetch_one, is_database_configured


purchase_orders = [
    {
        "PO_ID": 5001,
        "SUPPLIER_ID": 7001,
        "SUPPLIER_NAME": "Mueller Komponenten GmbH",
        "ORDER_DATE": "2026-05-20",
        "STATUS": "OFFEN",
    },
    {
        "PO_ID": 5002,
        "SUPPLIER_ID": 7002,
        "SUPPLIER_NAME": "Schneider Metallteile AG",
        "ORDER_DATE": "2026-05-21",
        "STATUS": "OFFEN",
    },
    {
        "PO_ID": 5003,
        "SUPPLIER_ID": 7003,
        "SUPPLIER_NAME": "Keller Bauteile GmbH",
        "ORDER_DATE": "2026-05-22",
        "STATUS": "TEILWEISE GELIEFERT",
    },
]


purchase_order_items = [
    {
        "PO_ID": 5001,
        "PO_ITEM_ID": 8001,
        "COMPONENT_ID": 1,
        "ARTICLE": "Schraube M8",
        "ORDERED_QTY": 100,
        "PO_ITEM_STATUS": "OFFEN",
    },
    {
        "PO_ID": 5002,
        "PO_ITEM_ID": 8002,
        "COMPONENT_ID": 2,
        "ARTICLE": "Metallplatte",
        "ORDERED_QTY": 50,
        "PO_ITEM_STATUS": "OFFEN",
    },
]


def _normalise_purchase_order(row):
    row.setdefault("SUPPLIER_NAME", f"Lieferant {row.get('SUPPLIER_ID', '-')}")
    row.setdefault("STATUS", "OFFEN")
    return row


def _normalise_purchase_order_item(row):
    row["PO_ID"] = int(row["PO_ID"])
    row["PO_ITEM_ID"] = int(row["PO_ITEM_ID"])
    row["ARTICLE"] = (
        row.get("ARTICLE")
        or row.get("COMPONENT_NAME")
        or f"Bestellposition {row['PO_ITEM_ID']}"
    )
    row["ORDERED_QTY"] = row.get("ORDERED_QTY") or row.get("QUANTITY") or 0
    return row


def _fetch_purchase_orders_from_db():
    queries = [
        """
            SELECT TOP 100
                p.PO_ID,
                p.SUPPLIER_ID,
                s.SUPPLIER_NAME,
                p.INS_DATE AS ORDER_DATE,
                p.PO_STATUS AS STATUS
            FROM dbo.T_PO p
            LEFT JOIN dbo.T_SUPPLIERS s
                ON s.SUPPLIER_ID = p.SUPPLIER_ID
            ORDER BY p.PO_ID DESC
        """,
        """
            SELECT TOP 100
                PO_ID,
                SUPPLIER_ID,
                INS_DATE AS ORDER_DATE,
                PO_STATUS AS STATUS
            FROM dbo.T_PO
            ORDER BY PO_ID DESC
        """,
        """
            SELECT TOP 100
                PO_ID,
                SUPPLIER_ID,
                INS_DATE AS ORDER_DATE
            FROM dbo.T_PO
            ORDER BY PO_ID DESC
        """,
    ]

    last_error = None

    for query in queries:
        try:
            return [_normalise_purchase_order(row) for row in fetch_all(query)]

        except Exception as exc:
            last_error = exc

    print("Bestellungen konnten nicht aus der DB geladen werden:")
    print(last_error)
    return None


def _fetch_purchase_order_items_from_db(po_id):
    queries = [
        """
            SELECT
                PO_ID,
                PO_ITEM_ID,
                COMPONENT_ID,
                ARTICLE,
                ORDERED_QTY,
                PO_ITEM_STATUS
            FROM list_views.V_LIST_PO_ITEM_FOR_GOODS_RECEIPT
            WHERE PO_ID = ?
              AND ORDERED_QTY > 0
            ORDER BY PO_ITEM_ID
        """,
        """
            SELECT
                po_item.PO_ID,
                po_item.PO_ITEM_ID,
                po_item.ID_COMPONENT AS COMPONENT_ID,
                component.COMPONENT_NAME AS ARTICLE,
                po_item.QUANTITY AS ORDERED_QTY,
                po_item.STATUS AS PO_ITEM_STATUS
            FROM dbo.T_PO_ITEMS po_item
            LEFT JOIN dbo.T_BIKE_COMPONENTS component
                ON component.COMPONENT_ID = po_item.ID_COMPONENT
            WHERE po_item.PO_ID = ?
              AND po_item.QUANTITY > 0
            ORDER BY po_item.PO_ITEM_ID
        """,
    ]

    last_error = None

    for query in queries:
        try:
            return [
                _normalise_purchase_order_item(row)
                for row in fetch_all(query, [po_id])
            ]

        except Exception as exc:
            last_error = exc

    print("Bestellpositionen konnten nicht aus der DB geladen werden:")
    print(last_error)
    return None


def _fetch_purchase_order_item_from_db(po_id, po_item_id):
    queries = [
        """
            SELECT
                PO_ID,
                PO_ITEM_ID,
                COMPONENT_ID,
                ARTICLE,
                ORDERED_QTY,
                PO_ITEM_STATUS
            FROM list_views.V_LIST_PO_ITEM_FOR_GOODS_RECEIPT
            WHERE PO_ID = ?
              AND PO_ITEM_ID = ?
              AND ORDERED_QTY > 0
        """,
        """
            SELECT
                po_item.PO_ID,
                po_item.PO_ITEM_ID,
                po_item.ID_COMPONENT AS COMPONENT_ID,
                component.COMPONENT_NAME AS ARTICLE,
                po_item.QUANTITY AS ORDERED_QTY,
                po_item.STATUS AS PO_ITEM_STATUS
            FROM dbo.T_PO_ITEMS po_item
            LEFT JOIN dbo.T_BIKE_COMPONENTS component
                ON component.COMPONENT_ID = po_item.ID_COMPONENT
            WHERE po_item.PO_ID = ?
              AND po_item.PO_ITEM_ID = ?
              AND po_item.QUANTITY > 0
        """,
    ]

    last_error = None
    query_succeeded = False

    for query in queries:
        try:
            row = fetch_one(query, [po_id, po_item_id])
            query_succeeded = True

            if row is not None:
                return _normalise_purchase_order_item(row)

        except Exception as exc:
            last_error = exc

    if not query_succeeded and last_error is not None:
        print("Bestellposition konnte nicht aus der DB geladen werden:")
        print(last_error)

    return None


def _fetch_purchase_order_item_by_item_id_from_db(po_item_id):
    query = """
        SELECT TOP 1
            po_item.PO_ID,
            po_item.PO_ITEM_ID,
            po_item.ID_COMPONENT AS COMPONENT_ID,
            component.COMPONENT_NAME AS ARTICLE,
            po_item.QUANTITY AS ORDERED_QTY,
            po_item.STATUS AS PO_ITEM_STATUS
        FROM dbo.T_PO_ITEMS po_item
        LEFT JOIN dbo.T_BIKE_COMPONENTS component
            ON component.COMPONENT_ID = po_item.ID_COMPONENT
        WHERE po_item.PO_ITEM_ID = ?
        ORDER BY po_item.PO_ID
    """

    try:
        row = fetch_one(query, [po_item_id])

        if row is not None:
            return _normalise_purchase_order_item(row)

    except Exception as exc:
        print("Bestellposition konnte nicht anhand der PO_ITEM_ID geladen werden:")
        print(exc)

    return None


def get_purchase_orders():
    if is_database_configured():
        db_purchase_orders = _fetch_purchase_orders_from_db()

        if db_purchase_orders:
            return db_purchase_orders

    return purchase_orders


def get_purchase_order_items(po_id):
    try:
        po_id = int(po_id)

    except (TypeError, ValueError):
        return []

    if is_database_configured():
        db_purchase_order_items = _fetch_purchase_order_items_from_db(po_id)

        if db_purchase_order_items is not None:
            return db_purchase_order_items

    return [
        item for item in purchase_order_items
        if item["PO_ID"] == po_id
    ]


def get_purchase_order_item(po_id, po_item_id):
    try:
        po_id = int(po_id)
        po_item_id = int(po_item_id)

    except (TypeError, ValueError):
        return None

    if is_database_configured():
        db_purchase_order_item = _fetch_purchase_order_item_from_db(po_id, po_item_id)

        if db_purchase_order_item is not None:
            return db_purchase_order_item

    for item in purchase_order_items:
        if item["PO_ID"] == po_id and item["PO_ITEM_ID"] == po_item_id:
            return item

    return None


def get_purchase_order_item_by_item_id(po_item_id):
    try:
        po_item_id = int(po_item_id)

    except (TypeError, ValueError):
        return None

    if is_database_configured():
        db_purchase_order_item = _fetch_purchase_order_item_by_item_id_from_db(
            po_item_id
        )

        if db_purchase_order_item is not None:
            return db_purchase_order_item

    for item in purchase_order_items:
        if item["PO_ITEM_ID"] == po_item_id:
            return item

    return None


def get_purchase_order_by_id(po_id):
    try:
        po_id = int(po_id)

    except (TypeError, ValueError):
        return None

    if is_database_configured():
        queries = [
            """
                SELECT
                    p.PO_ID,
                    p.SUPPLIER_ID,
                    s.SUPPLIER_NAME,
                    p.INS_DATE AS ORDER_DATE,
                    p.PO_STATUS AS STATUS
                FROM dbo.T_PO p
                LEFT JOIN dbo.T_SUPPLIERS s
                    ON s.SUPPLIER_ID = p.SUPPLIER_ID
                WHERE p.PO_ID = ?
            """,
            """
                SELECT
                    PO_ID,
                    SUPPLIER_ID,
                    INS_DATE AS ORDER_DATE,
                    PO_STATUS AS STATUS
                FROM dbo.T_PO
                WHERE PO_ID = ?
            """,
            """
                SELECT
                    PO_ID,
                    SUPPLIER_ID,
                    INS_DATE AS ORDER_DATE
                FROM dbo.T_PO
                WHERE PO_ID = ?
            """,
        ]

        last_error = None

        for query in queries:
            try:
                row = fetch_one(query, [po_id])

                if row is not None:
                    return _normalise_purchase_order(row)

            except Exception as exc:
                last_error = exc

        print("Bestellung konnte nicht aus der DB geladen werden:")
        print(last_error)

    for po in purchase_orders:
        if po["PO_ID"] == po_id:
            return po

    return None
