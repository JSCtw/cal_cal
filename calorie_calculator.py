# calorie_calculator.py
"""依解析結果查表計算熱量與糖量。

甜度：Brand_sweet_setting 的百分比為「剩餘糖量比例」p（依品牌不同），
    最終糖量 = 糖量 × p
    最終熱量 = 熱量 − 糖量 × (1 − p) × 4    （1g 糖 = 4 kcal）

配料：需在 Toppings 表中該品牌欄位打 "V" 才可加減；熱飲查無資料時退回冰飲數值。
回傳格式：{"ok": True, "calories": int, "sugar": float, "ice_fallback": bool}
或 {"ok": False, "error": 錯誤訊息}
"""
import logging

logger = logging.getLogger(__name__)


def _error(message):
    return {"ok": False, "error": message}


class CalorieCalculator:
    def __init__(self, data_loader):
        self.loader = data_loader

    def calculate(self, parsed: dict) -> dict:
        brand, drink = parsed["brand"], parsed["drink"]
        size, ice = parsed["size"], parsed["ice"]

        row = self.loader.drinks_index.get((brand, drink, size, ice))
        fallback = False
        if row is None and ice == "H":
            row = self.loader.drinks_index.get((brand, drink, size, "I"))
            fallback = row is not None
        if row is None:
            variants = self.loader.drink_variants.get((brand, drink))
            if variants:
                sizes = "、".join(sorted({s for s, _ in variants}))
                return _error(f"「{drink}」沒有 {size} 尺寸的資料，可選尺寸：{sizes}")
            return _error(f"資料表中查無「{brand} {drink}」，請檢查 Drinks 工作表")

        calories, sugar = row
        if calories is None or sugar is None:
            return _error(f"「{brand} {drink}」的熱量或糖量欄位不是有效數字，請檢查 Google Sheets")

        sweetness = parsed.get("sweetness")
        if sweetness:
            brand_sweets = self.loader.sweet_map.get(brand, {})
            ratio = brand_sweets.get(sweetness)
            if ratio is None:
                available = "、".join(s for s in self.loader.sweetness_order if s in brand_sweets)
                return _error(f"{brand} 沒有提供「{sweetness}」，可選甜度：{available or '（無資料）'}")
            calories -= sugar * (1 - ratio) * 4
            sugar *= ratio

        for name, count in parsed.get("toppings", []):
            delta = self._topping_values(brand, name)
            if "error" in delta:
                return _error(delta["error"])
            calories += delta["calories"] * count
            sugar += delta["sugar"] * count

        for name, count in parsed.get("removed_toppings", []):
            delta = self._topping_values(brand, name)
            if "error" in delta:
                return _error(delta["error"])
            calories -= delta["calories"] * count
            sugar -= delta["sugar"] * count

        # +1e-9 補償二進位浮點誤差，讓 31.35 這類 .x5 值正確進位
        return {
            "ok": True,
            "calories": round(max(0.0, calories) + 1e-9),
            "sugar": round(max(0.0, sugar) + 1e-9, 1),
            "ice_fallback": fallback,
        }

    def _topping_values(self, brand, name):
        values = self.loader.toppings_map.get(name)
        if values is None:
            return {"error": f"找不到配料「{name}」，請確認名稱"}
        if name not in self.loader.brand_toppings.get(brand, set()):
            available = "、".join(sorted(self.loader.brand_toppings.get(brand, set())))
            suffix = f"，可選配料：{available}" if available else ""
            return {"error": f"{brand} 沒有提供配料「{name}」{suffix}"}
        calories, sugar = values
        if calories is None or sugar is None:
            return {"error": f"配料「{name}」的熱量或糖量欄位不是有效數字，請檢查 Google Sheets"}
        return {"calories": calories, "sugar": sugar}
