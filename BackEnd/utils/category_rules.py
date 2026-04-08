import pandas as pd

CATEGORY_MAPPING = {
    'Boxer': ['boxer'],
    'Tank Top': ['tank top', 'tanktop', 'tank', 'top'],
    'Jeans': ['jeans'],
    'Denim Shirt': ['denim'],
    'Flannel Shirt': ['flannel'],
    'Polo Shirt': ['polo'],
    'Panjabi': ['panjabi', 'punjabi'],
    'Trousers': ['trousers', 'pant', 'cargo', 'trouser', 'joggers', 'track pant', 'jogger'],
    'Twill Chino': ['twill chino'],
    'Mask': ['mask'],
    'Water Bottle': ['water bottle'],
    'Contrast Shirt': ['contrast'],
    'Turtleneck': ['turtleneck', 'mock neck'],
    'Drop Shoulder': ['drop', 'shoulder'],
    'Wallet': ['wallet'],
    'Kaftan Shirt': ['kaftan'],
    'Active Wear': ['active wear'],
    'Jersy': ['jersy'],
    'Sweatshirt': ['sweatshirt', 'hoodie', 'pullover'],
    'Jacket': ['jacket', 'outerwear', 'coat'],
    'Belt': ['belt'],
    'Sweater': ['sweater', 'cardigan', 'knitwear'],
    'Passport Holder': ['passport holder'],
    'Cap': ['cap'],
    'Leather Bag': ['bag', 'backpack'],
}

def get_product_category(name: str) -> str:
    """Expert rule-based categorization for DEEN products."""
    if not name or not isinstance(name, str):
        return "Others"
        
    name_str = name.lower()
    for cat, keywords in CATEGORY_MAPPING.items():
        if any(kw.lower() in name_str for kw in keywords):
            return cat
    
    # Special handling for T-Shirts and Shirts (Sleeve Logic)
    fs_keywords = ['full sleeve', 'long sleeve', 'fs', 'l/s']
    is_fs = any(kw in name_str for kw in fs_keywords)
    
    if any(kw in name_str for kw in ['t-shirt', 't shirt', 'tee']):
        return 'FS T-Shirt' if is_fs else 'T-Shirt'
    if 'shirt' in name_str:
        return 'FS Shirt' if is_fs else 'HS Shirt'
        
    return 'Others'

def apply_category_expert_rules(df: pd.DataFrame, name_col: str = "item_name") -> pd.DataFrame:
    """Applies the mapping to a dataframe and adds a 'Category' column."""
    if df.empty or name_col not in df.columns:
        return df
    df['Category'] = df[name_col].apply(get_product_category)
    return df
