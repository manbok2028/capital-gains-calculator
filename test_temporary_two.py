"""일시적 2주택 특례 검증: 1년 경계, 처분기한 경계, 2년/3년 규정 구분, 경과조치"""

from datetime import date

from core import load_rules
from inputs import normalize_case
from temporary_two import check_temporary_two_house, deadline_years, parse_two_house_inputs

rules = load_rules()


def check(**override):
    raw = {
        "acquisition_date": "2016-05-10", "transfer_date": "2026-11-20",
        "acquisition_price": "5억", "transfer_price": "10억",
        "house_count": 2, "new_house_acquisition_date": "2025-03-01",
        "house_count_before_new": 1,
        "old_house_regulated_at_new_acquisition": "아니오",
        "new_house_regulated_at_acquisition": "아니오",
    }
    raw.update(override)
    return check_temporary_two_house(normalize_case(raw), raw, rules)


def raises(**override):
    try:
        check(**override)
    except ValueError:
        return True
    return False


# 1) 기한(년) 구분: 2년 규정은 4가지를 모두 만족할 때만
def years(old_reg, new_reg, new_date, transfer, **extra):
    raw = {"new_house_acquisition_date": new_date, "old_house_regulated_at_new_acquisition": old_reg,
           "new_house_regulated_at_acquisition": new_reg}
    raw.update(extra)
    return deadline_years(parse_two_house_inputs(raw), date.fromisoformat(transfer), rules)[0]

assert years(True, True, "2026-09-01", "2026-11-20") == 2
assert years(True, False, "2026-09-01", "2026-11-20") == 3      # 신규주택이 조정대상지역 아님
assert years(False, True, "2026-09-01", "2026-11-20") == 3      # 종전주택이 조정대상지역 아님
assert years(True, True, "2026-08-04", "2026-11-20") == 2       # 2026-08-04 취득: 2년
assert years(True, True, "2026-08-03", "2026-11-20") == 3       # 2026-08-03 취득: 종전 규정
assert years(True, True, "2026-09-01", "2026-09-30") == 3       # 시행일(10/1) 전 양도
assert years(True, True, "2026-09-01", "2026-10-01") == 2       # 시행일 당일 양도
# 계약금을 8/3 이전에 지급했다면 3년
assert years(True, True, "2026-09-01", "2026-11-20", new_house_contract_date="2026-08-03") == 3
assert years(True, True, "2026-09-01", "2026-11-20", new_house_contract_date="2026-08-04") == 2
# 조정대상지역 공고일(포함) 이전 취득이면 3년
assert years(True, True, "2026-09-01", "2026-11-20", new_area_designation_date="2026-09-01") == 3
assert years(True, True, "2026-09-01", "2026-11-20", new_area_designation_date="2026-08-31") == 2

# 2) 1년 경과 요건: 종전 취득일의 1년 후 같은 날은 아직 '지난 후'가 아니다 (다음 날부터)
base = dict(acquisition_date="2020-06-10", transfer_date="2023-12-01")
assert check(new_house_acquisition_date="2021-06-10", **base)["qualifies"] is False
assert check(new_house_acquisition_date="2021-06-11", **base)["qualifies"] is True

# 3) 처분기한 경계 (3년): 신규 취득일의 3년 후 같은 날까지
b3 = dict(new_house_acquisition_date="2023-03-15")
assert check(transfer_date="2026-03-15", **b3)["qualifies"] is True
assert check(transfer_date="2026-03-16", **b3)["qualifies"] is False

# 4) 2년 규정 경계
b2 = dict(new_house_acquisition_date="2026-09-01", old_house_regulated_at_new_acquisition="예",
          new_house_regulated_at_acquisition="예")
assert check(transfer_date="2028-09-01", **b2)["qualifies"] is True
r = check(transfer_date="2028-09-02", **b2)
assert r["qualifies"] is False and r["deadline_years"] == 2

# 5) 신규주택 취득 직전 보유 주택 수
assert check(house_count_before_new=2)["qualifies"] is False

# 6) 자료 모순은 입력 오류
assert raises(new_house_acquisition_date="2015-01-01")           # 종전 취득일보다 앞섬
assert raises(new_house_acquisition_date="2027-01-01")           # 양도일보다 늦음
assert raises(new_house_acquisition_date="")                      # 누락
assert raises(new_house_contract_date="2025-04-01")              # 계약금 지급일 > 취득일
assert raises(house_count_before_new="abc")

print("모든 테스트 통과")
