from datetime import date

APP_TITLE = "DEEN Commerce BI"
APP_VERSION = "v2.5.0"
APP_DATA_START_DATE = date(2022, 8, 1)

PRIMARY_NAV = ("Vision",)

PRIMARY_PAGE_CONFIG = (
    {
        "key": "intelligence_hub",
        "label": "Vision",
        "description": "Executive KPIs, Customer Behavior, and Strategic Analytics.",
    },
)

MORE_TOOLS = [
    "System Logs",
    "Dev Lab",
]

INVENTORY_LOCATIONS = ["Ecom", "Mirpur", "Wari", "Cumilla", "Sylhet"]

STATUS_COLORS = {
    "success": "#15803d",
    "warning": "#b45309",
    "error": "#b91c1c",
    "info": "#1d4ed8",
}
