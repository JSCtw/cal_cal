from data_loader import DataLoader
from input_parser import UserInputParser
from calorie_calculator import CalorieCalculator

def main():
    loader = DataLoader("data/Nutrition_Facts.xlsx")
    parser = UserInputParser(loader)
    calculator = CalorieCalculator(loader)

    while True:
        user_input = input("請輸入飲料資訊（或輸入 exit 離開）：")
        if user_input.lower() == "exit":
            break

        parsed = parser.parse_input(user_input)
        if not parsed["brand"] or not parsed["drink"] or not parsed["size"]:
            print("❌ 輸入格式不完整，請確保包含品牌、飲料與容量資訊。")
            continue

        total_cal, error = calculator.calculate_total(parsed)
        if error:
            print(f"❌ 錯誤：{error}")
        else:
            print(f"✅ 熱量為：{total_cal} 大卡")

if __name__ == "__main__":
    main()
