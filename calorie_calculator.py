# calorie_calculator.py
import pandas as pd

class CalorieCalculator:
    def __init__(self, data_loader):
        self.data_loader = data_loader

    def _get_drink_row(self, brand: str, drink: str, size: str, ice: str):
        # ... (這個函式不變) ...
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
        # ... (前面的 base_drink_row 查找不變) ...
        base_drink_row = self._get_drink_row(
            parsed_input["brand"], parsed_input["drink"],
            parsed_input["size"], parsed_input["ice"]
        )
        if base_drink_row is None:
            print(f"[Calculator] 查無基礎飲品， parsed_input: {parsed_input}")
            return None

        try:
            base_calories = pd.to_numeric(base_drink_row.get('熱量'), errors='coerce')
            base_sugar = pd.to_numeric(base_drink_row.get('糖量'), errors='coerce')

            final_calories = 0.0 if pd.isna(base_calories) else float(base_calories)
            final_sugar = 0.0 if pd.isna(base_sugar) else float(base_sugar)
            
            # --- 甜度調整除錯 ---
            sweetness_multiplier = 1.0
            parsed_sweetness = parsed_input.get("sweetness")
            print(f"[Calculator-DEBUG] 開始調整甜度。解析到的甜度為: '{parsed_sweetness}' (類型: {type(parsed_sweetness)})")

            if parsed_sweetness:
                sweet_df = self.data_loader.get_sweet_settings_dataframe()
                # 使用 .strip() 確保比對時沒有多餘空格
                sweet_row = sweet_df[sweet_df['甜度'].astype(str).str.strip() == parsed_sweetness]
                
                if not sweet_row.empty:
                    multiplier_val = pd.to_numeric(sweet_row.iloc[0]['公式'], errors='coerce')
                    if not pd.isna(multiplier_val):
                        sweetness_multiplier = float(multiplier_val)
                        print(f"[Calculator-DEBUG] 找到甜度設定，使用的乘數為: {sweetness_multiplier}")
                else:
                    print(f"[Calculator-DEBUG] 在 sweet_setting.csv 中找不到甜度 '{parsed_sweetness}' 的設定。")
            
            # ... (後續計算不變) ...
            original_sugar_calories = final_sugar * 4
            adjusted_sugar = final_sugar * sweetness_multiplier
            final_calories = final_calories - original_sugar_calories + (adjusted_sugar * 4)
            final_sugar = adjusted_sugar
            
            if parsed_input["toppings"]:
                # ...
                pass
            
            # ... (配料疊加邏輯不變) ...
            if parsed_input["toppings"]:
                toppings_df = self.data_loader.get_toppings_dataframe()
                for topping_name in parsed_input["toppings"]:
                    topping_row = toppings_df[toppings_df['Topping_Name'] == topping_name]
                    if not topping_row.empty:
                        final_calories += float(topping_row.iloc[0]['熱量'])
                        final_sugar += float(topping_row.iloc[0]['糖量'])

            return {"calories": round(final_calories), "sugar": round(final_sugar, 1)}

        except Exception as e:
            print(f"[Calculator ERROR] 在計算過程中發生嚴重錯誤: {e}")
            import traceback
            traceback.print_exc()
            return None