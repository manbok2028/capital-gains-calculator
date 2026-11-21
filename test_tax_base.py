"""4단계 검증: 장기보유특별공제율, 고가주택 안분, 기본공제, 과세표준"""

from core import load_rules
from exemption import judge_exemption, parse_scope
from inputs import normalize_case, compute_periods
from tax_base import calc_tax_base, long_term_rate

rules = load_rules()


def run(raw, **kw):
    case = normalize_case(raw)
    periods = compute_periods(case)
    ex = judge_exemption(case, periods, parse_scope(raw), rules)
    return ex, calc_tax_base(case, periods, ex, rules, **kw)


def raw_case(**override):
    raw = {
        "acquisition_date": "2016-05-10", "transfer_date": "2026-11-20",
        "acquisition_price": "5억", "transfer_price": "15억",
        "residence_start": "2016-05-10", "residence_end": "2026-11-20",
    }
    raw.update(override)
    return raw


# 1) 공제율 경계
assert long_term_rate(10, 10, True, rules)[:2] == (80, "table2")
assert long_term_rate(15, 15, True, rules)[:2] == (80, "table2")        # 상한
assert long_term_rate(3, 2, True, rules)[:2] == (20, "table2")          # 12 + 8
assert long_term_rate(3, 1, True, rules)[:2] == (6, "table1")           # 거주 부족 -> 표1
assert long_term_rate(2, 2, True, rules)[:2] == (0, "none")             # 보유 3년 미만
assert long_term_rate(3, 0, False, rules)[:2] == (6, "table1")
assert long_term_rate(15, 0, False, rules)[:2] == (30, "table1")
assert long_term_rate(20, 0, False, rules)[:2] == (30, "table1")        # 상한
assert long_term_rate(2, 0, False, rules)[:2] == (0, "none")
assert long_term_rate(10, 10, False, rules)[:2] == (20, "table1")       # 1주택 아니면 표2 불가

# 2) 고가주택, 보유10 거주10: 양도차익 10억, 과세비율 1/5, 공제 80%
ex, s = run(raw_case())
assert ex["status"] == "HIGH_VALUE_PARTIAL"
assert s["gain"] == 1_000_000_000 and s["taxable_gain"] == 200_000_000
assert s["ltd_rate_pct"] == 80 and s["ltd_amount"] == 160_000_000
assert s["income_amount"] == 40_000_000 and s["basic_deduction"] == 2_500_000
assert s["tax_base"] == 37_500_000

# 3) 같은 건인데 거주 정보 없음(비조정 취득) -> 표1 20%
ex, s = run(raw_case(residence_start="", residence_end=""))
assert s["ltd_table"] == "table1" and s["ltd_rate_pct"] == 20
assert s["ltd_amount"] == 40_000_000 and s["tax_base"] == 157_500_000

# 4) 일반 과세(조정대상지역 취득, 거주 요건 미충족, 보유 6년): 표1 12%
ex, s = run(raw_case(acquisition_date="2020-01-10", transfer_date="2026-11-20",
                     acquisition_price="5억", transfer_price="8억", expenses="1,000만원",
                     residence_start="", residence_end="", regulated_at_acquisition="예"))
assert ex["status"] == "TAXABLE"
assert s["gain"] == 290_000_000 and s["taxable_gain"] == 290_000_000
assert s["ltd_rate_pct"] == 12 and s["ltd_amount"] == 34_800_000
assert s["income_amount"] == 255_200_000 and s["tax_base"] == 252_700_000

# 5) 비과세 / 양도차손은 과세표준 0
ex, s = run(raw_case(transfer_price="10억"))
assert ex["status"] == "EXEMPT" and s["tax_base"] == 0 and s["taxable_gain"] == 0
ex, s = run(raw_case(acquisition_date="2025-01-10", acquisition_price="9억", transfer_price="8억",
                     residence_start="", residence_end=""))
assert s["gain"] < 0 and s["tax_base"] == 0 and s["ltd_amount"] == 0

# 6) 기본공제: 소득금액이 250만원보다 작으면 그만큼만, 이미 썼으면 0
ex, s = run(raw_case(acquisition_date="2025-01-10", transfer_date="2026-11-20",
                     acquisition_price="5억", transfer_price="5억 100만".replace(" ", ""),
                     residence_start="", residence_end="", regulated_at_acquisition="예"))
assert ex["status"] == "TAXABLE" and s["gain"] == 1_000_000
assert s["basic_deduction"] == 1_000_000 and s["tax_base"] == 0
ex, s = run(raw_case(acquisition_date="2025-01-10", acquisition_price="5억", transfer_price="6억",
                     residence_start="", residence_end="", regulated_at_acquisition="예"),
            basic_deduction_available=False)
assert s["basic_deduction"] == 0 and s["tax_base"] == 100_000_000

# 7) 상담 필요 사례는 계산하지 않는다
try:
    run(raw_case(house_count=2))
    raise AssertionError("상담 필요 사례가 계산되었습니다")
except ValueError:
    pass

print("모든 테스트 통과")
