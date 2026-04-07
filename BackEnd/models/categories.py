import re

def _normalize(value) -> str:
    return str(value or "").strip().lower()

def _has_any(keywords, text):
    return any(
        re.search(rf"\b{re.escape(kw.lower())}\b", text, re.IGNORECASE)
        for kw in keywords
    )

def get_category_for_orders(name) -> str:
    """Old order categorization (maintained for backward compatibility if needed)."""
    text = _normalize(name)
    if not text:
        return "Items"

    order_rules = [
        ("Boxer", ["boxer"]),
        ("Jeans", ["jeans"]),
        ("Denim", ["denim"]),
        ("Flannel", ["flannel"]),
        ("Polo", ["polo"]),
        ("Panjabi", ["panjabi"]),
        ("Trousers", ["trouser"]),
        ("Twill", ["twill", "chino"]),
        ("Sweatshirt", ["sweatshirt"]),
        ("Tank Top", ["tank top"]),
        ("Pants", ["gabardine", "pant"]),
        ("Contrast Shirt", ["contrast"]),
        ("Turtleneck", ["turtleneck"]),
        ("Wallet", ["wallet"]),
        ("Kaftan", ["kaftan"]),
        ("Active", ["active"]),
        ("1 Pack Mask", ["mask"]),
        ("Bag", ["bag"]),
        ("Bottle", ["bottle"]),
    ]

    for label, keywords in order_rules:
        if _has_any(keywords, text):
            return label

    fs_keywords = ["full sleeve"]
    if _has_any(["t-shirt", "t shirt"], text):
        return "FS T-Shirt" if any(kw in text for kw in fs_keywords) else "HS T-Shirt"

    if "shirt" in text:
        return "FS Shirt" if any(kw in text for kw in fs_keywords) else "HS Shirt"

    words = text.split()
    if len(words) >= 2:
        return f"{words[0].title()} {words[1].title()}"
    return "Items"

def get_category_for_sales(name) -> str:
    """Categorizes products based on keywords in their names (v9.5 Expert Rules)."""
    name_str = _normalize(name)
    if not name_str:
        return "Others"

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
        if _has_any(keywords, name_str):
            return cat

    fs_keywords = ["full sleeve", "long sleeve", "fs", "l/s"]
    if _has_any(["t-shirt", "t shirt", "tee"], name_str):
        return "FS T-Shirt" if _has_any(fs_keywords, name_str) else "HS T-Shirt"

    if _has_any(["shirt"], name_str):
        return "FS Shirt" if _has_any(fs_keywords, name_str) else "HS Shirt"

    return "Others"
