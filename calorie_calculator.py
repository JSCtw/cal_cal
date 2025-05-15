# calorie_calculator.py
import pandas as pd
import re # 導入正則表達式模組

class CalorieCalculator:
    def __init__(self, data_loader): # <<--- 確保 __init__ 方法接收 data_loader 參數
        """
        初始化 CalorieCalculator。

        Args:
            data_loader: DataLoader 的實例，提供對飲品、配料、甜度設定等資料的存取。
        """
        self.data_loader = data_loader
        # 建議在需要時才透過 getter 方法獲取 DataFrame，以確保獲取的是最新狀態
        # 例如: self.data_loader.get_drinks_dataframe()

    def get_drink_row(self, brand: str, drink_name: str, size: str, ice: str) -> pd.Series | None:
        """
        根據品牌、飲品名稱、容量和冰量從 drinks_df 中獲取飲品資料列。
        如果請求的是熱飲 (ice='H') 但找不到，則嘗試查找冰飲 (ice='I') 作為回退。
        返回找到的第一筆符合條件的飲品資料 (Pandas Series)，如果找不到則返回 None。
        """
        df = self.data_loader.get_drinks_dataframe()
        if df is None or df.empty:
            print("[CalorieCalculator錯誤] Drinks DataFrame 未載入或為空。")
            return None

        # --- 除錯打印 START ---
        print(f"\n--- [CalorieCalculator 除錯] 進入 get_drink_row ---")
        print(f"  傳入參數:")
        print(f"    brand: '{brand}' (類型: {type(brand)})")
        print(f"    drink_name (Standard_Drinks_Name): '{drink_name}' (類型: {type(drink_name)})")
        print(f"    size: '{size}' (類型: {type(size)})")
        print(f"    ice (請求的代碼): '{ice}' (類型: {type(ice)})")

        # Drinks 工作表中用於篩選的欄位名稱
        brand_col = "Brand_Standard_Name"
        drink_name_col = "Standard_Drinks_Name"
        size_col = "Size"
        ice_col = "冰量"

        print(f"  使用的篩選欄位: brand='{brand_col}', drink='{drink_name_col}', size='{size_col}', ice='{ice_col}'")

        # 檢查必要的欄位是否存在於 DataFrame 中
        required_cols_in_df = [brand_col, drink_name_col, size_col, ice_col]
        for r_col in required_cols_in_df:
            if r_col not in df.columns:
                print(f"  [CalorieCalculator錯誤] Drinks DataFrame 中找不到必要的欄位: '{r_col}'。可用的欄位有: {df.columns.tolist()}")
                print(f"--- [CalorieCalculator 除錯] 離開 get_drink_row (因欄位缺失) ---\n")
                return None
        
        # 初始篩選 (不含冰量)
        try:
            condition_base = (
                (df[brand_col].astype(str).str.strip() == str(brand).strip()) &
                (df[drink_name_col].astype(str).str.strip() == str(drink_name).strip()) &
                (df[size_col].astype(str).str.strip() == str(size).strip())
            )
            filtered_df = df[condition_base]
        except Exception as e:
            print(f"  [CalorieCalculator錯誤] 初始篩選 (品牌、品名、容量) 時發生錯誤: {e}")
            print(f"--- [CalorieCalculator 除錯] 離開 get_drink_row (因篩選錯誤) ---\n")
            return None

        print(f"  初始篩選 (品牌、品名、容量) 後找到的記錄數量: {len(filtered_df)}")
        if not filtered_df.empty:
            print(f"  符合品牌、品名、容量的記錄 (顯示冰量欄 '{ice_col}'):\n{filtered_df[[ice_col]]}")
        else:
            print(f"  未找到符合品牌 '{brand}', 品名 '{drink_name}', 容量 '{size}' 的飲品。")
            print(f"--- [CalorieCalculator 除錯] 離開 get_drink_row (因初始篩選無結果) ---")
            return None

        # --- 根據冰量進行二次篩選，加入回退邏輯 ---
        drink_row_df = pd.DataFrame() # 初始化為空的 DataFrame

        if ice == "H":
            print(f"  [冰量篩選] 請求的是熱飲 (H)。嘗試查找冰量為 'H' 的記錄...")
            condition_hot = (filtered_df[ice_col].astype(str).str.strip() == "H")
            drink_row_df = filtered_df[condition_hot]
            print(f"    篩選 'H' 後找到的記錄數量: {len(drink_row_df)}")

            if drink_row_df.empty:
                print(f"  [get_drink_row 回退邏輯] 未找到冰量為 'H' 的記錄，嘗試查找冰量為 'I' 的記錄作為替代...")
                condition_iced_fallback = (filtered_df[ice_col].astype(str).str.strip() == "I")
                drink_row_df = filtered_df[condition_iced_fallback]
                if not drink_row_df.empty:
                    print(f"    回退查找冰量 'I' 後找到的記錄數量: {len(drink_row_df)}")
                    print(f"    警告：將使用冰量為 'I' 的資料計算熱飲熱量。")
                else:
                    print(f"    回退查找冰量 'I' 也未找到記錄。")
        else: # 如果請求的 ice 本身就是 "I" 或其他非 "H" 的特定冰量代碼
            print(f"  [冰量篩選] 請求的冰量為 '{ice}'。嘗試查找對應記錄...")
            condition_specific_ice = (filtered_df[ice_col].astype(str).str.strip() == str(ice).strip())
            drink_row_df = filtered_df[condition_specific_ice]
            print(f"    篩選 '{ice}' 後找到的記錄數量: {len(drink_row_df)}")

        if not drink_row_df.empty:
            print(f"  最終篩選後找到的記錄:\n{drink_row_df.iloc[[0]]}") # 打印第一條找到的記錄
        else:
            print(f"  在符合基本條件的飲品中，未找到冰量為 '{ice}' (或其回退選項) 的記錄。")
        
        print(f"--- [CalorieCalculator 除錯] 離開 get_drink_row ---\n")
        # --- 除錯打印 END ---

        if drink_row_df.empty:
            return None
        return drink_row_df.iloc[0] # 返回第一筆匹配的記錄 (Pandas Series)

    def adjust_sweetness(self, total_cal: float, sugar_g: float, brand: str, sweetness_level: str | None) -> float:
        """根據甜度調整熱量，使用正則表達式解析公式。"""
        if sweetness_level is None:
            print("[CalorieCalculatorInfo] 未提供甜度資訊，熱量不調整。")
            return total_cal

        sweet_df = self.data_loader.get_sweet_settings_dataframe()
        if sweet_df is None or sweet_df.empty:
            print("[CalorieCalculatorWarning] 甜度設定 DataFrame 未載入或為空，熱量不調整。")
            return total_cal

        # Excel `sweet_setting` 工作表預期欄位: "甜度", "類別", "公式"
        expected_sweet_cols = ["甜度", "類別", "公式"]
        for col in expected_sweet_cols:
            if col not in sweet_df.columns:
                print(f"[CalorieCalculatorWarning] 甜度設定 DataFrame 中找不到欄位 '{col}'，熱量不調整。")
                return total_cal
        
        category = "清心福全" if brand == "清心福全" else "一般" # 此分類邏輯可能需依您的 Excel 調整
        
        print(f"  [甜度調整] 品牌: '{brand}', 甜度級別: '{sweetness_level}', 分類: '{category}'")

        row_series_df = sweet_df[
            (sweet_df["甜度"].astype(str).str.strip() == str(sweetness_level).strip()) &
            (sweet_df["類別"].astype(str).str.strip() == str(category).strip())
        ]

        if row_series_df.empty:
            print(f"  [甜度調整] 未找到甜度級別 '{sweetness_level}' 和分類 '{category}' 的對應設定，熱量不調整。")
            return total_cal

        formula_str = str(row_series_df.iloc[0]["公式"]).strip()
        print(f"  [甜度調整] 找到公式: '{formula_str}'")

        # 定義通用的熱量和糖量關鍵字 (來自您 Excel 中的公式)
        calorie_keyword = "熱量" # 您 Excel 公式中代表基礎熱量的詞
        sugar_keyword = "糖量"   # 您 Excel 公式中代表基礎糖量的詞

        try:
            if not formula_str or formula_str.lower() == "no_change":
                print("  [甜度調整] 公式為 'no_change' 或空，熱量不調整。")
                return total_cal

            # 模式1: 熱量 - 糖量 * 百分比% * 因子 (例如 "熱量-糖量*42.5%*4")
            match_sugar_reduction = re.fullmatch(
                rf"{calorie_keyword}\s*-\s*{sugar_keyword}\s*\*\s*([\d.]+)\s*%\s*\*\s*([\d.]+)", 
                formula_str, 
                flags=re.IGNORECASE # 忽略大小寫以增加彈性
            )
            if match_sugar_reduction:
                percentage_str = match_sugar_reduction.group(1)
                factor_str = match_sugar_reduction.group(2)
                try:
                    ratio = float(percentage_str) / 100
                    factor = float(factor_str)
                    calories_to_reduce_from_sugar = sugar_g * ratio * factor
                    adjusted_cal = total_cal - calories_to_reduce_from_sugar
                    print(f"  [甜度調整] 依公式 '{formula_str}' 計算：減少 {calories_to_reduce_from_sugar:.1f} 大卡，調整後熱量: {adjusted_cal:.1f}")
                    return adjusted_cal
                except ValueError:
                    print(f"  [甜度調整警告] 公式 '{formula_str}' 中的百分比或因子無法轉換為數字，熱量不調整。")
                    return total_cal

            # 模式2: 熱量 * 百分比% (例如 "熱量*70%")
            match_calorie_percentage = re.fullmatch(
                rf"{calorie_keyword}\s*\*\s*([\d.]+)\s*%", 
                formula_str,
                flags=re.IGNORECASE
            )
            if match_calorie_percentage:
                percentage_str = match_calorie_percentage.group(1)
                try:
                    ratio = float(percentage_str) / 100
                    adjusted_cal = total_cal * ratio
                    print(f"  [甜度調整] 依熱量百分比調整 ({float(percentage_str):.1f}%)，調整後熱量: {adjusted_cal:.1f}")
                    return adjusted_cal
                except ValueError:
                    print(f"  [甜度調整警告] 公式 '{formula_str}' 中的百分比無法轉換為數字，熱量不調整。")
                    return total_cal
            
            # 模式3: 熱量 - 固定值 (例如 "熱量-30")
            match_calorie_fixed_reduction = re.fullmatch(
                rf"{calorie_keyword}\s*-\s*([\d.]+)", 
                formula_str,
                flags=re.IGNORECASE
            )
            if match_calorie_fixed_reduction:
                reduction_val_str = match_calorie_fixed_reduction.group(1)
                try:
                    reduction_val = float(reduction_val_str)
                    adjusted_cal = total_cal - reduction_val
                    print(f"  [甜度調整] 依熱量固定值減少 ({reduction_val:.1f})，調整後熱量: {adjusted_cal:.1f}")
                    return adjusted_cal
                except ValueError:
                    print(f"  [甜度調整警告] 公式 '{formula_str}' 中的減少值無法轉換為數字，熱量不調整。")
                    return total_cal

            print(f"  [甜度調整] 無法識別的公式格式 (未匹配任何已知模式): '{formula_str}'，熱量不調整。")
            return total_cal
        
        except Exception as e:
            print(f"  [甜度調整錯誤] 解析或計算公式 '{formula_str}' 時發生通用錯誤: {e}，熱量不調整。")
            return total_cal

    def calc_toppings_calories(self, toppings_list: list) -> float:
        """計算配料的總熱量。"""
        total_topping_cal = 0.0
        toppings_data_df = self.data_loader.get_toppings_dataframe()

        if toppings_data_df is None or toppings_data_df.empty:
            print("[CalorieCalculatorWarning] 配料 DataFrame 未載入或為空，配料熱量計為 0。")
            return 0.0

        # Toppings 工作表預期欄位: "Topping_Name", "熱量"
        topping_name_col = "Topping_Name"
        calories_col = "熱量"

        if topping_name_col not in toppings_data_df.columns or calories_col not in toppings_data_df.columns:
            print(f"[CalorieCalculatorWarning] 配料 DataFrame 中缺少 '{topping_name_col}' 或 '{calories_col}' 欄位，配料熱量計為 0。")
            return 0.0

        print(f"  [配料計算] 接收到的配料列表: {toppings_list}")
        for item_dict in toppings_list:
            name = item_dict["name"]
            quantity = item_dict["quantity"]
            action = item_dict["action"]

            topping_row_df = toppings_data_df[ # 修改變數名以表示其為 DataFrame
                toppings_data_df[topping_name_col].astype(str).str.strip() == str(name).strip()
            ]

            if not topping_row_df.empty:
                try:
                    calories_per_unit = float(topping_row_df.iloc[0][calories_col])
                    current_topping_cal = calories_per_unit * quantity
                    
                    if action == "add":
                        total_topping_cal += current_topping_cal
                        print(f"    [配料計算] +{name}*{quantity}: +{current_topping_cal:.1f} 大卡")
                    elif action == "remove":
                        total_topping_cal -= current_topping_cal
                        print(f"    [配料計算] -{name}*{quantity}: -{current_topping_cal:.1f} 大卡")
                except ValueError:
                    print(f"    [配料計算警告] 配料 '{name}' 的熱量值 '{topping_row_df.iloc[0][calories_col]}' 無法轉換為數字。")
                except Exception as e:
                    print(f"    [配料計算錯誤] 處理配料 '{name}' 時發生錯誤: {e}")
            else:
                print(f"    [配料計算警告] 在配料資料中未找到配料: '{name}'")
        
        print(f"  [配料計算] 配料總熱量調整: {total_topping_cal:.1f} 大卡")
        return total_topping_cal

    def _parse_topping(self, topping_str): # 這個方法已不再被主要流程使用
        print("[CalorieCalculatorDeprecationWarning] CalorieCalculator 中的 _parse_topping 方法已棄用，其功能應由 UserInputParser 完成。")
        if "*2" in topping_str: # 非常簡陋的解析
            return topping_str.replace("*2", ""), 2
        return topping_str, 1

    def calculate_total(self, parsed_input: dict) -> tuple[float | None, str | None]:
        """
        計算總熱量。

        Args:
            parsed_input: UserInputParser 解析後的字典。

        Returns:
            元組 (總熱量, 錯誤訊息)。如果成功，錯誤訊息為 None。
        """
        if not parsed_input or not parsed_input.get("brand") or not parsed_input.get("drink"):
            return None, "輸入資訊不完整 (品牌或飲品缺失)"

        drink_row = self.get_drink_row(
            parsed_input["brand"],
            parsed_input["drink"],
            parsed_input["size"],
            parsed_input["ice"]
        )

        if drink_row is None: # get_drink_row 返回 None 表示查無此飲品
            return None, "查無此飲品"

        # 從 drink_row 提取熱量和糖量，確保欄位名與 Drinks 工作表一致
        calories_col_drinks = "熱量"
        sugar_col_drinks = "糖量"

        if calories_col_drinks not in drink_row.index: # drink_row 是 Pandas Series
            return None, f"飲品資料中缺少熱量欄位 '{calories_col_drinks}'"
        # 糖量是可選的，如果沒有，甜度調整可能按預設行為處理
        if sugar_col_drinks not in drink_row.index:
             print(f"[CalorieCalculatorWarning] 飲品資料中缺少糖量欄位 '{sugar_col_drinks}'，甜度調整可能不準確或不執行。")

        try:
            base_total_cal = float(drink_row[calories_col_drinks])
            sugar_g = float(drink_row.get(sugar_col_drinks, 0)) # 如果沒有糖量欄，預設為0
        except ValueError:
             return None, f"飲品資料中的熱量 '{drink_row.get(calories_col_drinks)}' 或糖量 '{drink_row.get(sugar_col_drinks)}' 格式不正確。"
        except Exception as e: # 更通用的例外捕捉
            return None, f"提取飲品基礎熱量或糖量時發生錯誤: {e}"

        print(f"\n[CalorieCalculator] 開始計算總熱量...")
        print(f"  基礎飲品: {parsed_input['brand']} - {parsed_input['drink']} ({parsed_input['size']}, {parsed_input['ice']})")
        print(f"  原始熱量: {base_total_cal:.1f} 大卡, 原始糖量: {sugar_g:.1f} 克")

        # 甜度調整
        adjusted_cal_after_sweetness = self.adjust_sweetness(
            base_total_cal,
            sugar_g,
            parsed_input["brand"],
            parsed_input.get("sweetness") # sweetness 可能為 None
        )
        print(f"  甜度調整後熱量: {adjusted_cal_after_sweetness:.1f} 大卡")

        # 配料熱量計算
        toppings_cal = self.calc_toppings_calories(parsed_input.get("toppings", []))
        
        final_total_cal = adjusted_cal_after_sweetness + toppings_cal
        print(f"  最終總熱量: {final_total_cal:.1f} 大卡 (甜度調整後 + 配料)")
        print(f"[CalorieCalculator] 計算結束。\n")

        return round(final_total_cal, 1), None