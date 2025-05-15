import re
import pandas as pd # 主要用於 MockDataLoader 的類型提示，主類別不直接用

# 嘗試從 config.py 導入設定，如果失敗則使用預設值
try:
    from config import DEFAULT_SIZE, DEFAULT_ICE, ICE_OPTIONS
    CONFIG_LOADED_SUCCESS = True # 用一個不同的變數名，避免與 UserInputParser 中的搞混
except ImportError:
    CONFIG_LOADED_SUCCESS = False
    DEFAULT_SIZE = "L" # config.py 中定義的預設值
    DEFAULT_ICE = "I"  # config.py 中定義的預設值
    ICE_OPTIONS = {    # config.py 中定義的冰量選項
        "熱": "H", "温": "H", "溫": "H",
        "正常冰": "I", "正常": "I", "少冰": "I",
        "微冰": "I", "去冰": "I", "常溫": "I",
    }

class UserInputParser:
    def __init__(self, data_loader): # data_loader 應為 DataLoader 的實例
        """
        初始化 UserInputParser。

        Args:
            data_loader: DataLoader 的實例，提供別名映射和 DataFrame。
        """
        self.data_loader = data_loader

        if CONFIG_LOADED_SUCCESS:
            self.default_size = DEFAULT_SIZE
            self.default_ice = DEFAULT_ICE
            self.ice_options = ICE_OPTIONS
            # 只有在直接執行此檔案進行測試時才打印 (例如 python input_parser.py)
            if __name__ == '__main__':
                print("[ParserConfig] 成功從 config.py 載入設定。")
        else:
            self.default_size = DEFAULT_SIZE # Fallback
            self.default_ice = DEFAULT_ICE   # Fallback
            self.ice_options = ICE_OPTIONS # Fallback
            if __name__ == '__main__':
                print("[ParserConfig] config.py 未找到或常數未定義，使用內建預設值。")

        # 預處理已知的甜度級別 (使用 Excel 中的 "甜度" 欄位)
        try:
            if (self.data_loader.sweet_setting is not None and
                    "甜度" in self.data_loader.sweet_setting.columns):
                self.known_sweetness_levels = set(
                    self.data_loader.sweet_setting["甜度"].astype(str).str.strip().unique()
                )
            else:
                self.known_sweetness_levels = set()
                if __name__ == '__main__':
                    print("[ParserData] DataLoader 中未找到甜度設定或 '甜度' 欄位。")
        except Exception as e:
            self.known_sweetness_levels = set()
            if __name__ == '__main__':
                print(f"[ParserData] 準備甜度級別時發生錯誤: {e}")

        # 預處理已知的配料名稱 (使用 Excel 中的 "Topping_Name" 欄位)
        try:
            if (self.data_loader.toppings_df is not None and
                    "Topping_Name" in self.data_loader.toppings_df.columns):
                self.valid_topping_names = set(
                    self.data_loader.toppings_df["Topping_Name"].astype(str).str.strip().unique()
                )
            else:
                self.valid_topping_names = set()
                if __name__ == '__main__':
                    print("[ParserData] DataLoader 中未找到配料資料或 'Topping_Name' 欄位。")
        except Exception as e:
            self.valid_topping_names = set()
            if __name__ == '__main__':
                print(f"[ParserData] 準備配料名稱時發生錯誤: {e}")

    def _parse_topping(self, topping_str: str) -> dict | None:
        """解析單個配料字串 (例如："+珍珠*2", "-椰果")。"""
        if not topping_str or not (topping_str.startswith("+") or topping_str.startswith("-")):
            return None
        action = "add" if topping_str.startswith("+") else "remove"
        item_part = topping_str[1:]
        name = ""
        quantity = 1
        match = re.fullmatch(r"([^*]+)(?:\*(\d+))?", item_part)
        if match:
            name = match.group(1).strip()
            if match.group(2):
                try:
                    quantity = int(match.group(2))
                    if quantity <= 0:
                        print(f"[ParserWarning] 配料 '{name}' 的數量無效: {match.group(2)}。將預設為 1。")
                        quantity = 1
                except ValueError:
                    print(f"[ParserWarning] 配料 '{name}' 的數量非整數: {match.group(2)}。將預設為 1。")
                    quantity = 1
        else:
            name = item_part.strip()
        if not name:
            print(f"[ParserWarning] 從輸入中得到空的配料名稱: {topping_str}")
            return None
        if self.valid_topping_names and name not in self.valid_topping_names:
            print(f"[ParserInfo] 配料 '{name}' 不在已知的配料列表中。仍將按要求添加/移除。")
        return {"name": name, "quantity": quantity, "action": action}

    def parse_input(self, user_input: str) -> dict:
        """將使用者輸入字串解析為結構化的字典。"""
        result = {
            "brand": None, "drink": None, "sweetness": None,
            "ice": None, "size": None, "toppings": [],
        }
        if not user_input or not user_input.strip():
            print("[ParserError] 使用者輸入為空。")
            return result

        words = user_input.strip().split()
        processed_words = [False] * len(words)

        # --- 第一遍掃描 ---
        # 品牌識別
        print("\n--- [UserInputParser 除錯] 開始解析品牌 ---")
        for i, word in enumerate(words):
            if processed_words[i]:
                continue

            print(f"  [品牌檢查] 正在檢查詞語: '{word}' (類型: {type(word)})")
            # 直接使用 get 方法避免 KeyErrror，並檢查 data_loader.brands_alias 是否已初始化
            is_brand_alias_key = False
            if hasattr(self.data_loader, 'brands_alias') and self.data_loader.brands_alias is not None:
                is_brand_alias_key = word in self.data_loader.brands_alias
            
            print(f"    '{word}' 是否為 brands_alias 的鍵? {is_brand_alias_key}")
            if not is_brand_alias_key:
                if hasattr(self.data_loader, 'brands_alias') and self.data_loader.brands_alias is not None:
                    if len(self.data_loader.brands_alias) < 30:
                        print(f"    可用的品牌別名鍵 (brands_alias.keys()): {list(self.data_loader.brands_alias.keys())}")
                    else:
                        print(f"    brands_alias 字典較大(數量: {len(self.data_loader.brands_alias)})，不完全列出。請檢查 DataLoader 的除錯輸出。")
                else:
                    print(f"    brands_alias 字典未初始化或為 None。")
            
            if is_brand_alias_key:
                if result["brand"] is None:
                    result["brand"] = self.data_loader.brands_alias[word]
                    processed_words[i] = True
                    print(f"    [品牌識別成功] 品牌設定為: '{result['brand']}' (來自別名 '{word}')")
                else:
                    print(f"    [品牌警告] 已識別品牌 '{result['brand']}'，忽略後續品牌詞 '{self.data_loader.brands_alias.get(word, word)}'")
                continue 
        print("--- [UserInputParser 除錯] 品牌解析結束 ---")

        # 容量、冰量、甜度識別 (順序調整，先處理這些明確的)
        for i, word in enumerate(words):
            if processed_words[i]: continue
            # 容量
            if hasattr(self.data_loader, 'size_alias') and self.data_loader.size_alias is not None and \
               word in self.data_loader.size_alias:
                if result["size"] is None:
                    result["size"] = self.data_loader.size_alias[word]
                    processed_words[i] = True
                else: print(f"[ParserWarning] 找到多個類似容量的詞。將使用 '{result['size']}'。")
                continue
            # 冰量
            if word in self.ice_options:
                if result["ice"] is None:
                    result["ice"] = self.ice_options[word]
                    processed_words[i] = True
                else: print(f"[ParserWarning] 找到多個類似冰量的詞。將使用 '{result['ice']}'。")
                continue
            # 甜度
            if self.known_sweetness_levels and word in self.known_sweetness_levels:
                if result["sweetness"] is None:
                    result["sweetness"] = word
                    processed_words[i] = True
                else: print(f"[ParserWarning] 找到多個類似甜度的詞。將使用 '{result['sweetness']}'。")
                continue
        
        # 配料識別
        for i, word in enumerate(words):
            if processed_words[i]: continue
            if word.startswith("+") or word.startswith("-"):
                topping_data = self._parse_topping(word)
                if topping_data: result["toppings"].append(topping_data)
                processed_words[i] = True
                continue

        # --- 第二遍掃描：識別飲品名稱 ---
        print("\n--- [UserInputParser 除錯] 開始解析飲品名稱 ---")
        remaining_indices = [i for i, p_flag in enumerate(processed_words) if not p_flag]
        
        if result["brand"]:
            print(f"  [飲品檢查] 品牌已識別為: '{result['brand']}'")
            print(f"  [飲品檢查] 剩餘未處理詞的索引: {remaining_indices} (對應詞語: {[words[x] for x in remaining_indices]})")

            # 優先嘗試兩個連續的未處理詞作為飲品別名
            if len(remaining_indices) >= 2:
                print("  [飲品檢查] 嘗試雙詞飲品別名...")
                for i in range(len(remaining_indices) - 1):
                    idx1 = remaining_indices[i]
                    idx2 = remaining_indices[i+1]
                    if idx2 == idx1 + 1: # 確保在原始 split 後的 list 中是連續的
                        potential_drink_alias = f"{words[idx1]} {words[idx2]}"
                        print(f"    [飲品檢查] 嘗試雙詞組合: '{potential_drink_alias}'")
                        lookup_key = (result["brand"], potential_drink_alias)
                        if hasattr(self.data_loader, 'drinks_alias') and self.data_loader.drinks_alias is not None and \
                           lookup_key in self.data_loader.drinks_alias:
                            result["drink"] = self.data_loader.drinks_alias[lookup_key]
                            processed_words[idx1], processed_words[idx2] = True, True
                            print(f"    [飲品識別成功] 飲品(雙詞)設定為: '{result['drink']}'")
                            break 
            
            # 如果雙詞未找到，或沒有足夠的詞，則嘗試單個未處理詞作為飲品別名
            if result["drink"] is None:
                print("  [飲品檢查] 嘗試單詞飲品別名...")
                current_remaining_indices = [i for i, p_flag in enumerate(processed_words) if not p_flag] # 更新剩餘索引
                for r_idx in current_remaining_indices:
                    alias_word = words[r_idx]
                    print(f"    [飲品檢查] 嘗試單詞: '{alias_word}'")
                    lookup_key = (result["brand"], alias_word)
                    
                    # 除錯：打印 drinks_alias 中與當前品牌相關的條目
                    if hasattr(self.data_loader, 'drinks_alias') and self.data_loader.drinks_alias is not None:
                        # brand_specific_aliases = {k: v for k, v in self.data_loader.drinks_alias.items() if k[0] == result["brand"]}
                        # print(f"    [飲品檢查] 品牌 '{result['brand']}' 的可用飲品別名: {brand_specific_aliases if brand_specific_aliases else '無'}")
                        pass # 上面的打印可能過於冗長，DataLoader 的打印更集中
                    
                    if hasattr(self.data_loader, 'drinks_alias') and self.data_loader.drinks_alias is not None and \
                       lookup_key in self.data_loader.drinks_alias:
                        result["drink"] = self.data_loader.drinks_alias[lookup_key]
                        processed_words[r_idx] = True
                        print(f"    [飲品識別成功] 飲品(單詞)設定為: '{result['drink']}'")
                        break
                    else:
                        print(f"    [飲品檢查] 查找鍵 {lookup_key} 在飲品別名中未找到。")
        else:
            print("  [飲品檢查] 品牌未被識別，跳過飲品名稱解析。")
        print("--- [UserInputParser 除錯] 飲品名稱解析結束 ---")
        
        unprocessed_final = [words[i] for i, p_flag in enumerate(processed_words) if not p_flag]
        if unprocessed_final:
            print(f"[ParserInfo] 輸入中最終未處理的詞語: {unprocessed_final}")

        if result["size"] is None: result["size"] = self.default_size
        if result["ice"] is None: result["ice"] = self.default_ice
        return result

# --- 以下為簡易測試區塊 ---
if __name__ == '__main__':
    class MockDataLoader: # 用於獨立測試 UserInputParser
        def __init__(self):
            self.brands_alias = {
                "清心": "清心福全", "清心福全": "清心福全", # 標準名也作為別名
                "50嵐": "五十嵐", "五十嵐": "五十嵐",
                "一沐日": "一沐日" # 假設 "一沐日" 是標準名且作為自己的別名
            }
            self.size_alias = {"大杯": "L", "中杯": "M", "L": "L"}
            self.drinks_alias = {
                ("清心福全", "隱藏版"): "清心隱藏版",
                ("清心福全", "清心隱藏版"): "清心隱藏版", # 標準名也作為別名
                ("清心福全", "珍奶"): "珍珠奶茶",
                ("五十嵐", "四季春"): "四季春茶",
                ("五十嵐", "四季 春"): "四季春茶", # 測試雙詞
                ("一沐日", "高山青"): "高山青茶", # 測試別名
                ("一沐日", "高山青茶"): "高山青茶"  # 標準名也作為別名
            }
            self.sweet_setting = pd.DataFrame({"甜度": ["正常糖", "少糖", "半糖", "微糖", "無糖"]})
            self.toppings_df = pd.DataFrame({"Topping_Name": ["珍珠", "椰果", "波霸", "雙粉"]})
            print("[MockDataLoader] Mock DataLoader initialized with test data.")
            print("Mock Brands Alias:", self.brands_alias)
            print("Mock Drinks Alias:", self.drinks_alias)


    print("--- UserInputParser 獨立測試 ---")
    mock_loader = MockDataLoader()
    parser = UserInputParser(mock_loader)

    test_inputs = [
        "一沐日 高山青 微糖 少冰 +雙粉",
        "清心 隱藏版 微糖 少冰 +珍珠*2 -椰果",
        "五十嵐 四季 春 L 去冰 無糖",
        "清心福全 清心隱藏版 大杯 熱", # 直接用標準名
    ]

    for ti in test_inputs:
        print(f"\n--- 測試輸入: '{ti}' ---")
        parsed = parser.parse_input(ti)
        print("--- 解析結果 ---")
        for key, value in parsed.items():
            print(f"  {key}: {value}")
        print("------------------")