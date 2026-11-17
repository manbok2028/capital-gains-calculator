"""양도소득세 계산기 - 3단계: 1세대 1주택 비과세 판정 (1차 범위: 국내 주택, 매매 취득)"""

from datetime import date
from fractions import Fraction

# 취득 당시 조정대상지역이면 '거주 2년' 요건이 붙는 취득일 기준 (소득세법 시행령 제154조) - 원문 재확인 필요
RESIDENCE_REQ_FROM = date(2017, 8, 3)

STATUS_LABELS = {
    "EXEMPT": "비과세",
    "HIGH_VALUE_PARTIAL": "고가주택 일부 과세",
    "TAXABLE": "과세 (비과세 요건 미충족)",
    "CONSULT": "상담 필요",
}

_PURCHASE_WORDS = {"purchase", "매매", "구입", "매수", "일반매매"}
_OTHER_WORDS = {
    "inheritance": "상속", "상속": "상속",
    "gift": "증여", "증여": "증여",
    "other": "기타", "기타": "기타",
}


def format_won(n):
    """1350000000 -> '13억 5,000만원'"""
    if n == 0:
        return "0원"
    eok, rest = divmod(n, 10**8)
    man, won = divmod(rest, 10**4)
    parts = []
    if eok:
        parts.append(f"{eok:,}억")
    if man:
        parts.append(f"{man:,}만")
    if won:
        parts.append(f"{won:,}")
    return " ".join(parts) + "원"


def parse_scope(raw):
    """자동 계산 범위를 가르는 입력(세대 보유 주택 수, 취득 원인)을 검증한다."""
    try:
        house_count = int(str(raw.get("house_count", 1)).strip())
    except ValueError:
        raise ValueError("세대 보유 주택 수는 숫자로 입력하세요.")
    if house_count < 1:
        raise ValueError("세대 보유 주택 수는 1 이상이어야 합니다. (양도하는 주택 포함)")

    word = str(raw.get("acquisition_type", "purchase")).strip().lower()
    if word in _PURCHASE_WORDS:
        kind = "purchase"
    elif word in _OTHER_WORDS:
        kind = _OTHER_WORDS[word]
    else:
        raise ValueError("취득 원인은 매매, 상속, 증여, 기타 중에서 입력하세요.")
    return {"house_count": house_count, "acquisition_type": kind}


def _result(status, reasons, taxable_ratio=None):
    return {"status": status, "label": STATUS_LABELS[status],
            "reasons": reasons, "taxable_ratio": taxable_ratio}


def judge_exemption(case, periods, scope, rules):
    """1세대 1주택 비과세 여부를 판정한다.

    case: inputs.normalize_case() 결과, periods: inputs.compute_periods() 결과,
    scope: parse_scope() 결과. 반환: status, label, reasons(이유 문장 목록), taxable_ratio.
    """
    ex = rules["exemption"]
    threshold = ex["high_value_house_threshold"]
    holding, residence = periods["holding_years"], periods["residence_years"]

    # 1) 자동 계산 범위 밖은 계산하지 않고 상담으로 안내
    consult = []
    if scope["house_count"] != 1:
        consult.append(f"세대 전체 보유 주택이 {scope['house_count']}채입니다. "
                       "일시적 2주택·다주택은 자동 판정 범위 밖이라 상담이 필요합니다.")
    if scope["acquisition_type"] != "purchase":
        consult.append(f"취득 원인이 '{scope['acquisition_type']}'입니다. "
                       "상속·증여 등으로 취득한 주택은 자동 판정 범위 밖이라 상담이 필요합니다.")
    if consult:
        return _result("CONSULT", consult)

    # 2) 비과세 요건 확인 (미충족 사유를 모두 모은다)
    fails = []
    if holding < ex["min_holding_years"]:
        fails.append(f"보유기간이 {holding}년으로 {ex['min_holding_years']}년 미만입니다.")

    need_residence = ex["min_residence_years_if_regulated_at_acquisition"]
    if (case["regulated_at_acquisition"]
            and case["acquisition_date"] >= RESIDENCE_REQ_FROM
            and residence < need_residence):
        fails.append(f"취득 당시 조정대상지역이라 거주 {need_residence}년 이상이 필요한데 "
                     f"거주기간은 {residence}년입니다.")
    if fails:
        return _result("TAXABLE", fails)

    # 3) 요건 충족: 12억 이하는 전부 비과세, 초과하면 초과분 비율만 과세
    price = case["transfer_price"]
    base_reason = f"보유기간 {holding}년으로 비과세 요건을 충족합니다."
    if price <= threshold:
        return _result("EXEMPT", [
            base_reason,
            f"양도가액 {format_won(price)}이 {format_won(threshold)} 이하라 전액 비과세입니다."])

    ratio = Fraction(price - threshold, price)
    return _result("HIGH_VALUE_PARTIAL", [
        base_reason,
        f"양도가액 {format_won(price)}이 {format_won(threshold)}을 넘는 고가주택입니다.",
        f"초과분 {format_won(price - threshold)}에 해당하는 비율({ratio.numerator}/{ratio.denominator})의 "
        "양도차익만 과세됩니다."], ratio)


def describe(result):
    """판정 결과를 사람이 읽을 수 있는 문장으로 만든다."""
    lines = [f"판정: {result['label']}"]
    lines += [f"- {r}" for r in result["reasons"]]
    return "\n".join(lines)


if __name__ == "__main__":
    from inputs import normalize_case, compute_periods
    from core import load_rules

    rules = load_rules()
    raw = {
        "acquisition_date": "2018-05-10", "transfer_date": "2026-11-20",
        "acquisition_price": "5억", "transfer_price": "13억5000만",
        "residence_start": "2018-05-10", "residence_end": "2026-11-20",
        "regulated_at_acquisition": "예",
    }
    case = normalize_case(raw)
    print(describe(judge_exemption(case, compute_periods(case), parse_scope(raw), rules)))