"""양도소득세 계산기 - 5단계: 세율 적용, 지방소득세, 최종 세액 (1차 범위: 국내 주택, 1세대 1주택 중심)"""

from core import load_rules, tax_by_formula, local_income_tax
from exemption import STATUS_LABELS, describe, format_won, judge_exemption, parse_scope
from inputs import compute_periods, normalize_case
from tax_base import calc_tax_base, describe_base
from merged_household import REASON_TITLES, check_merged_household, parse_two_house_reason
from temporary_two import check_temporary_two_house

NOTICE = ("※ 입력하신 내용만으로 계산한 참고용 결과입니다. 실제 신고 세액은 세대 구성, 보유 주택 수, "
          "취득·양도 시기, 필요경비 증빙 등에 따라 달라질 수 있으니 신고 전 세무사 확인을 권장합니다.")


def pick_rate(exemption_status, holding, rules):
    """적용 세율을 고른다. 반환: ('short', 세율%) 또는 ('basic', None)

    비과세 요건을 못 채운 주택을 2년 안에 팔면 단기보유 세율(1년 미만 70%, 2년 미만 60%),
    그 밖에는 기본세율(6~45%)을 쓴다.
    """
    if exemption_status == "TAXABLE":
        for rule in rules["short_term_rates_house"]:
            if holding < rule["under_years"]:
                return "short", rule["rate_pct"]
    return "basic", None


def calculate(raw, rules=None, basic_deduction_available=True):
    """입력값(dict)으로 양도소득세를 끝까지 계산한다. 입력 오류는 ValueError.

    반환 dict: status(판정), exemption, periods, base(과세표준 계산 과정),
               rate_kind, rate_pct, income_tax(산출세액), local_tax(지방소득세), total_tax(합계)
    '상담 필요' 사례는 세액 없이(None) 판정 결과만 돌려준다.
    """
    rules = rules or load_rules()
    case = normalize_case(raw)
    periods = compute_periods(case)
    scope = parse_scope(raw)

    # 세대 보유 주택이 2채이면 2주택이 된 이유(신규주택/동거봉양/혼인)에 맞는 특례 요건부터 확인한다.
    temp = None
    if scope["house_count"] == 2:
        reason = parse_two_house_reason(raw)
        title = REASON_TITLES[reason]
        if reason == "temporary":
            temp = check_temporary_two_house(case, raw, rules)
        else:
            temp = check_merged_household(case, raw, rules, reason)
        if temp["qualifies"]:
            scope = dict(scope, house_count=1)  # 특례: 양도하는 주택을 1세대 1주택으로 본다
        else:
            exemption = {"status": "CONSULT", "label": STATUS_LABELS["CONSULT"],
                         "taxable_ratio": None, "reasons": [f"{title} 요건을 충족하지 못했습니다."]
                         + temp["reasons"]
                         + ["이 경우 2주택자의 양도로 보아 조정대상지역 중과 등 별도 검토가 필요해 "
                            "자동 계산하지 않습니다. 상담이 필요합니다."]}
            return {"status": "CONSULT", "exemption": exemption, "periods": periods, "base": None,
                    "rate_kind": None, "rate_pct": None, "income_tax": None, "local_tax": None,
                    "total_tax": None, "temporary_two": temp}

    exemption = judge_exemption(case, periods, scope, rules)
    if temp is not None:
        if exemption["status"] == "TAXABLE":
            # 특례 요건은 맞지만 양도하는 주택이 1세대 1주택 비과세 요건(보유 2년, 거주 2년)을 못 채운 경우
            exemption = {"status": "CONSULT", "label": STATUS_LABELS["CONSULT"], "taxable_ratio": None,
                         "reasons": temp["reasons"]
                         + ["그러나 양도하는 주택이 1세대 1주택 비과세 요건을 충족하지 못했습니다."]
                         + exemption["reasons"]
                         + ["이 경우 2주택자의 양도로 과세될 수 있어 조정대상지역 중과 등 별도 검토가 필요합니다. "
                            "자동 계산하지 않으니 상담이 필요합니다."]}
        else:
            exemption = dict(exemption, reasons=temp["reasons"] + exemption["reasons"])
    result = {"status": exemption["status"], "exemption": exemption, "periods": periods,
              "base": None, "rate_kind": None, "rate_pct": None,
              "income_tax": None, "local_tax": None, "total_tax": None, "temporary_two": temp}
    if exemption["status"] == "CONSULT":
        return result

    base = calc_tax_base(case, periods, exemption, rules, basic_deduction_available)
    kind, short_pct = pick_rate(exemption["status"], periods["holding_years"], rules)
    if base["tax_base"] <= 0:
        income_tax = 0
    elif kind == "short":
        income_tax = base["tax_base"] * short_pct // 100
    else:
        income_tax = tax_by_formula(base["tax_base"], rules["basic_rates"])
    local_tax = local_income_tax(income_tax, rules)
    result.update({"base": base, "rate_kind": kind, "rate_pct": short_pct,
                   "income_tax": income_tax, "local_tax": local_tax,
                   "total_tax": income_tax + local_tax})
    return result


def describe_result(r):
    """계산 결과 전체를 사람이 읽는 문장으로 만든다."""
    lines = [describe(r["exemption"])]
    if r["status"] == "CONSULT":
        lines += ["", "→ 이 사례는 자동 계산하지 않습니다. 세무사 상담을 이용해 주세요."]
    else:
        lines += ["", "[과세표준 계산]", describe_base(r["base"]), "", "[세액 계산]"]
        if r["base"]["tax_base"] <= 0:
            lines.append("과세표준이 0원이라 납부할 세금이 없습니다.")
        else:
            rate_text = (f"단기보유 세율 {r['rate_pct']}%" if r["rate_kind"] == "short"
                         else "기본세율(6~45% 누진)")
            lines += [f"적용 세율: {rate_text}",
                      f"{'양도소득세(산출세액)':<22}{format_won(r['income_tax']):>20}",
                      f"{'지방소득세(10%)':<22}{format_won(r['local_tax']):>20}",
                      f"{'납부할 세금 합계':<22}{format_won(r['total_tax']):>20}",
                      "", "신고·납부: 양도일이 속하는 달의 말일부터 2개월 이내 (예정신고)"]
    lines += ["", NOTICE]
    return "\n".join(lines)


if __name__ == "__main__":
    demo = {
        "acquisition_date": "2018-05-10", "transfer_date": "2026-11-20",
        "acquisition_price": "5억", "transfer_price": "15억",
        "residence_start": "2018-05-10", "residence_end": "2026-11-20",
    }
    print(describe_result(calculate(demo)))
