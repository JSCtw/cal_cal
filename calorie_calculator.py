# calorie_calculator.py (防呆增強版)
import pandas as pd
import numpy as np # 匯入 numpy 來處理 NaN

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
            print(f"[Calculator] 查無基礎飲品， parsed_input: {parsed_input}")
            return None

        try:
            # --- 關鍵修改：增加對空值(NaN)的處理和類型轉換的保護 ---
            base_calories = pd.to_numeric(base_drink_row.get('熱量'), errors='coerce')
            base_sugar = pd.to_numeric(base_drink_row.get('糖量'), errors='coerce')

            # 如果轉換失敗或值為空，則設為 0
            final_calories = 0.0 if pd.isna(base_calories) else float(base_calories)
            final_sugar = 0.0 if pd.isna(base_sugar) else float(base_sugar)
            
            print(f"[Calculator] 基礎營養素: 熱量={final_calories}, 糖量={final_sugar}")
            
            # --- 甜度調整 ---
            sweetness_multiplier = 1.0
            if parsed_input["sweetness"]:
                sweet_df = self.data_loader.get_sweet_settings_dataframe()
                sweet_row = sweet_df[sweet_df['甜度'].astype(str) == parsed_input["sweetness"]]
                if not sweet_row.empty:
                    multiplier_val = pd.to_numeric(sweet_row.iloc[0]['公式'], errors='coerce')
                    if not pd.isna(multiplier_val):
                        sweetness_multiplier = float(multiplier_val)

            original_sugar_calories = final_sugar * 4
            adjusted_sugar = final_sugar * sweetness_multiplier
            final_calories = final_calories - original_sugar_calories + (adjusted_sugar * 4)
            final_sugar = adjusted_sugar
            print(f"[Calculator] 甜度調整後: 熱量={final_calories}, 糖量={final_sugar}")

            # --- 配料疊加 ---
            if parsed_input["toppings"]:
                toppings_df = self.data_loader.get_toppings_dataframe()
                for topping_name in parsed_input["toppings"]:
                    topping_row = toppings_df[toppings_df['Topping_Name'] == topping_name]
                    if not topping_row.empty:
                        topping_calories = pd.to_numeric(topping_row.iloc[0]['熱量'], errors='coerce')
                        topping_sugar = pd.to_numeric(topping_row.iloc[0]['糖量'], errors='coerce')

                        if not pd.isna(topping_calories):
                            final_calories += float(topping_calories)
                        if not pd.isna(topping_sugar):
                            final_sugar += float(topping_sugar)
            print(f"[Calculator] 配料疊加後: 熱量={final_calories}, 糖量={final_sugar}")

            return {"calories": round(final_calories), "sugar": round(final_sugar, 1)}

        except Exception as e:
            # 加入詳細的錯誤日誌，以便我們知道是哪一步出錯
            print(f"[Calculator ERROR] 在計算過程中發生嚴重錯誤: {e}")
            import traceback
            traceback.print_exc()
            return None # 返回 None，讓 app.py 知道計算失敗