# calorie_calculator.py
import pandas as pd

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
        if base_drink_row is None: return None

        final_calories = float(base_drink_row['熱量'])
        final_sugar = float(base_drink_row['糖量'])

        sweetness_multiplier = 1.0
        if parsed_input["sweetness"]:
            sweet_df = self.data_loader.get_sweet_settings_dataframe()
            sweet_row = sweet_df[sweet_df['甜度'].astype(str) == parsed_input["sweetness"]]
            if not sweet_row.empty:
                sweetness_multiplier = float(sweet_row.iloc[0]['公式'])
        
        original_sugar_calories = final_sugar * 4
        adjusted_sugar = final_sugar * sweetness_multiplier
        final_calories = final_calories - original_sugar_calories + (adjusted_sugar * 4)
        final_sugar = adjusted_sugar
        
        if parsed_input["toppings"]:
            toppings_df = self.data_loader.get_toppings_dataframe()
            for topping_name in parsed_input["toppings"]:
                topping_row = toppings_df[toppings_df['Topping_Name'] == topping_name]
                if not topping_row.empty:
                    final_calories += float(topping_row.iloc[0]['熱量'])
                    final_sugar += float(topping_row.iloc[0]['糖量'])
        return {"calories": round(final_calories), "sugar": round(final_sugar, 1)}