# input_parser.py
"""把使用者輸入拆解成品牌、品名、尺寸、冰量、甜度與加減配料。

解析順序：
1. 先用正則抽出 +配料 / -配料（支援 *N 份數與全形符號），並從字串移除
2. 第 1 個詞比對品牌（別名表或正式名稱）
3. 品牌後的詞組出品名（最多合併 3 個連續詞，處理品名被空格拆開的情況）
4. 剩餘文字依序比對尺寸、冰量、甜度（長別名優先，比中後即從文字移除，避免重複比對）
"""
import re

from config import DEFAULT_SIZE, DEFAULT_ICE, ICE_OPTIONS

# +配料、-配料，可用 *N 指定份數（支援全形 ＋－＊）
_TOPPING_PATTERN = re.compile(r"([+＋\-－])\s*([^\s+＋\-－*＊]+)(?:[*＊](\d+))?")

# 品名最多可由幾個連續詞組成
_MAX_DRINK_TOKENS = 3


class UserInputParser:
    def __init__(self, data_loader):
        self.loader = data_loader

    def parse(self, user_input: str) -> dict:
        text = user_input.strip()

        toppings, removed = [], []

        def _collect(match):
            sign, name, times = match.groups()
            count = int(times) if times else 1
            (toppings if sign in "+＋" else removed).append((name, count))
            return " "

        remainder = _TOPPING_PATTERN.sub(_collect, text)

        words = remainder.split()
        if len(words) < 2:
            return {"error": "輸入資訊過少，請遵循「品牌 品名 [尺寸/冰量/甜度] [+配料]」格式"}

        brand = self._identify_brand(words[0])
        if not brand:
            return {"error": f"找不到品牌「{words[0]}」"}

        drink, used_tokens = self._identify_drink(brand, words[1:])
        if not drink:
            return {"error": f"在 {brand} 中找不到飲品「{words[1]}」"}

        rest_text = " ".join(words[1 + used_tokens:])
        size, rest_text = self._consume(rest_text, self.loader.size_alias_map)
        ice, rest_text = self._consume(rest_text, ICE_OPTIONS)
        sweetness, rest_text = self._consume_sweetness(rest_text)

        return {
            "brand": brand,
            "drink": drink,
            "size": size or DEFAULT_SIZE,
            "ice": ice or DEFAULT_ICE,
            "sweetness": sweetness,
            "toppings": toppings,
            "removed_toppings": removed,
        }

    def _identify_brand(self, token):
        token = token.strip()
        if token in self.loader.known_brands:
            return token
        return (self.loader.brands_alias_map.get(token)
                or self.loader.brands_alias_map.get(token.casefold()))

    def _identify_drink(self, brand, tokens):
        """從品牌後的詞嘗試組出品名，較長的組合優先。"""
        brand_drinks = self.loader.brand_drinks.get(brand, set())
        for k in range(min(_MAX_DRINK_TOKENS, len(tokens)), 0, -1):
            candidate = "".join(tokens[:k])
            # 正式品名優先於別名，避免別名表把使用者輸入的正式品名改寫成別款飲料
            if candidate in brand_drinks:
                return candidate, k
            std = self.loader.drinks_alias_map.get((brand, candidate))
            if std:
                return std, k
        return None, 0

    @staticmethod
    def _consume(text, mapping):
        """在剩餘文字中尋找別名（長的優先），找到後從文字移除。回傳 (標準值, 剩餘文字)。"""
        for alias in sorted(mapping, key=len, reverse=True):
            if alias and alias in text:
                return mapping[alias], text.replace(alias, " ", 1)
        return None, text

    def _consume_sweetness(self, text):
        names = {s for levels in self.loader.sweet_map.values() for s in levels}
        names.update(self.loader.sweetness_order)
        for name in sorted(names, key=len, reverse=True):
            if name and name in text:
                return name, text.replace(name, " ", 1)
        return None, text
