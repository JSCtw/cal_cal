# calorie_calculator.py
import pandas as pd
import re

class CalorieCalculator:
    def __init__(self, data_loader):
        self.data_loader = data_loader

    def _get_drink_row(self, brand: str, drink: str, size: str, ice: str):
        drinks_df = self.data_loader.get_drinks_dataframe()
        condition = (
            (drinks_df['Brand_Standard_Name'] == brand) &
            (drinks_df['Standard_Drinks_Name'] == drink) &
            (drinks_df['Size'] == size) &
            (drinks_df['冰量'] == ice)
        )
        result = drinks_df[condition]
        if not result.empty:
            return result.iloc[0]
        if ice == 'H':
            condition_fallback = (
                (drinks_df['Brand_Standard_Name'] == brand) &
                (drinks_df['Standard_Drinks_Name'] == drink) &
                (drinks_df['Size'] == size) & (drinks_df['冰量'] == 'I')
            )
            result_fallback = drinks_df[condition_fallback]
            if not result_fallback.empty:
                return result_fallback.iloc[0]
        return None

    def calculate(self, parsed_input: dict) -> dict | None:
        base_drink_row = self._get_drink_row(
            parsed_input["brand"], parsed_input["drink"],
            parsed_input["size"], parsed_input["ice"]
        )
        if base_drink_row is None:
            return None

        try:
            base_calories = float(pd.to_numeric(base_drink_row.get('熱量'), errors='coerce'))
            base_sugar = float(pd.to_numeric(base_drink_row.get('糖量'), errors='coerce'))

            final_calories = base_calories
            final_sugar = base_sugar
            
            # 甜度調整
            sweetness_level = parsed_input.get("sweetness")
            if sweetness_level:
                category = "清心福全" if parsed_input["brand"] == "清心福全" else "一般"
                sweet_df = self.data_loader.get_sweet_settings_dataframe()
                condition = (
                    (sweet_df['甜度'].astype(str) == sweetness_level) &
                    (sweet_df['類別'].astype(str) == category)
                )
                sweet_rule = sweet_df[condition]

                if not sweet_rule.empty:
                    formula = str(sweet_rule.iloc[0]['公式']).strip()
                    if "糖量" in formula:
                        match = re.search(r'([\d.]+)\s*%', formula)
                        if match:
                            percentage_to_remove = float(match.group(1)) / 100.0
                            
                            sugar_to_remove = base_sugar * percentage_to_remove
                            calories_to_remove = sugar_to_remove * 4
                            
                            final_sugar -= sugar_to_remove
                            final_calories -= calories_to_remove
                    # 如果公式是"熱量"或其他格式，則不進行調整，維持全糖值

            # 1. 現有的加配料邏輯 (完全不變)
            if parsed_input["toppings"]:
                toppings_df = self.data_loader.get_toppings_dataframe()
                for topping_name in parsed_input["toppings"]:
                    topping_row = toppings_df[toppings_df['Topping_Name'] == topping_name]
                    if not topping_row.empty:
                        final_calories += float(topping_row.iloc[0]['熱量'])
                        final_sugar += float(topping_row.iloc[0]['糖量'])

            # 2.【新增】減配料邏輯
            if parsed_input.get("removed_toppings"):
                toppings_df = self.data_loader.get_toppings_dataframe() # 可以重複使用
                for topping_name in parsed_input["removed_toppings"]:
                    topping_row = toppings_df[toppings_df['Topping_Name'] == topping_name]
                    if not topping_row.empty:
                        final_calories -= float(topping_row.iloc[0]['熱量'])
                        final_sugar -= float(topping_row.iloc[0]['糖量'])

            # 3.【新增】保護機制，防止熱量/糖量變為負數
            final_calories = max(0, final_calories)
            final_sugar = max(0, final_sugar)

            return {"calories": round(final_calories), "sugar": round(final_sugar, 1)}

        except Exception as e:
            print(f"[Calculator ERROR] 計算過程中發生錯誤: {e}")
            import traceback
            traceback.print_exc()
            return None