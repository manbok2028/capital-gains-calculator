"""2단계 검증: 입력 파싱, 기간 경계, 사건 검증"""

from datetime import date

import inputs
from inputs import parse_date, parse_won, add_years, full_years, normalize_case, compute_periods


def raises(func, *args):
    try:
        func(*args)
    except ValueError:
        return True
    return False


# 1) 날짜 파싱
assert parse_date("2020-03-15") == date(2020, 3, 15)
assert parse_date("2020.3.5") == date(2020, 3, 5)
assert parse_date("20200315") == date(2020, 3, 15)
for bad in ("2020-13-01", "2021.02.29", "abc", "", "2020-3", "２０２０-03-15"):
    assert raises(parse_date, bad), bad

# 2) 금액 파싱
assert parse_won("1,200,000,000원") == 1_200_000_000
assert parse_won("12억") == 1_200_000_000
assert parse_won("12억5000만") == 1_250_000_000
assert parse_won("5000만원") == 50_000_000
assert parse_won("0") == 0
for bad in ("", "-5", "12.5억", "abc", "12억5", "억"):
    assert raises(parse_won, bad), bad

# 3) 응당일 (윤년 포함)
assert add_years(date(2020, 3, 15), 2) == date(2022, 3, 15)
assert add_years(date(2020, 2, 29), 1) == date(2021, 2, 28)
assert add_years(date(2020, 2, 29), 4) == date(2024, 2, 29)

# 4) 기간 경계 - 기본 규칙(응당일 당일 충족)
a = date(2020, 3, 15)
assert full_years(a, a) == 0
assert full_years(a, date(2022, 3, 14)) == 1
assert full_years(a, date(2022, 3, 15)) == 2
assert full_years(a, date(2023, 3, 14)) == 2
assert full_years(a, date(2023, 3, 15)) == 3
assert full_years(a, date(2030, 3, 15)) == 10
assert raises(full_years, date(2022, 1, 1), date(2021, 1, 1))

# 5) 기간 경계 - 다음 날 규칙
assert full_years(a, date(2022, 3, 15), "anniversary_next_day") == 1
assert full_years(a, date(2022, 3, 16), "anniversary_next_day") == 2

# 6) 윤일 취득
leap = date(2020, 2, 29)
assert full_years(leap, date(2021, 2, 27)) == 0
assert full_years(leap, date(2021, 2, 28)) == 1

# 7) 사건 검증
ok = {
    "acquisition_date": "2018-05-10", "transfer_date": "2026-11-20",
    "acquisition_price": "5억", "transfer_price": "13억5000만",
    "expenses": "3,000만원",
    "residence_start": "2018-05-10", "residence_end": "2026-11-20",
    "regulated_at_acquisition": "예",
}
c = normalize_case(ok)
assert c["transfer_price"] == 1_350_000_000 and c["expenses"] == 30_000_000
assert c["regulated_at_acquisition"] is True
assert compute_periods(c) == {"holding_years": 8, "residence_years": 8}

# 선택 항목 생략
c2 = normalize_case({"acquisition_date": "2020-01-01", "transfer_date": "2022-01-01",
                     "acquisition_price": "3억", "transfer_price": "4억"})
assert c2["expenses"] == 0 and c2["residence_start"] is None
assert compute_periods(c2) == {"holding_years": 2, "residence_years": 0}

# 오류 사례
def with_(**kw):
    d = dict(ok)
    d.update(kw)
    return d

assert raises(normalize_case, with_(transfer_date="2018-01-01"))            # 양도일 < 취득일
assert raises(normalize_case, with_(acquisition_price="0"))                 # 0원
assert raises(normalize_case, with_(residence_end=""))                      # 한쪽만 입력
assert raises(normalize_case, with_(residence_start="2017-01-01"))          # 보유기간 밖
assert raises(normalize_case, with_(residence_end="2027-01-01"))            # 보유기간 밖
assert raises(normalize_case, {"acquisition_date": "2020-01-01"})           # 필수 누락

print("모든 테스트 통과")