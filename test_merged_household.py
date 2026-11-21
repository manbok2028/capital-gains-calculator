"""동거봉양 합가 / 혼인 합가 특례 검증: 10년 경계, 요건 누락, 시행 시점"""

from core import load_rules
from inputs import normalize_case
from merged_household import check_merged_household, parse_two_house_reason

rules = load_rules()


def check(reason, **override):
    raw = {
        "acquisition_date": "2016-05-10", "transfer_date": "2026-11-20",
        "acquisition_price": "5억", "transfer_price": "10억",
        "house_count": 2, "two_house_reason": reason,
        "merge_date": "2022-03-01", "one_house_each_before_merge": "예",
        "parent_qualified": "예", "was_separate_household": "예",
    }
    raw.update(override)
    return check_merged_household(normalize_case(raw), raw, rules, parse_two_house_reason(raw))


def raises(reason, **override):
    try:
        check(reason, **override)
    except ValueError:
        return True
    return False


# 1) 사유 표기
for word, want in [("신규주택", "temporary"), ("동거봉양", "parent_care"), ("혼인", "marriage"),
                   ("parent_care", "parent_care"), ("혼인 합가", "marriage")]:
    assert parse_two_house_reason({"two_house_reason": word}) == want, word
assert parse_two_house_reason({}) == "temporary"
assert raises("parent_care", two_house_reason="상속") is True

# 2) 정상 충족
assert check("parent_care")["qualifies"] is True
assert check("marriage")["qualifies"] is True

# 3) 10년 경계 (양도일 2026-11-20): 합가일 2016-11-20이면 마지막 날, 2016-11-19이면 하루 초과
assert check("parent_care", merge_date="2016-11-20")["qualifies"] is True
assert check("parent_care", merge_date="2016-11-19")["qualifies"] is False
assert check("marriage", merge_date="2016-11-20")["qualifies"] is True
assert check("marriage", merge_date="2016-11-19")["qualifies"] is False

# 4) 요건 누락은 미충족 (입력이 없으면 안전한 쪽)
assert check("parent_care", parent_qualified="아니오")["qualifies"] is False
assert check("parent_care", was_separate_household="아니오")["qualifies"] is False
assert check("parent_care", one_house_each_before_merge="아니오")["qualifies"] is False
assert check("marriage", one_house_each_before_merge="아니오")["qualifies"] is False
r = check("parent_care", parent_qualified="아니오", was_separate_household="아니오")
assert len(r["reasons"]) == 2

# 5) 혼인 합가에서는 부모 관련 질문이 필요 없다
assert check("marriage", parent_qualified="아니오", was_separate_household="아니오")["qualifies"] is True

# 6) 양도하는 주택을 합가 이후에 취득했다면 미충족
assert check("parent_care", acquisition_date="2023-01-01", merge_date="2022-03-01")["qualifies"] is False

# 7) 시행 시점: 2024-11-12 전 양도분은 자동 판정하지 않음
assert check("marriage", transfer_date="2024-11-11", merge_date="2022-01-01")["qualifies"] is False
assert check("marriage", transfer_date="2024-11-12", merge_date="2022-01-01")["qualifies"] is True

# 8) 자료 모순은 입력 오류
assert raises("marriage", merge_date="")                    # 누락
assert raises("marriage", merge_date="2027-01-01")          # 양도일보다 늦음

print("모든 테스트 통과")
