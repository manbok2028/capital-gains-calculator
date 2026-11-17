"""1단계 검증: 손으로 계산한 값, 구간 경계, 두 계산 방식의 일치 여부"""

import random

from core import load_rules, tax_by_formula, tax_by_slices, local_income_tax

rules = load_rules()
br = rules["basic_rates"]

# 1) 손으로 검산한 값
known = {
    0: 0,
    14_000_000: 840_000,            # 1,400만 x 6%
    50_000_000: 6_240_000,          # 5,000만 x 15% - 126만
    100_000_000: 19_560_000,        # 1억 x 35% - 1,544만
    1_000_000_000: 384_060_000,     # 10억 x 42% - 3,594만
    1_200_000_000: 474_060_000,     # 12억 x 45% - 6,594만
}
for base, expected in known.items():
    got = tax_by_formula(base, br)
    assert got == expected, f"{base}: {got} != {expected}"

# 2) 모든 구간 경계에서 공식 계산 == 구간합산 계산 (누진공제가 맞는지 검증)
for b in br:
    if b["upper"] is None:
        continue
    for delta in (-1, 0, 1):
        base = b["upper"] + delta
        assert tax_by_formula(base, br) == tax_by_slices(base, br), base

# 3) 무작위 값 5,000개에서도 일치
random.seed(1)
for _ in range(5000):
    base = random.randint(1, 3_000_000_000)
    assert tax_by_formula(base, br) == tax_by_slices(base, br), base

# 4) 지방소득세 10%
assert local_income_tax(19_560_000, rules) == 1_956_000

print("모든 테스트 통과")