# data_loader.py (已更新為讀取 CSV)
import pandas as pd
import os # 匯入 os 模組來組合路徑

class DataLoader:
    def __init__(self, data_folder="data"):
        self.data_folder = data_folder
        try:
            # 定義所有 CSV 檔案的路徑
            drinks_path = os.path.join(self.data_folder, "drinks.csv")
            toppings_path = os.path.join(self.data_folder, "toppings.csv")
            sweet_setting_path = os.path.join(self.data_folder, "sweet_setting.csv")
            brands_alias_path = os.path.join(self.data_folder, "brands_alias.csv")
            size_alias_path = os.path.join(self.data_folder, "size_alias.csv")
            drinks_alias_path = os.path.join(self.data_folder, "drinks_alias.csv")

            # --- 隔離測試：一次只載入一個檔案 ---

            print("[DataLoader - DEBUG] 測試：只載入 brands_alias.csv...")
            self.brands_alias_map = self._load_alias_from_csv(brands_alias_path, "Brand_Alias_Name", "Brand_Standard_Name")
            print("[DataLoader - DEBUG] brands_alias.csv 載入成功。")

            # --- 暫時將其他 DataFrame 和 map 初始化為空的，避免程式出錯 ---
            self.drinks_df = pd.DataFrame()
            self.toppings_df = pd.DataFrame()
            self.sweet_setting_df = pd.DataFrame()
            self.size_alias_map = {}
            self.drinks_alias_map = {}

            # --- 以下為暫時註解掉的原始程式碼 ---
            # self.drinks_df = pd.read_csv(drinks_path)
            # self.toppings_df = pd.read_csv(toppings_path)
            # self.sweet_setting_df = pd.read_csv(sweet_setting_path)
            # self.size_alias_map = self._load_alias_from_csv(size_alias_path, "Size_Alias", "Size")
            # self.drinks_alias_map = self._load_drink_alias_from_csv(drinks_alias_path)

            # print("[DataLoader] 所有 CSV 資料已成功載入。")
        except Exception as e:
            print(f"[DataLoader錯誤] 資料載入過程中發生錯誤: {e}")
            raise

    def _load_alias_from_csv(self, file_path, alias_col, standard_col):
        df = pd.read_csv(file_path)
        alias_map = {}
        for _, row in df.iterrows():
            alias_map[str(row[alias_col]).strip()] = str(row[standard_col]).strip()
        return alias_map

    def _load_drink_alias_from_csv(self, file_path):
        df = pd.read_csv(file_path)
        drink_aliases_map = {}
        for _, row in df.iterrows():
            brand_std_name = str(row["Brand_Standard_Name"]).strip()
            standard_drink_name = str(row["Standard_Drinks_Name"]).strip()
            if pd.notna(row["Alias_Drinks_Name"]):
                aliases_string = str(row["Alias_Drinks_Name"]).strip()
                individual_aliases = aliases_string.split(',')
                for alias in individual_aliases:
                    cleaned_alias = alias.strip()
                    if cleaned_alias:
                        lookup_key = (brand_std_name, cleaned_alias)
                        drink_aliases_map[lookup_key] = standard_drink_name
        return drink_aliases_map

    # --- Getter 方法 (保持不變) ---
    def get_drinks_dataframe(self): return self.drinks_df
    def get_toppings_dataframe(self): return self.toppings_df
    def get_sweet_settings_dataframe(self): return self.sweet_setting_df
    def get_brands_alias_map(self): return self.brands_alias_map
    def get_size_alias_map(self): return self.size_alias_map
    def get_drinks_alias_map(self): return self.drinks_alias_map