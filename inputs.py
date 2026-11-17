"""양도소득세 계산기 - 2단계: 입력 파싱/검증과 보유·거주 기간 계산"""

import re
from datetime import date

# 기간 계산 기준 (세무사 확인 필요한 지점이라 한 곳에서 바꿀 수 있게 분리)
#   "anniversary_inclusive": 취득일의 N년 후 같은 날(응당일) 당일부터 N년 충족
#   "anniversary_next_day" : 응당일의 다음 날부터 N년 충족
PERIOD_RULE = "anniversary_inclusive"


# ---------- 문자열 -> 값 ----------

def parse_date(text):
    """'2020-03-15', '2020.3.15', '2020/3/15', '20200315'를 date로 바꾼다."""
    s = str(text).strip()
    m = re.fullmatch(r"([0-9]{4})[-./]([0-9]{1,2})[-./]([0-9]{1,2})", s) or \
        re.fullmatch(r"([0-9]{4})([0-9]{2})([0-9]{2})", s)
    if not m:
        raise ValueError("날짜 형식 오류: 2020-03-15 또는 20200315 형태로 입력하세요.")
    y, mo, d = (int(g) for g in m.groups())
    try:
        return date(y, mo, d)
    except ValueError:
        raise ValueError(f"존재하지 않는 날짜입니다: {y}년 {mo}월 {d}일")


def parse_won(text):
    """'1,200,000,000', '12억', '12억5000만원', '5000만' 같은 금액을 원 단위 정수로 바꾼다."""
    s = str(text).strip().replace(",", "").replace(" ", "")
    if s.endswith("원"):
        s = s[:-1]
    if not s:
        raise ValueError("금액을 입력하세요.")
    if re.fullmatch(r"[0-9]+", s):
        return int(s)
    m = re.fullmatch(r"(?:([0-9]+)억)?(?:([0-9]+)만)?([0-9]+)?", s)
    if not m or not any(m.groups()):
        raise ValueError("금액 형식 오류: 숫자만, 또는 '12억', '12억5000만'처럼 입력하세요.")
    eok, man, rest = m.groups()
    if rest and (eok or man):
        raise ValueError("금액 형식 오류: '억/만' 뒤에 단위 없는 숫자를 붙일 수 없습니다.")
    return int(eok or 0) * 10**8 + int(man or 0) * 10**4 + int(rest or 0)


# ---------- 기간 계산 ----------

def add_years(d, years):
    """d의 N년 후 같은 날(응당일). 2월 29일처럼 해당 날짜가 없으면 그 달의 말일."""
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        return date(d.year + years, d.month, 28)


def full_years(start, end, rule=None):
    """start부터 end까지 채워진 만 연수. end가 start보다 앞서면 ValueError."""
    rule = rule or PERIOD_RULE
    if end < start:
        raise ValueError("종료일이 시작일보다 앞섭니다.")
    years = end.year - start.year
    while years > 0:
        anniversary = add_years(start, years)
        ok = end >= anniversary if rule == "anniversary_inclusive" else end > anniversary
        if ok:
            break
        years -= 1
    return max(years, 0)


# ---------- 사건 전체 검증 ----------

def normalize_case(raw):
    """고객이 입력한 값(문자열 가능)을 검증해서 표준 dict로 돌려준다. 오류는 ValueError.

    필수: acquisition_date, transfer_date, acquisition_price, transfer_price
    선택: expenses(기본 0), residence_start, residence_end, regulated_at_acquisition(기본 False)
    """
    case = {}
    try:
        case["acquisition_date"] = parse_date(raw["acquisition_date"])
        case["transfer_date"] = parse_date(raw["transfer_date"])
        case["acquisition_price"] = parse_won(raw["acquisition_price"])
        case["transfer_price"] = parse_won(raw["transfer_price"])
    except KeyError as e:
        raise ValueError(f"필수 입력 누락: {e.args[0]}")

    if case["transfer_date"] < case["acquisition_date"]:
        raise ValueError("양도일이 취득일보다 앞섭니다.")
    if case["acquisition_price"] <= 0 or case["transfer_price"] <= 0:
        raise ValueError("취득가액과 양도가액은 0보다 커야 합니다.")

    case["expenses"] = parse_won(raw.get("expenses", 0))

    rs, re_ = raw.get("residence_start"), raw.get("residence_end")
    if (rs in (None, "")) != (re_ in (None, "")):
        raise ValueError("거주 시작일과 종료일은 함께 입력해야 합니다.")
    if rs in (None, ""):
        case["residence_start"] = case["residence_end"] = None
    else:
        case["residence_start"] = parse_date(rs)
        case["residence_end"] = parse_date(re_)
        if case["residence_end"] < case["residence_start"]:
            raise ValueError("거주 종료일이 시작일보다 앞섭니다.")
        if case["residence_start"] < case["acquisition_date"] or \
           case["residence_end"] > case["transfer_date"]:
            raise ValueError("거주기간이 보유기간(취득일~양도일)을 벗어납니다.")

    flag = raw.get("regulated_at_acquisition", False)
    if isinstance(flag, str):
        flag = flag.strip().lower() in ("y", "yes", "예", "네", "true", "1")
    case["regulated_at_acquisition"] = bool(flag)
    return case


def compute_periods(case):
    """보유·거주 만 연수를 계산해 dict로 반환한다. (normalize_case 결과를 받는다)"""
    holding = full_years(case["acquisition_date"], case["transfer_date"])
    if case["residence_start"] is None:
        residence = 0
    else:
        residence = full_years(case["residence_start"], case["residence_end"])
    return {"holding_years": holding, "residence_years": residence}