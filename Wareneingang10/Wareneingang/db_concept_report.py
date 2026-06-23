from app.db import fetch_all


CHECKS = [
    (
        "View Wareneingang Status",
        """
        SELECT STATUS, COUNT(*) AS COUNT_ROWS
        FROM list_views.V_LIST_GOODS_RECEIPT
        GROUP BY STATUS
        ORDER BY STATUS
        """,
    ),
    (
        "View Wareneingangsposition Condition",
        """
        SELECT CONDITION_ID, COUNT(*) AS COUNT_ROWS
        FROM list_views.V_LIST_GOODS_RECEIPT_ITEM
        GROUP BY CONDITION_ID
        ORDER BY CONDITION_ID
        """,
    ),
    (
        "View Wareneingangsposition Sollmengen",
        """
        SELECT
            SUM(CASE WHEN ORDERED_QTY <= 0 THEN 1 ELSE 0 END) AS ORDERED_QTY_NOT_POSITIVE,
            SUM(CASE WHEN RECEIVED_QTY < 0 THEN 1 ELSE 0 END) AS RECEIVED_QTY_NEGATIVE,
            COUNT(*) AS TOTAL_ROWS
        FROM list_views.V_LIST_GOODS_RECEIPT_ITEM
        """,
    ),
    (
        "Basistabelle Wareneingang Status",
        """
        SELECT STATUS, COUNT(*) AS COUNT_ROWS
        FROM dbo.T_GOODS_RECEIPT
        GROUP BY STATUS
        ORDER BY STATUS
        """,
    ),
    (
        "Basistabelle Wareneingangsposition Condition",
        """
        SELECT CONDITION_ID, COUNT(*) AS COUNT_ROWS
        FROM dbo.T_GOODS_RECEIPT_ITEM
        GROUP BY CONDITION_ID
        ORDER BY CONDITION_ID
        """,
    ),
]


for title, query in CHECKS:
    print(f"\n=== {title} ===")
    rows = fetch_all(query)

    if not rows:
        print("  keine Treffer")
        continue

    for row in rows:
        print(f"  {row}")
