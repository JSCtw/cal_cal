# tests/test_offline.py
"""不需網路與金鑰的離線邏輯測試：用模擬的新版工作表資料驗證解析與計算。

執行方式：python tests/test_offline.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calorie_calculator import CalorieCalculator
from data_loader import DataLoader
from input_parser import UserInputParser

# 模擬新版 Google Sheets 結構的原始資料
RAW = {
    "drinks": [
        {"Brand_Standard_Name": "50嵐", "Standard_Drinks_Name": "珍珠奶茶",
         "Size": "L", "冰量": "I", "熱量": 650, "糖量": 45},
        {"Brand_Standard_Name": "50嵐", "Standard_Drinks_Name": "珍珠奶茶",
         "Size": "M", "冰量": "I", "熱量": 500, "糖量": 35},
        {"Brand_Standard_Name": "50嵐", "Standard_Drinks_Name": "四季春青茶",
         "Size": "L", "冰量": "I", "熱量": 160, "糖量": 40},
        {"Brand_Standard_Name": "50嵐", "Standard_Drinks_Name": "波霸奶茶/奶綠/奶青",
         "Size": "L", "冰量": "I", "熱量": 600, "糖量": 42},
        {"Brand_Standard_Name": "50嵐", "Standard_Drinks_Name": "奶茶/奶綠/奶青",
         "Size": "L", "冰量": "I", "熱量": 420, "糖量": 40},
        {"Brand_Standard_Name": "清心福全", "Standard_Drinks_Name": "嚴選高山茶",
         "Size": "L", "冰量": "I", "熱量": 120, "糖量": 30},
        {"Brand_Standard_Name": "迷客夏", "Standard_Drinks_Name": "大正紅茶拿鐵",
         "Size": "L", "冰量": "I", "熱量": 200, "糖量": 38},
        {"Brand_Standard_Name": "迷客夏", "Standard_Drinks_Name": "大正紅茶拿鐵",
         "Size": "L", "冰量": "H", "熱量": 190, "糖量": 36},
    ],
    "toppings": [
        {"Topping_Name": "珍珠", "熱量": 180, "糖量": 10,
         "50嵐": "V", "迷客夏": "V", "清心福全": ""},
        {"Topping_Name": "椰果", "熱量": 50, "糖量": 8,
         "50嵐": "V", "迷客夏": "", "清心福全": "V"},
    ],
    "brand_sweet": [
        ["Brand-sweet_setting", "50嵐", "清心福全", "迷客夏"],
        ["正常", "100%", "100%", "100%"],
        ["少糖", "70%", "", "82.5%"],
        ["微糖", "30%", "35%", ""],
        ["無糖", "0%", "0%", "0%"],
    ],
    "brands_alias": [
        {"Brand_Alias_Name": "五十嵐", "Brand_Standard_Name": "50嵐"},
        {"Brand_Alias_Name": "清心", "Brand_Standard_Name": "清心福全"},
        {"Brand_Alias_Name": "MILKSHA", "Brand_Standard_Name": "迷客夏"},
    ],
    "size_alias": [
        {"Size_Alias": "大杯", "Size": "L"},
        {"Size_Alias": "大", "Size": "L"},
        {"Size_Alias": "中杯", "Size": "M"},
        {"Size_Alias": "中", "Size": "M"},
    ],
    "drinks_alias": [
        {"Brand_Standard_Name": "50嵐", "Standard_Drinks_Name": "珍珠奶茶",
         "Alias_Drinks_Name": "珍奶, 波霸奶茶"},
        {"Brand_Standard_Name": "清心福全", "Standard_Drinks_Name": "嚴選高山茶",
         "Alias_Drinks_Name": "高山, 高山茶"},
        {"Brand_Standard_Name": "迷客夏", "Standard_Drinks_Name": "大正紅茶拿鐵",
         "Alias_Drinks_Name": "大正紅茶"},
    ],
}

PASSED = []
FAILED = []


def check(name, actual, expected):
    if actual == expected:
        PASSED.append(name)
    else:
        FAILED.append(f"{name}\n    期望: {expected}\n    實際: {actual}")


def main():
    loader = DataLoader()
    loader.build(RAW)
    parser = UserInputParser(loader)
    calc = CalorieCalculator(loader)

    def run(text):
        parsed = parser.parse(text)
        if parsed.get("error"):
            return {"ok": False, "error": parsed["error"]}, parsed
        return calc.calculate(parsed), parsed

    # 1. 甜度（剩餘比例 30%）+ 配料份數 *2
    #    熱量 650 - 45*(1-0.3)*4 = 524；+珍珠180*2 = 884；糖 45*0.3 + 10*2 = 33.5
    r, _ = run("50嵐 珍奶 微糖 +珍珠*2")
    check("微糖+珍珠*2 熱量", r.get("calories"), 884)
    check("微糖+珍珠*2 糖量", r.get("sugar"), 33.5)

    # 2. 品牌別名 + 尺寸 M + 品牌別甜度（50嵐少糖=70%）
    #    500 - 35*0.3*4 = 458；糖 35*0.7 = 24.5
    r, p = run("五十嵐 珍珠奶茶 中 少糖")
    check("五十嵐 中杯 尺寸", p.get("size"), "M")
    check("五十嵐 少糖 熱量", r.get("calories"), 458)
    check("五十嵐 少糖 糖量", r.get("sugar"), 24.5)

    # 3. 迷客夏少糖比例不同（82.5%）：200 - 38*0.175*4 = 173.4 -> round 173
    r, _ = run("迷客夏 大正紅茶 少糖")
    check("迷客夏 少糖 熱量", r.get("calories"), 173)
    check("迷客夏 少糖 糖量", r.get("sugar"), 31.4)

    # 4. 熱飲 fallback：清心無 H 資料，退回 I
    r, p = run("清心 高山 熱 大")
    check("熱飲 fallback 冰量解析", p.get("ice"), "H")
    check("熱飲 fallback 啟動", r.get("ice_fallback"), True)
    check("熱飲 fallback 熱量", r.get("calories"), 120)

    # 5. 熱飲有 H 資料時直接使用（品名含「大」不可誤判尺寸）
    r, p = run("迷客夏 大正紅茶拿鐵 熱")
    check("H 資料存在不 fallback", r.get("ice_fallback"), False)
    check("品名含大不誤判尺寸", p.get("size"), "L")
    check("熱飲熱量", r.get("calories"), 190)

    # 6. 品牌沒有該甜度 -> 錯誤並列出可選
    r, _ = run("清心 高山 少糖")
    check("無此甜度回錯誤", r.get("ok"), False)
    check("錯誤列出可選甜度",
          "可選甜度：正常、微糖、無糖" in r.get("error", ""), True)

    # 7. 品牌沒打 V 的配料 -> 錯誤
    r, _ = run("清心 高山 +珍珠")
    check("無此配料回錯誤", r.get("ok"), False)
    check("錯誤含品牌無配料", "清心福全 沒有提供配料「珍珠」" in r.get("error", ""), True)

    # 8. 無糖：650 - 45*4 = 470，糖 0
    r, _ = run("50嵐 珍奶 無糖")
    check("無糖 熱量", r.get("calories"), 470)
    check("無糖 糖量", r.get("sugar"), 0.0)

    # 9. 減配料：650 - 180 = 470，糖 45 - 10 = 35
    r, _ = run("50嵐 珍奶 -珍珠")
    check("減配料 熱量", r.get("calories"), 470)
    check("減配料 糖量", r.get("sugar"), 35.0)

    # 10. 找不到品牌
    r, _ = run("麻古 芝芝")
    check("未知品牌錯誤", "找不到品牌" in r.get("error", ""), True)

    # 11. 品名被空格拆開仍可合併比對
    _, p = run("50嵐 四季 春青茶")
    check("多詞品名合併", p.get("drink"), "四季春青茶")

    # 12. 找不到的配料名
    r, _ = run("50嵐 珍奶 +布蕾")
    check("未知配料錯誤", "找不到配料「布蕾」" in r.get("error", ""), True)

    # 13. 合併品名展開：後段取代結尾（波霸奶綠 <- 波霸奶茶/奶綠/奶青）
    r, p = run("50嵐 波霸奶綠")
    check("合併品名-取代結尾", p.get("drink"), "波霸奶綠")
    check("合併品名-取代結尾 熱量", r.get("calories"), 600)

    # 14. 合併品名展開：等長段視為完整品名（奶青 <- 奶茶/奶綠/奶青）
    r, p = run("50嵐 奶青")
    check("合併品名-完整名", p.get("drink"), "奶青")
    check("合併品名-完整名 熱量", r.get("calories"), 420)

    # 15. 合併品名第一段本身可查
    r, _ = run("50嵐 波霸奶茶")
    check("合併品名-第一段", r.get("calories"), 600)

    print(f"通過 {len(PASSED)} 項")
    if FAILED:
        print(f"失敗 {len(FAILED)} 項：")
        for f in FAILED:
            print(f"  ✗ {f}")
        sys.exit(1)
    print("全部測試通過 ✅")


if __name__ == "__main__":
    main()
