# data_loader.py
"""從 Google Sheets 載入營養資料，建立查詢用的索引結構。

工作表結構（試算表：Nutrition_Facts）：
- Drinks:              Brand_Standard_Name, Standard_Drinks_Name, Size, 冰量, 熱量, 糖量, ...
                       （其餘分項欄位不使用；「熱量／糖量」為最終權威值）
- Toppings:            Topping_Name, 熱量, 糖量, <各品牌欄位，打 "V" 表示該品牌提供此配料>
- Brand_sweet_setting: 列=甜度、欄=品牌，儲存格為「剩餘糖量比例」（如 70%），空格=該品牌無此甜度
- Brands_Alias:        Brand_Alias_Name, Brand_Standard_Name
- Size_Alias:          Size_Alias, Size
- Drinks_Alias:        Brand_Standard_Name, Standard_Drinks_Name, Alias_Drinks_Name（逗號分隔多個別名）

載入成功後會把原始資料寫入本地快取檔；啟動時若 Google Sheets 連不上，
會退回快取資料，避免 Sheets 故障導致機器人完全無法啟動。
"""
import json
import logging
import os

import gspread

logger = logging.getLogger(__name__)


def _to_float(value):
    try:
        return float(str(value).strip().replace(",", ""))
    except (TypeError, ValueError):
        return None


def _expand_names(name):
    """把「珍珠奶茶/奶綠/奶青」這類合併品名展開成多個完整品名。

    規則（50嵐 的資料慣例）：第一段為完整品名；後續各段若比第一段短，
    取代第一段結尾等長的文字（奶綠 -> 珍珠奶綠），否則視為另一個完整品名
    （「奶茶/奶綠/奶青」-> 奶茶、奶綠、奶青）。空段（連續斜線）自動略過。
    """
    parts = [p.strip() for p in name.split("/") if p.strip()]
    if len(parts) <= 1:
        return parts
    base = parts[0]
    expanded = [base]
    for alt in parts[1:]:
        expanded.append(base[:-len(alt)] + alt if len(alt) < len(base) else alt)
    return expanded


def _parse_ratio(value):
    """把 '70%'、'82.5%'、'0.7' 等剩餘糖量比例解析成 0~1 的浮點數；空白回傳 None。"""
    s = str(value).strip().replace("％", "%")
    if not s:
        return None
    try:
        if s.endswith("%"):
            return float(s[:-1]) / 100.0
        x = float(s)
        return x / 100.0 if x > 1 else x
    except ValueError:
        return None


class DataLoader:
    def __init__(self, secret_key_json_str="", sheet_name="", cache_path="cache/sheet_cache.json"):
        self.secret_key_json_str = secret_key_json_str
        self.sheet_name = sheet_name
        self.cache_path = cache_path
        self.source = None  # "sheets" 或 "cache"

    def load(self):
        """啟動時載入：優先抓 Google Sheets，失敗時退回本地快取。"""
        try:
            self.refresh()
        except Exception:
            logger.exception("無法從 Google Sheets 載入資料，嘗試使用本地快取")
            if not self._load_cache():
                raise

    def refresh(self):
        """重新從 Google Sheets 抓取所有工作表並重建索引。"""
        secret_key_dict = json.loads(self.secret_key_json_str)
        gc = gspread.service_account_from_dict(secret_key_dict)
        spreadsheet = gc.open(self.sheet_name)

        raw = {
            "drinks": spreadsheet.worksheet("Drinks").get_all_records(),
            "toppings": spreadsheet.worksheet("Toppings").get_all_records(),
            "brand_sweet": spreadsheet.worksheet("Brand_sweet_setting").get_all_values(),
            "brands_alias": spreadsheet.worksheet("Brands_Alias").get_all_records(),
            "size_alias": spreadsheet.worksheet("Size_Alias").get_all_records(),
            "drinks_alias": spreadsheet.worksheet("Drinks_Alias").get_all_records(),
        }
        self.build(raw)
        self.source = "sheets"
        self._save_cache(raw)
        logger.info("已從 Google Sheets 載入 %d 筆飲品資料", len(self.drinks_index))

    def build(self, raw):
        """把原始資料轉成查詢索引。先在區域變數組完、最後一次掛上，避免其他執行緒讀到半成品。"""
        # --- Drinks ---
        drinks_index = {}    # (品牌, 品名, Size, 冰量) -> (熱量, 糖量)
        brand_drinks = {}    # 品牌 -> {正式品名}
        drink_variants = {}  # (品牌, 品名) -> {(Size, 冰量)}
        for row in raw["drinks"]:
            brand = str(row.get("Brand_Standard_Name", "")).strip()
            drink = str(row.get("Standard_Drinks_Name", "")).strip()
            size = str(row.get("Size", "")).strip()
            ice = str(row.get("冰量", "")).strip()
            if not (brand and drink):
                continue
            values = (_to_float(row.get("熱量")), _to_float(row.get("糖量")))
            # 合併品名（含 "/"）展開成多個名稱，全部指向同一筆營養資料；
            # 原始合併字串也保留可查
            for name in {drink, *_expand_names(drink)}:
                drinks_index[(brand, name, size, ice)] = values
                brand_drinks.setdefault(brand, set()).add(name)
                drink_variants.setdefault((brand, name), set()).add((size, ice))

        # --- Toppings（品牌欄打 V 表示該品牌提供） ---
        toppings_map = {}    # 配料名 -> (熱量, 糖量)
        brand_toppings = {}  # 品牌 -> {配料名}
        base_cols = {"Topping_Name", "熱量", "糖量"}
        for row in raw["toppings"]:
            name = str(row.get("Topping_Name", "")).strip()
            if not name:
                continue
            toppings_map[name] = (_to_float(row.get("熱量")), _to_float(row.get("糖量")))
            for col, cell in row.items():
                if col in base_cols:
                    continue
                if str(cell).strip().upper() == "V":
                    brand_toppings.setdefault(str(col).strip(), set()).add(name)

        # --- Brand_sweet_setting 矩陣 ---
        sweet_map = {}        # 品牌 -> {甜度: 剩餘糖量比例}
        sweetness_order = []  # 依工作表列順序，用於錯誤訊息中列出可選甜度
        matrix = raw["brand_sweet"]
        header = [str(c).strip() for c in matrix[0]] if matrix else []
        matrix_brands = header[1:]
        for row in matrix[1:]:
            sweet_name = str(row[0]).strip() if row else ""
            if not sweet_name:
                continue
            sweetness_order.append(sweet_name)
            for i, brand in enumerate(matrix_brands, start=1):
                ratio = _parse_ratio(row[i]) if i < len(row) else None
                if ratio is not None:
                    sweet_map.setdefault(brand, {})[sweet_name] = ratio

        # --- 別名表 ---
        brands_alias_map = {}
        for row in raw["brands_alias"]:
            alias = str(row.get("Brand_Alias_Name", "")).strip()
            std = str(row.get("Brand_Standard_Name", "")).strip()
            if alias and std:
                brands_alias_map[alias] = std
                brands_alias_map.setdefault(alias.casefold(), std)  # 英文別名不分大小寫

        size_alias_map = {}
        for row in raw["size_alias"]:
            alias = str(row.get("Size_Alias", "")).strip()
            if alias:
                size_alias_map[alias] = str(row.get("Size", "")).strip()

        drinks_alias_map = {}  # (品牌, 別名) -> 正式品名
        for row in raw["drinks_alias"]:
            brand = str(row.get("Brand_Standard_Name", "")).strip()
            std = str(row.get("Standard_Drinks_Name", "")).strip()
            aliases = str(row.get("Alias_Drinks_Name", "")).strip()
            if not (brand and std and aliases):
                continue
            for alias in aliases.split(","):
                alias = alias.strip()
                if alias:
                    drinks_alias_map[(brand, alias)] = std

        known_brands = set(brand_drinks) | set(matrix_brands) | set(brand_toppings)

        self.drinks_index = drinks_index
        self.brand_drinks = brand_drinks
        self.drink_variants = drink_variants
        self.toppings_map = toppings_map
        self.brand_toppings = brand_toppings
        self.sweet_map = sweet_map
        self.sweetness_order = sweetness_order
        self.brands_alias_map = brands_alias_map
        self.size_alias_map = size_alias_map
        self.drinks_alias_map = drinks_alias_map
        self.known_brands = known_brands

    # --- 本地快取 ---
    def _save_cache(self, raw):
        try:
            cache_dir = os.path.dirname(self.cache_path)
            if cache_dir:
                os.makedirs(cache_dir, exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(raw, f, ensure_ascii=False)
        except OSError:
            logger.warning("無法寫入快取檔 %s", self.cache_path, exc_info=True)

    def _load_cache(self):
        try:
            with open(self.cache_path, encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, ValueError):
            return False
        self.build(raw)
        self.source = "cache"
        logger.warning("已改用本地快取資料（%s）", self.cache_path)
        return True
