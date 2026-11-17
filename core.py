"""양도소득세 계산기 - 1단계: 세율표(JSON) 로드와 누진세 계산 (정수/분수 연산, float 미사용)"""

import json
from fractions import Fraction


def load_rules(path="rules_2026.json"):
    """세율표 등 법령 수치를 담은 JSON을 읽는다."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def tax_by_formula(base, brackets):
    """산출세액 = 과세표준 x 세율 - 누진공제 (구간을 찾아 한 번에 계산)."""
    if base <= 0:
        return 0
    for b in brackets:
        if b["upper"] is None or base <= b["upper"]:
            exact = Fraction(base * b["rate_pct"], 100) - b["deduction"]
            return int(exact)  # 원 미만 절사 (양수이므로 int = floor)
    raise ValueError("세율표에 해당 구간이 없습니다")


def tax_by_slices(base, brackets):
    """구간별로 잘라서(초과누진) 세액을 더한다. tax_by_formula 교차 검증용."""
    if base <= 0:
        return 0
    total = Fraction(0)
    lower = 0
    for b in brackets:
        upper = b["upper"] if b["upper"] is not None else base
        part = min(base, upper) - lower
        if part > 0:
            total += Fraction(part * b["rate_pct"], 100)
        if base <= upper:
            break
        lower = upper
    return int(total)


def local_income_tax(tax, rules):
    """지방소득세 = 산출세액 x 10% (원 미만 절사)."""
    return tax * rules["local_income_tax_pct"] // 100


if __name__ == "__main__":
    rules = load_rules()
    br = rules["basic_rates"]
    for base in (14_000_000, 50_000_000, 100_000_000, 1_000_000_000, 1_200_000_000):
        a, b = tax_by_formula(base, br), tax_by_slices(base, br)
        print(f"과세표준 {base:>13,}원 -> 산출세액 {a:>12,}원 (구간합산 {b:>12,}원) {'일치' if a == b else '불일치!'}")