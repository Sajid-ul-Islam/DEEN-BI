import re


# --- Category Logic ---
def get_category_from_name(name):
    """Categorizes products based on keywords in their names (v9.5 Expert Rules)."""
    name_str = str(name).lower()

    def has_any(keywords, text):
        return any(
            re.search(rf"\b{re.escape(kw.lower())}\b", text, re.IGNORECASE)
            for kw in keywords
        )

    specific_cats = {
        "Tank Top": ["tank top"],
        "Boxer": ["boxer"],
        "Jeans": ["jeans"],
        "Denim Shirt": ["denim"],
        "Flannel Shirt": ["flannel"],
        "Polo Shirt": ["polo"],
        "Panjabi": ["panjabi", "punjabi"],
        "Trousers": ["trousers", "trouser"],
        "Joggers": ["joggers", "jogger", "track pant"],
        "Twill Chino": ["twill chino", "chino", "twill"],
        "Mask": ["mask"],
        "Leather Bag": ["bag", "backpack"],
        "Water Bottle": ["water bottle"],
        "Contrast Shirt": ["contrast"],
        "Turtleneck": ["turtleneck", "mock neck"],
        "Drop Shoulder": ["drop", "shoulder"],
        "Wallet": ["wallet"],
        "Kaftan Shirt": ["kaftan"],
        "Active Wear": ["active wear"],
        "Jersy": ["jersy"],
        "Sweatshirt": ["sweatshirt", "hoodie", "pullover"],
        "Jacket": ["jacket", "outerwear", "coat"],
        "Belt": ["belt"],
        "Sweater": ["sweater", "cardigan", "knitwear"],
        "Passport Holder": ["passport holder"],
        "Card Holder": ["card holder"],
        "Cap": ["cap"],
    }

    for cat, keywords in specific_cats.items():
        if has_any(keywords, name_str):
            return cat

    fs_keywords = ["full sleeve", "long sleeve", "fs", "l/s"]
    if has_any(["t-shirt", "t shirt", "tee"], name_str):
        return "FS T-Shirt" if has_any(fs_keywords, name_str) else "HS T-Shirt"

    if has_any(["shirt"], name_str):
        return "FS Shirt" if has_any(fs_keywords, name_str) else "HS Shirt"

    return "Others"


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
