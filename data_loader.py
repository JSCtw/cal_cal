import pandas as pd

class DataLoader:
    def __init__(self, file_path="Nutrition_Facts.xlsx"):
        """
        初始化 DataLoader。

        Args:
            file_path (str, optional): Excel 檔案的路徑。
                                       預設為 "Nutrition_Facts.xlsx"。
        """
        self.file_path = file_path
        try:
            # 載入品牌別名 (Brands_Alias)
            # Excel 欄位: Brand_Alias_Name, Brand_Standard_Name
            self.brands_alias = self.load_alias(
                sheet_name="Brands_Alias",
                alias_col_name="Brand_Alias_Name",
                standard_col_name="Brand_Standard_Name"
            )

            # 載入容量別名 (Size_Alias)
            # Excel 欄位: Size_Alias, Size
            self.size_alias = self.load_alias(
                sheet_name="Size_Alias",
                alias_col_name="Size_Alias",
                standard_col_name="Size"
            )

            # 載入飲品別名 (Drinks_Alias)
            # Excel 欄位: Brand_Standard_Name, Alias_Drinks_Name, Standard_Drinks_Name
            self.drinks_alias = self.load_drink_alias("Drinks_Alias")

            # 載入主要的 DataFrame
            self.drinks_df = pd.read_excel(self.file_path, sheet_name="Drinks", engine="openpyxl")
            self.toppings_df = pd.read_excel(self.file_path, sheet_name="Toppings", engine="openpyxl")
            self.sweet_setting = pd.read_excel(self.file_path, sheet_name="sweet_setting", engine="openpyxl")

            # --- 加入以下除錯打印 START ---
            print("\n--- [DataLoader 除錯] 已載入的別名詞典內容 ---")
            print("品牌別名 (self.brands_alias):")
            if self.brands_alias:
                for k, v in self.brands_alias.items():
                    print(f"  鍵: '{k}' (類型: {type(k)}) -> 值: '{v}' (類型: {type(v)})")
            else:
                print("  品牌別名詞典為空或未載入。")

            print("\n飲品別名 (self.drinks_alias):")
            if self.drinks_alias:
                for k_tuple, v_drink in self.drinks_alias.items():
                    if isinstance(k_tuple, tuple) and len(k_tuple) == 2:
                        k0_type = type(k_tuple[0])
                        k1_type = type(k_tuple[1])
                        print(f"  鍵: ('{k_tuple[0]}' (類型: {k0_type}), '{k_tuple[1]}' (類型: {k1_type})) -> 值: '{v_drink}' (類型: {type(v_drink)})")
                    else:
                        print(f"  飲品別名中出現非預期的鍵格式: {k_tuple}")
            else:
                print("  飲品別名詞典為空或未載入。")

            # data_loader.py, __init__ 方法的除錯打印區域
            # ... (打印 brands_alias 和 drinks_alias 的程式碼之後) ...
            print("\n容量別名 (self.size_alias):")
            if self.size_alias:
                for k, v in self.size_alias.items():
                     print(f"  鍵: '{k}' (類型: {type(k)}) -> 值: '{v}' (類型: {type(v)})")
            else:
                 print("  容量別名詞典為空或未載入。")
                           
            print("--- [DataLoader 除錯] 結束 ---\n")
            # --- 加入除錯打印 END ---

            # print("[DataLoader] 所有資料已成功載入。")

        except FileNotFoundError:
            print(f"[DataLoader錯誤] 找不到 Excel 檔案於: {self.file_path}")
            raise
        except KeyError as e:
            print(f"[DataLoader錯誤] 其中一個 Excel 工作表的欄位名稱未找到: {e}")
            print("請確保 Excel 中的欄位名稱與 DataLoader 中預期的名稱完全一致。")
            raise
        except Exception as e:
            print(f"[DataLoader錯誤] 資料載入過程中發生未預期的錯誤: {e}")
            raise

    def load_alias(self, sheet_name, alias_col_name, standard_col_name):
        """通用載入別名工作表，將別名欄位對應到標準欄位。"""
        try:
            df = pd.read_excel(self.file_path, sheet_name=sheet_name, engine="openpyxl")
            if alias_col_name not in df.columns:
                raise KeyError(f"工作表 '{sheet_name}' 中找不到欄位 '{alias_col_name}'。找到的欄位有: {df.columns.tolist()}")
            if standard_col_name not in df.columns:
                raise KeyError(f"工作表 '{sheet_name}' 中找不到欄位 '{standard_col_name}'。找到的欄位有: {df.columns.tolist()}")
            return {
                str(row[alias_col_name]).strip(): str(row[standard_col_name]).strip()
                for _, row in df.iterrows()
            }
        except Exception as e:
            print(f"[DataLoader錯誤] 載入別名工作表 '{sheet_name}' 時發生錯誤: {e}")
            raise

    def load_drink_alias(self, sheet_name):
        """載入飲品別名工作表，處理單一儲存格中可能存在的多個別名（以逗號分隔）。"""
        drink_aliases_map = {}
        try:
            df = pd.read_excel(self.file_path, sheet_name=sheet_name, engine="openpyxl")
            expected_cols = ["Brand_Standard_Name", "Alias_Drinks_Name", "Standard_Drinks_Name"]
            for col in expected_cols:
                if col not in df.columns:
                    raise KeyError(f"工作表 '{sheet_name}' 中找不到欄位 '{col}'。找到的欄位有: {df.columns.tolist()}")

            for _, row in df.iterrows():
                brand_std_name = str(row["Brand_Standard_Name"]).strip()
                standard_drink_name = str(row["Standard_Drinks_Name"]).strip()
                aliases_string = str(row["Alias_Drinks_Name"]).strip()
                individual_aliases = aliases_string.split(',')
                for alias in individual_aliases:
                    cleaned_alias = alias.strip()
                    if cleaned_alias:
                        lookup_key = (brand_std_name, cleaned_alias)
                        drink_aliases_map[lookup_key] = standard_drink_name
            return drink_aliases_map
        except Exception as e:
            print(f"[DataLoader錯誤] 載入飲品別名工作表 '{sheet_name}' 時發生錯誤: {e}")
            raise

    # --- Getter 方法 ---
    def get_brands_alias(self):
        return self.brands_alias

    def get_size_alias(self):
        return self.size_alias

    def get_drinks_alias(self):
        return self.drinks_alias

    def get_drinks_dataframe(self):
        return self.drinks_df

    def get_toppings_dataframe(self):
        return self.toppings_df

    def get_sweet_settings_dataframe(self):
        return self.sweet_setting
