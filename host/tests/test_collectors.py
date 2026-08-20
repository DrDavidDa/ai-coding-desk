from asr import parse_asr_json
from collectors.glm import parse_quota_json
from collectors.claude import parse_claude_usage, parse_deepseek_balance
from collectors.codex import parse_codex_usage
from collectors.cursor import parse_cursor_summary
from collectors.kimi import parse_kimi_usage
from collectors.trae import parse_trae_usage
from collectors.coze import parse_coze_benefits
from collectors.util import normalize_win_proxy, parse_clash_mixed_port


def test_asr_json_text_field():
    assert parse_asr_json({"text": "put jwt"}) == "put jwt"
    assert parse_asr_json({"data": {"text": "hi"}}) == "hi"
    assert parse_asr_json({"text": "<|zh|><|NEUTRAL|><|Speech|>把登录改成 JWT"}) == "把登录改成 JWT"


SAMPLE_GLM = {
    "code": 200,
    "data": {
        "limits": [
            {"type": "TOKENS_LIMIT", "unit": 3, "number": 5, "percentage": 15, "nextResetTime": 1786249956626},
            {"type": "TOKENS_LIMIT", "unit": 6, "number": 1, "percentage": 24, "nextResetTime": 1786230000000},
            {"type": "TIME_LIMIT", "unit": 5, "number": 1, "percentage": 20, "nextResetTime": 1786316400000},
        ],
        "level": "pro",
    },
    "success": True,
}


def test_glm_limits_order():
    q = parse_quota_json(SAMPLE_GLM)
    assert q["ok"] is True
    assert q["h5"] == 15
    assert q["d7"] == 24
    assert q["mcp"] == 20
    assert q["reset_h5"] == 1786249956


def test_glm_keeps_prev_on_bad_code():
    prev = {"h5": 40, "d7": 10, "ok": True}
    q = parse_quota_json({"code": 401}, prev)
    assert q["h5"] == 40
    assert q["ok"] is False
    assert q["err"] == "http"


def test_claude_header_style_fraction():
    q = parse_claude_usage({"five_hour_utilization": 0.42, "seven_day_utilization": 0.17})
    assert q["h5"] == 42
    assert q["d7"] == 17
    assert q["ok"] is True


def test_claude_five_hour_dict_and_zero():
    q = parse_claude_usage(
        {
            "five_hour": {"utilization": 0, "resets_at": "2026-08-20T12:00:00Z"},
            "seven_day": {"utilization": 12.4, "resets_at": "2026-08-24T12:00:00Z"},
        }
    )
    assert q["ok"] is True
    assert q["h5"] == 0
    assert q["d7"] == 12
    assert q["reset_h5"] > 0


def test_claude_empty_body_not_ok():
    q = parse_claude_usage({"error": {"type": "forbidden"}})
    assert q["ok"] is False


def test_deepseek_balance_cents():
    q = parse_deepseek_balance(
        {
            "is_available": True,
            "balance_infos": [
                {"currency": "CNY", "total_balance": "2.37", "granted_balance": "0.00", "topped_up_balance": "2.37"}
            ],
        }
    )
    assert q["ok"] is True
    assert q["daily_tokens"] == 237
    assert "h5" not in q
    assert "d7" not in q


def test_codex_used_percent():
    q = parse_codex_usage(
        {
            "rate_limits": {
                "primary_window": {"used_percent": 8, "reset_at": 100},
                "secondary_window": {"used_percent": 31, "reset_at": 200},
            }
        }
    )
    assert q["h5"] == 8
    assert q["d7"] == 31
    assert q["reset_h5"] == 100


def test_codex_plus_weekly_primary_window():
    q = parse_codex_usage(
        {
            "plan_type": "plus",
            "rate_limit": {
                "primary_window": {
                    "used_percent": 50,
                    "limit_window_seconds": 604800,
                    "reset_at": 1787716793,
                },
                "secondary_window": None,
            },
        }
    )
    assert q["ok"] is True
    assert q["d7"] == 50
    assert "h5" not in q
    assert q["reset_d7"] == 1787716793
    assert "reset_h5" not in q


def test_normalize_win_proxy():
    assert normalize_win_proxy("127.0.0.1:7897") == "http://127.0.0.1:7897"
    assert normalize_win_proxy("http=127.0.0.1:7897;https=127.0.0.1:7897") == "http://127.0.0.1:7897"
    assert normalize_win_proxy("") is None


def test_parse_clash_mixed_port():
    assert parse_clash_mixed_port("verge_mixed_port: 7897\n") == 7897
    assert parse_clash_mixed_port("mixed-port: 7890\nallow-lan: false\n") == 7890
    assert parse_clash_mixed_port("") is None


def test_cursor_summary():
    q = parse_cursor_summary({"autoPercentUsed": 37, "apiPercentUsed": 80, "billingCycleEnd": 9})
    assert q["auto_pct"] == 37
    assert q["api_pct"] == 80
    assert q["ok"] is True


def test_cursor_individual_usage_plan():
    q = parse_cursor_summary(
        {
            "billingCycleEnd": "2026-09-16T07:22:20.000Z",
            "individualUsage": {
                "plan": {
                    "autoPercentUsed": 92.14,
                    "apiPercentUsed": 100,
                    "totalPercentUsed": 93.24,
                }
            },
        }
    )
    assert q["auto_pct"] == 92
    assert q["api_pct"] == 100
    assert q["total_pct"] == 93
    assert q["cycle_end"] > 1700000000
    assert q["ok"] is True


def test_kimi_remaining_to_used():
    q = parse_kimi_usage(
        {
            "usage": {"limit": "100", "remaining": "74", "resetTime": "2026-08-24T03:24:20Z"},
            "limits": [
                {
                    "window": {"duration": 300, "timeUnit": "TIME_UNIT_MINUTE"},
                    "detail": {"limit": "100", "remaining": "85", "resetTime": "2026-08-20T09:24:20Z"},
                }
            ],
        }
    )
    assert q["ok"] is True
    assert q["d7"] == 26
    assert q["h5"] == 15


def test_trae_credits_ignores_empty_usage_packs():
    q = parse_trae_usage(
        {
            "is_credits_billing": True,
            "user_entitlement_pack_list": [
                {
                    "entitlement_base_info": {
                        "end_time": 1788767022,
                        "quota": {"credits_limit": 2000},
                    },
                    "usage": {},
                },
                {
                    "entitlement_base_info": {
                        "end_time": 1788191999,
                        "quota": {"credits_limit": 500},
                    },
                    "usage": {"credits_amount": 136.6028},
                },
            ],
        }
    )
    assert q["ok"] is True
    assert q["h5"] == 27
    assert q["left"] == 363
    assert q["cap"] == 500
    assert q["reset_h5"] == 1788191999


def test_trae_empty_pack_list_not_ok():
    q = parse_trae_usage({"user_entitlement_pack_list": "nope"}, {"ok": True, "h5": 10})
    assert q["ok"] is False
    assert q["err"] == "parse"
    assert q["h5"] == 10


def test_coze_tool_limit_and_plan():
    q = parse_coze_benefits(
        {
            "code": 0,
            "data": {
                "basic_info": {"user_level": "pro_personal"},
                "benefit_info": [
                    {
                        "benefit_type": "call_tool_limit",
                        "basic": {
                            "item_info": {
                                "used": 0,
                                "total": 1000,
                                "end_at": 1788191999,
                                "strategy": "by_quota",
                            }
                        },
                    }
                ],
            },
        }
    )
    assert q["ok"] is True
    assert q["h5"] == 0
    assert q["left"] == 1000
    assert q["cap"] == 1000
    assert q["reset_h5"] == 1788191999
    assert q["plan"] == "pro_personal"


def test_coze_plan_only_no_fake_windows():
    q = parse_coze_benefits({"code": 0, "data": {"basic_info": {"user_level": "pro_personal"}}})
    assert q["ok"] is True
    assert "h5" not in q
    assert q["plan"] == "pro_personal"
