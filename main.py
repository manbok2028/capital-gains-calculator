"""양도소득세 계산기 (국내 주택, 1세대 1주택 중심) - 고객용 콘솔 프로그램"""

from calculator import calculate, describe_result
from exemption import parse_scope
from inputs import parse_date, parse_won
from run_cases import run_all

INTRO = """=== 양도소득세 계산기 (주택) ===
자동 계산 범위: 국내 주택 1채를 매매로 취득해 양도하는 경우 (1세대 1주택 비과세 판정 + 일반 과세)
다주택, 일시적 2주택, 상속·증여 취득 등은 계산하지 않고 상담을 안내합니다.
"""


def ask(prompt, parse=None, optional=False):
    """입력을 받아 parse로 검증한다. 형식이 틀리면 안내 후 다시 묻는다. 문자열을 돌려준다."""
    while True:
        text = input(prompt).strip()
        if optional and not text:
            return ""
        try:
            if parse:
                parse(text)
            return text
        except ValueError as e:
            print(f"  → {e}")


def ask_yes_no(prompt):
    while True:
        text = input(prompt + " (y/n): ").strip().lower()
        if text in ("y", "yes", "예", "네"):
            return True
        if text in ("n", "no", "아니오", "아니요"):
            return False
        print("  → y 또는 n으로 입력하세요.")


def parse_house_count(text):
    try:
        n = int(text)
    except ValueError:
        raise ValueError("주택 수는 숫자로 입력하세요.")
    if n < 1:
        raise ValueError("주택 수는 1 이상이어야 합니다. (양도하는 주택 포함)")


def parse_acquisition(text):
    parse_scope({"acquisition_type": text})


def collect_input():
    """고객에게 질문해서 계산용 입력(dict)과 기본공제 사용 가능 여부를 만든다."""
    raw = {}
    raw["acquisition_date"] = ask("취득일 (예: 2018-05-10): ", parse_date)
    raw["transfer_date"] = ask("양도일 (예: 2026-11-20): ", parse_date)
    raw["acquisition_price"] = ask("취득가액 (예: 5억, 500000000): ", parse_won)
    raw["transfer_price"] = ask("양도가액 (예: 13억5000만): ", parse_won)
    raw["expenses"] = ask("취득가액 외 필요경비 합계 - 취득세, 중개수수료, 자본적지출 등 (없으면 Enter): ",
                          parse_won, optional=True) or "0"
    raw["house_count"] = ask("양도일 현재 본인과 배우자 등 같은 세대가 보유한 주택 수 (양도하는 주택 포함): ",
                             parse_house_count)
    raw["acquisition_type"] = ask("취득 원인 (매매/상속/증여/기타): ", parse_acquisition)
    raw["regulated_at_acquisition"] = "예" if ask_yes_no("취득 당시 조정대상지역이었습니까?") else "아니오"
    if ask_yes_no("이 주택에 직접 거주하셨습니까?"):
        raw["residence_start"] = ask("거주 시작일: ", parse_date)
        raw["residence_end"] = ask("거주 종료일 (지금도 거주 중이면 양도일): ", parse_date)
    available = not ask_yes_no("올해 이미 다른 양도소득에서 기본공제(연 250만원)를 받으셨습니까?")
    return raw, available


def mode_calculate():
    while True:
        print()
        raw, available = collect_input()
        try:
            result = calculate(raw, basic_deduction_available=available)
        except ValueError as e:
            print(f"\n입력을 확인해 주세요: {e}\n처음부터 다시 입력합니다.")
            continue
        line = "#" + "-" * 39
        print(f"\n{line}\n# 계산 결과\n{line}")
        print(describe_result(result))
        return


def main():
    print(INTRO)
    print("[메뉴]\n1. 양도소득세 계산\n2. 테스트 케이스 실행 (검증용)")
    while True:
        choice = input("선택: ").strip()
        if choice == "1":
            mode_calculate()
            break
        if choice == "2":
            run_all()
            break
        print("입력 형식 오류: 1 또는 2를 입력하세요.")


if __name__ == "__main__":
    main()
