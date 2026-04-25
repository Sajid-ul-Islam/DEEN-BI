import re


# --- Category Logic ---
def get_category_from_name(name):
    """
    Redirects to the master centralized categorization engine to ensure
    all expert rules (like Active Wear, Trousers, Bundles) are applied globally.
    """
    from BackEnd.core.categories import get_category_for_sales
    return get_category_for_sales(name)


# --- Address Logic ---
def normalize_city_name(city_name):
    """
    Standardizes city/district names to match Pathao specific formats or correct spelling.
    """
    if not city_name:
        return ""

    c = city_name.strip()
    c_lower = c.lower()

    # User requested mappings
    if "brahmanbaria" in c_lower:
        return "B. Baria"
    if "narsingdi" in c_lower or "narsinghdi" in c_lower:
        return "Narshingdi"
    if "bagura" in c_lower or "bogura" in c_lower:
        return "Bogra"

    # Other common corrections
    if "chattogram" in c_lower:
        return "Chittagong"
    if "cox" in c_lower and "bazar" in c_lower:
        return "Cox's Bazar"
    if "chapainawabganj" in c_lower:
        return "Chapainawabganj"

    # Default: Title Case
    return c.title()
