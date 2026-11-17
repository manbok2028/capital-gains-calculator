"""3단계 검증: 비과세 판정의 경계값과 범위 밖 안내"""

from fractions import Fraction

import inputs
from core import load_rules
from exemption import format_won, parse_scope, judge_exemption
from inputs import normalize_case, compute_periods

rules = load_rules()


def judge(**override):
    raw = {
        "acquisition_date": "2018-05-10", "transfer_date": "2026-11-20",
        "acquisition_price": "5억", "transfer_price": "10억",
        "residence_start": "2018-05-10", "residence_end": "2026-11-20",
        "regulated_at_acquisition": "아니오",
    }
    raw.update(override)
    case = normalize_case(raw)
    return judge_exemption(case, compute_periods(case), parse_scope(raw), rules)


def raises(func, *args):
    try:
        func(*args)
    except ValueError:
        return True
    return False


# 1) 금액 표기
assert format_won(1_350_000_000) == "13억 5,000만원"
assert format_won(1_200_000_000) == "12억원"
assert format_won(50_000_000) == "5,000만원"
assert format_won(0) == "0원"

# 2) 12억 경계: 12억 정확히 = 비과세, 1원 초과 = 고가주택
assert judge(transfer_price="12억")["status"] == "EXEMPT"
r = judge(transfer_price="1200000001")
assert r["status"] == "HIGH_VALUE_PARTIAL" and r["taxable_ratio"] == Fraction(1, 1_200_000_001)
assert judge(transfer_price="13억5000만")["taxable_ratio"] == Fraction(1, 9)

# 3) 보유 2년 경계 (기본 규칙: 응당일 당일 충족)
base = dict(acquisition_date="2020-03-15", residence_start="2020-03-15")
r = judge(transfer_date="2022-03-14", residence_end="2022-03-14", **base)
assert r["status"] == "TAXABLE"
r = judge(transfer_date="2022-03-15", residence_end="2022-03-15", **base)
assert r["status"] == "EXEMPT"

# 3-1) 같은 날짜가 '다음 날 규칙'에서는 과세로 바뀌는지
inputs.PERIOD_RULE = "anniversary_next_day"
try:
    r = judge(transfer_date="2022-03-15", residence_end="2022-03-15", **base)
    assert r["status"] == "TAXABLE"
    r = judge(transfer_date="2022-03-16", residence_end="2022-03-16", **base)
    assert r["status"] == "EXEMPT"
finally:
    inputs.PERIOD_RULE = "anniversary_inclusive"

# 4) 조정대상지역 취득: 거주 2년 요건
r = judge(regulated_at_acquisition="예", residence_start="2025-01-01", residence_end="2026-11-20")
assert r["status"] == "TAXABLE" and "거주" in r["reasons"][0]
r = judge(regulated_at_acquisition="예")  # 거주 8년
assert r["status"] == "EXEMPT"
# 거주 요건은 2017-08-03 이후 취득분부터
r = judge(acquisition_date="2017-08-02", residence_start="2017-08-02", residence_end="2017-08-02",
          regulated_at_acquisition="예", transfer_date="2026-11-20")
assert r["status"] == "EXEMPT"
r = judge(acquisition_date="2017-08-03", residence_start="2017-08-03", residence_end="2017-08-03",
          regulated_at_acquisition="예", transfer_date="2026-11-20")
assert r["status"] == "TAXABLE"

# 5) 비조정대상지역 취득은 거주기간 입력 없이도 비과세
r = judge(residence_start="", residence_end="")
assert r["status"] == "EXEMPT"

# 6) 사유가 두 개 이상이면 모두 알려준다
r = judge(acquisition_date="2025-06-01", residence_start="2025-06-01", residence_end="2026-01-01",
          regulated_at_acquisition="예")
assert r["status"] == "TAXABLE" and len(r["reasons"]) == 2

# 7) 범위 밖은 상담 안내
assert judge(house_count=2)["status"] == "CONSULT"
assert judge(acquisition_type="상속")["status"] == "CONSULT"
assert len(judge(house_count=3, acquisition_type="증여")["reasons"]) == 2
assert judge(house_count="1", acquisition_type="매매")["status"] == "EXEMPT"

# 8) 범위 입력 검증
assert raises(parse_scope, {"house_count": "abc"})
assert raises(parse_scope, {"house_count": 0})
assert raises(parse_scope, {"acquisition_type": "교환"})

print("모든 테스트 통과")