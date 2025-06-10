# input_parser.py
import re
from config import DEFAULT_SIZE, DEFAULT_ICE, ICE_OPTIONS

class UserInputParser:
    def __init__(self, data_loader):
        self.data_loader = data_loader
        self.brands_alias_map = data_loader.get_brands_alias_map()
        self.drinks_alias_map = data_loader.get_drinks_alias_map()
        self.size_alias_map = data_loader.get_size_alias_map()

    def parse(self, user_input: str) -> dict:
        words = user_input.strip().split()
        if not words:
            return {"error": "輸入為空"}

        # 1. 解析品牌 (必定是第一個詞)
        brand_alias = words[0]
        identified_brand = self.brands_alias_map.get(brand_alias)
        if not identified_brand:
            return {"error": "找不到品牌"}

        # 2. 解析飲品 (必定是第二個詞)
        drink_alias = words[1]
        lookup_key = (identified_brand, drink_alias)
        identified_drink = self.drinks_alias_map.get(lookup_key)
        if not identified_drink:
            # 如果別名找不到，嘗試將其作為標準名稱
            drinks_df = self.data_loader.get_drinks_dataframe()
            # 確保比較時類型一致
            if drink_alias in drinks_df['Standard_Drinks_Name'].astype(str).values:
                identified_drink = drink_alias
            else:
                return {"error": "找不到飲品"}

        # 3. 解析其他規格
        identified_size = DEFAULT_SIZE
        identified_ice = DEFAULT_ICE
        identified_sweetness = None
        identified_toppings = []

        # 解析尺寸
        for alias, std_size in self.size_alias_map.items():
            if alias in user_input:
                identified_size = std_size
                break

        # 解析冰量
        for alias, std_ice in ICE_OPTIONS.items():
            if alias in user_input:
                identified_ice = std_ice
                break
        
        # 解析甜度
        sweetness_df = self.data_loader.get_sweet_settings_dataframe()
        for sweet_level in sweetness_df['甜度'].unique():
            if str(sweet_level) in user_input:
                identified_sweetness = str(sweet_level)
                break
        
        # 解析配料
        toppings_df = self.data_loader.get_toppings_dataframe()
        for topping_name in toppings_df['Topping_Name'].unique():
            if f"+{topping_name}" in user_input:
                 identified_toppings.append(topping_name)

        return {
            "brand": identified_brand,
            "drink": identified_drink,
            "size": identified_size,
            "ice": identified_ice,
            "sweetness": identified_sweetness,
            "toppings": identified_toppings,
        }