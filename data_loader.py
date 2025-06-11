# data_loader.py
import pandas as pd
import gspread
import os
import json

class DataLoader:
    def __init__(self, secret_key_json_str: str, sheet_name: str):
        try:
            # 將 JSON 字串解析為字典
            secret_key_dict = json.loads(secret_key_json_str)
            
            # 使用解析後的字典進行驗證
            gc = gspread.service_account_from_dict(secret_key_dict)
            spreadsheet = gc.open(sheet_name)
            
            # 讀取所有工作表並轉換為 DataFrame
            self.drinks_df = pd.DataFrame(spreadsheet.worksheet("Drinks").get_all_records())
            self.toppings_df = pd.DataFrame(spreadsheet.worksheet("Toppings").get_all_records())
            self.sweet_setting_df = pd.DataFrame(spreadsheet.worksheet("sweet_setting").get_all_records())
            
            brands_alias_data = spreadsheet.worksheet("Brands_Alias").get_all_records()
            self.brands_alias_map = {str(row["Brand_Alias_Name"]).strip(): str(row["Brand_Standard_Name"]).strip() for row in brands_alias_data}

            size_alias_data = spreadsheet.worksheet("Size_Alias").get_all_records()
            self.size_alias_map = {str(row["Size_Alias"]).strip(): str(row["Size"]).strip() for row in size_alias_data}

            drinks_alias_data = spreadsheet.worksheet("Drinks_Alias").get_all_records()
            self.drinks_alias_map = {}
            for row in drinks_alias_data:
                brand_std_name = str(row["Brand_Standard_Name"]).strip()
                standard_drink_name = str(row["Standard_Drinks_Name"]).strip()
                aliases_string = str(row.get("Alias_Drinks_Name", "")).strip()
                if aliases_string:
                    for alias in aliases_string.split(','):
                        cleaned_alias = alias.strip()
                        if cleaned_alias:
                            self.drinks_alias_map[(brand_std_name, cleaned_alias)] = standard_drink_name

            print("[DataLoader] 所有 Google Sheets 資料已成功載入。")

        except Exception as e:
            print(f"[DataLoader錯誤] 從 Google Sheets 載入資料時發生錯誤: {e}")
            raise
    
    # --- Getter 方法 ---
    def get_drinks_dataframe(self): return self.drinks_df
    def get_toppings_dataframe(self): return self.toppings_df
    def get_sweet_settings_dataframe(self): return self.sweet_setting_df
    def get_brands_alias_map(self): return self.brands_alias_map
    def get_size_alias_map(self): return self.size_alias_map
    def get_drinks_alias_map(self): return self.drinks_alias_map