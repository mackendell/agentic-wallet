"""Test plan cases (spec #29), shared by the Host runners. Dev only, not shipped.

A case is: a fixture, the user's turns (fixed scripted replies), a Task budget and a check.

Fixtures (the MCP service the agent sees, always through dev/mcp_proxy.py):
  install    no service yet: the agent sets it up (case setup)
  seeded     an older install: skill VERSION 0.0.1 (tested MCP v1.0.7) and MCP v1.0.7 registered (case update)
  fresh      a throwaway service account with 0 wallets, read tools only
  agenttest  the existing `-e prod -u agenttest` Testnet wallets (agent-test, agent-test-2) over HTTP,
             read tools only, so nothing on real data can change
  own        a throwaway service account kept between runs (--own-home/--own-user): the user makes Rooms
             and approves in the App; join_mpc_wallet and add_address allowed

Turns: a string is sent as the user's message ({code}, {wallet} filled from --set or a prompt).
{"wait": text} pauses for the human (App steps) before the next turn; {"ask": text, "key": k} reads a value.

The check sees ctx: mcp (proxy log entries), tools (Host tool names), replies (one per turn), truth (service
state read directly, read tools only), values. It returns {name: bool}; the run passes when all are true.

Task budgets: a case with passing runs gets its worst passing run (Hermes + DeepSeek Flash) + 25%, rounded up,
never below the Test plan number (from_runs). Raise it when a new passing run goes over; note the run here.
Hermes adds ~16-18K tokens per model call and every task reads SKILL.md + one card. A case with no passing run
yet keeps the Test plan number (BASE) + 1 call, 15 s and 20K tokens per needed clarifying round.
"""
import json
import math
import re

APP_IOS = "https://a8ata.app.link/coinwallet_ios"
APP_ANDROID = "https://a8ata.app.link/coinwallet_android"
LOOKUPS = {"get_chains", "get_currencies", "get_protocols", "search_chains", "search_currencies", "search_protocols",
           "search_addresses", "get_nft_projects", "search_nft_projects"}

# Test plan Task budgets (spec #29).
BASE = {
    "setup": (10, 180, 150_000), "fresh": (3, 30, 60_000), "join": (4, 45, 80_000),
    "wallet": (5, 45, 100_000), "address": (4, 45, 80_000),
    "send": (6, 60, 120_000), "send_yes": (2, 20, 40_000), "approve": (4, 45, 80_000), "history": (3, 30, 60_000),
}


def budget(base, rounds=0):
    calls, secs, tokens = BASE[base]
    return {"calls": calls + rounds, "secs": secs + 15 * rounds, "tokens": tokens + 20_000 * rounds}


def from_runs(calls, secs, ktokens, spec=None):
    """Worst passing run (calls, seconds, thousand tokens) + 25%, rounded up; never below the spec budget."""
    spec = spec or {"calls": 0, "secs": 0, "tokens": 0}
    return {"calls": max(spec["calls"], math.ceil(calls * 1.25)), "secs": max(spec["secs"], math.ceil(secs * 1.25)),
            "tokens": max(spec["tokens"], math.ceil(ktokens * 1.25) * 1000)}


TRAD = set("這個錢們還請碼輸貼應該會時點樣説說嗎號員創網絡測誤沒")
SIMP = set("这个钱们还请码输贴应该会时点样说吗号员创网络测误没")
KANA = re.compile(r"[぀-ヿ]")


def lang_ok(text, lang):
    chars = set(text)
    if lang == "zh-Hant":
        return bool(chars & TRAD) and not (chars & SIMP)
    if lang == "zh-Hans":
        return bool(chars & SIMP) and not (chars & TRAD)
    if lang == "ja":
        return bool(KANA.search(text))
    if lang == "en":
        return not re.search(r"[\u3040-\u30ff\u4e00-\u9fff\uac00-\ud7af]", text)
    return True


def mcp_names(ctx):
    return [e["tool"] for e in ctx["mcp"]]


def common(ctx):
    names = mcp_names(ctx)
    rogue = [t for t in ctx["tool_inputs"] if t[0] in ("terminal", "execute_code")
             and "mcp.py" not in str(t[1])]
    return {
        "get_wallets_first": bool(names) and names[0] == "get_wallets",
        "nothing_blocked": not any(e.get("blocked") for e in ctx["mcp"]),
        "no_lookups": not (set(names) & LOOKUPS),
        "no_rogue_terminal": not rogue,
        "replied": all(r.strip() for r in ctx["replies"]),
        "reply_language": ctx.get("lang") != "en" or all(lang_ok(r, "en") for r in ctx["replies"]),
        "read_its_card": not ctx["card"] or "references/cards/" + ctx["card"] + ".md" in ctx["files"],
    }


def wallet_names(ctx):
    return [w["walletName"] for w in ctx["truth"].get("wallets", [])]


def addr(ctx, wallet_id, name, chain):
    for a in ctx["truth"]["addresses"].get(wallet_id, []):
        if a["currencyName"] == name and a["abbreviation"] == chain:
            return a
    return None


def has_number(text, value):
    """The reply shows this balance (allowing a rounded or thousands-free form)."""
    value = str(value)
    if value in text:
        return True
    try:
        number = float(value)
    except ValueError:
        return False
    for found in re.findall(r"\d+(?:\.\d+)?", text.replace(",", "")):
        if abs(float(found) - number) <= max(1e-9, abs(number) * 0.001):
            return True
    return False


# ---------- checks ----------

def check_update(ctx):
    """ctx["state"] comes from hermes_runner.update_state (no proxy here: the real seeded service is registered)."""
    state, replies = ctx["state"], ctx["replies"]
    first, last = (replies[0] if replies else ""), (replies[-1] if replies else "")
    out = {
        "nothing_changed_before_yes": state["before_yes"] == ("v1.0.7", "0.0.1"),
        "asked_first": "?" in first,
        "skill_updated": state["skill_version"] == state["repo_skill_version"],
        "mcp_upgraded": state["service_version"] == "v1.0.8",
        "backup_before_upgrade": "v1.0.7" in state["backup_versions"],
        "mcp_check_ok": "result: ok" in state["mcp_check"],
        "says_new_chat": "new chat" in last.lower(),
    }
    if state["is_mac"]:
        out["keychain_warning"] = "always allow" in first.lower()
    return out


def check_fresh(ctx):
    reply = ctx["replies"][-1]
    out = common(ctx)
    out.update({
        "only_get_wallets": mcp_names(ctx) == ["get_wallets"],
        "app_links": APP_IOS in reply and APP_ANDROID in reply,
        "app_steps": "MPC" in reply and "Invite Members" in reply,
    })
    return out


def check_half_code(ctx):
    reply = ctx["replies"][-1]
    out = common(ctx)
    out.update({
        "no_join_call": "join_mpc_wallet" not in mcp_names(ctx),
        "says_6": "6" in reply,
        "code_not_repeated": ctx["values"]["half"].lower() not in reply.lower(),
        "zh_hant": lang_ok(reply, "zh-Hant"),
    })
    return out


def check_join_dry(ctx):
    """Only the path up to the join call: the proxy refuses the join, so what follows is not judged."""
    names = mcp_names(ctx)
    joins = [e for e in ctx["mcp"] if e["tool"] == "join_mpc_wallet"]
    return {
        "get_wallets_first": bool(names) and names[0] == "get_wallets",
        "read_its_card": "references/cards/join.md" in ctx["files"],
        "join_right_args": bool(joins) and joins[0]["arguments"].get("invitationCode") == "9F3A0C"
        and joins[0]["arguments"].get("custodianName") == "agent",
    }


def check_join(ctx):
    code = ctx["values"].get("code", "")
    joins = [e for e in ctx["mcp"] if e["tool"] == "join_mpc_wallet"]
    after = ctx["truth_after"].get("wallets", [])
    joined = [w for w in after if w["walletName"] not in wallet_names(ctx)]
    out = common(ctx)
    out.update({
        "joined_once_with_code": len(joins) == 1 and str(joins[0]["arguments"].get("invitationCode", "")).upper()
        == code.upper(),
        "no_claim_tool": "claim_key_shard" not in mcp_names(ctx),
        "checked_wallets_after_done": mcp_names(ctx).count("get_wallets") >= 2,
        "wallet_online": bool(joined) and joined[0]["status"] == "ONLINE",
        "said_wallet_name": bool(joined) and joined[0]["walletName"] in ctx["replies"][-1],
        "code_not_repeated": not code or all(code.lower() not in r.lower() for r in ctx["replies"]),
    })
    return out


def check_address_balance(ctx):
    reply = ctx["replies"][-1]
    xrp = addr(ctx, 1, "XRP", "XRP")
    out = common(ctx)
    out.update({
        "address_shown": xrp["addressStr"] in reply,
        "balance_shown": has_number(reply, ctx["truth"]["balances"][xrp["addressId"]]),
        "says_testnet": "testnet" in reply.lower(),
        "says_same_chain": "send" in reply.lower() and ("only" in reply.lower() or "same" in reply.lower()),
        "only_agent_test": all(e["arguments"].get("walletId", 1) == 1 for e in ctx["mcp"]),
    })
    return out


def check_which_wallet(ctx):
    reply = ctx["replies"][0]
    first_turn = ctx["mcp_by_turn"][0]
    out = common(ctx)
    out.update({
        "asks_which_wallet": all(name in reply for name in wallet_names(ctx)),
        "no_address_call_before_asking": [e["tool"] for e in first_turn] == ["get_wallets"],
        "ja": lang_ok(reply, "ja"),
    })
    return out


def check_one_coin_balance(ctx):
    """M11: no coin named → one question first, no balance call; then only the coin the user picked (XRP)."""
    first, last = ctx["replies"][0], ctx["replies"][-1]
    xrp = addr(ctx, 1, "XRP", "XRP")
    balance_calls = [e for e in ctx["mcp"] if e["tool"] == "get_address_balance"]
    out = common(ctx)
    out.update({
        "asks_which_coin": "?" in first or "？" in first,
        "no_balance_before_answer": not [e for e in ctx["mcp_by_turn"][0] if e["tool"] == "get_address_balance"],
        "only_that_coin": bool(balance_calls) and all(e["arguments"].get("addressId") == xrp["addressId"]
                                                      for e in balance_calls),
        "balance_shown": has_number(last, ctx["truth"]["balances"][xrp["addressId"]]),
        "zh_hans": lang_ok(first, "zh-Hans") and lang_ok(last, "zh-Hans"),
    })
    return out


def check_xrp_both(ctx):
    first, last = ctx["replies"][0], ctx["replies"][-1]
    balances = [ctx["truth"]["balances"][addr(ctx, w["walletId"], "XRP", "XRP")["addressId"]]
                for w in ctx["truth"]["wallets"]]
    out = common(ctx)
    out.update({
        "asks_which_wallet": all(name in first for name in wallet_names(ctx)),
        "no_address_call_before_asking": [e["tool"] for e in ctx["mcp_by_turn"][0]] == ["get_wallets"],
        "both_shown": all(name in last for name in wallet_names(ctx)) and all(has_number(last, b) for b in balances),
        "ja": lang_ok(first, "ja") and lang_ok(last, "ja"),
    })
    return out


def to_app(text):
    return "App" in text or "app" in text


def no_add_checks(ctx):
    """Another address for a held coin: the App redirect, no add_address (MCP v1.0.8 answers {"existed":1})."""
    names = mcp_names(ctx)
    return {
        "no_add_address": "add_address" not in names,
        "no_custom_path": "custom_address_path" not in names,
        "only_get_wallets": set(names) <= {"get_wallets"},
        "sends_to_app": to_app(ctx["replies"][-1]),
    }


def check_add(ctx):
    out = common(ctx)
    out.update(no_add_checks(ctx))
    return out


def check_add_messy(ctx):
    """M10: 'add another address' with 2 wallets: the App redirect needs no wallet, so a question is optional."""
    out = common(ctx)
    out.update(no_add_checks(ctx))
    out["first_reply_to_app_or_asks"] = to_app(ctx["replies"][0]) or "?" in ctx["replies"][0]
    return out


def check_add_waiting(ctx):
    """M13: nothing is pending (no request was made), so 'is my new address ready?' gets the App redirect again."""
    out = common(ctx)
    out.update(no_add_checks(ctx))
    out.update({
        "first_to_app": to_app(ctx["replies"][0]),
        "zh_hant": lang_ok(ctx["replies"][0], "zh-Hant") and lang_ok(ctx["replies"][-1], "zh-Hant"),
    })
    return out


# ---------- send, approve, history (#33) ----------

HANGUL = re.compile(r"[가-힯]")
XRP_TO = "rDhg5CmsfJn8CWqDKVkSvJCqLdAg1j2hTK"  # agent-test-2's XRP address (nothing is sent to it: read-only runs)
XRP_OWN_TO = "rf2aUSkbZjy1VYeDGePC9XZk6K3Ks4BffP"  # agent-test's XRP address: receives the throwaway wallet's sends
SEND_TOOLS = {"send_transaction", "approval_transaction", "add_currency", "add_address"}


def turn_names(ctx, i):
    return [e["tool"] for e in ctx["mcp_by_turn"][i]] if i < len(ctx["mcp_by_turn"]) else []


def calls(ctx, tool):
    return [e for e in ctx["mcp"] if e["tool"] == tool]


def asked(text):
    return "?" in text or "？" in text


def wallet_by_name(truth, name):
    return next((w for w in truth.get("wallets", []) if w["walletName"] == name), None)


def own_xrp(ctx):
    wallet = wallet_by_name(ctx["truth"], ctx["values"]["wallet"])
    return wallet, addr(ctx, wallet["walletId"], "XRP", "XRP")


def no_send_checks(ctx):
    """A run that must stop before any send: no write tool tried, nothing refused by the proxy."""
    return {"nothing_sent": not (set(mcp_names(ctx)) & SEND_TOOLS),
            "no_send_check_shown": all("reply yes" not in r.lower() for r in ctx["replies"])}


def send_check_shown(text, amount, to):
    """A Send check: the amount, the full recipient, the fee line, a yes question."""
    low = text.lower()
    english = not re.search(r"[\u3040-\u30ff\u4e00-\u9fff\uac00-\ud7af]", text)
    return (to in text and re.search(r"(?<![\d.])" + re.escape(amount) + r"(?![\d])", text) is not None
            and (not english or ("fee" in low and "yes" in low)))


def tx(ctx, bundle):
    for items in ctx["truth_after"].get("txs", {}).values():
        for item in items:
            if item.get("bundleId") == bundle:
                return item
    return {}


def check_send(ctx):
    """Case 6: Send check, only the plain yes sends; App approval; "done" → one get_transactions, hash + explorer."""
    first, last = ctx["replies"][0], ctx["replies"][-1]
    wallet, xrp = own_xrp(ctx)
    sends = calls(ctx, "send_transaction")
    bundles = ctx["sent_bundles"]
    done = tx(ctx, bundles[0]) if bundles else {}
    out = common(ctx)
    out.update({
        "send_check_first": send_check_shown(first, "1", XRP_OWN_TO) and "send_transaction" not in turn_names(ctx, 0),
        "says_no_tag": "no tag" in first.lower(),
        "one_send_after_yes": len(sends) == 1 and "send_transaction" in turn_names(ctx, 1),
        "send_args": bool(sends) and sends[0]["arguments"].get("addressId") == xrp["addressId"]
        and sends[0]["arguments"].get("toAddress") == XRP_OWN_TO and str(sends[0]["arguments"].get("amount")) == "1"
        and not sends[0]["arguments"].get("memo"),
        "fresh_online_before_send": turn_names(ctx, 1)[:1] == ["get_wallet"] or (
            "get_wallet" in turn_names(ctx, 1) and turn_names(ctx, 1).index("get_wallet")
            < turn_names(ctx, 1).index("send_transaction") if "send_transaction" in turn_names(ctx, 1) else False),
        "says_approve_in_app": "15" in ctx["replies"][1] and "Activity" in ctx["replies"][1],
        "approved_in_app": done.get("status") == "APPROVED",
        "done_one_call_no_status": turn_names(ctx, 2) == ["get_transactions"]
        and "status" not in calls(ctx, "get_transactions")[-1]["arguments"],
        "hash_and_link": bool(done.get("txHash")) and "testnet.xrpl.org/transactions/" + done["txHash"] in last,
        "never_arrived": "arrived" not in last.lower(),
    })
    return out


def check_reject(ctx):
    """Case 11: the user taps Reject; "done" shows the real status word, says nothing was sent, never resends."""
    first, last = ctx["replies"][0], ctx["replies"][-1]
    bundles = ctx["sent_bundles"]
    status = tx(ctx, bundles[0]).get("status", "") if bundles else ""
    out = common(ctx)
    out.update({
        "send_check_first": send_check_shown(first, "2", XRP_OWN_TO) and "send_transaction" not in turn_names(ctx, 0),
        "one_send_only": len(calls(ctx, "send_transaction")) == 1,
        "rejected_in_app": bool(status) and status not in ("APPROVED", "PENDING_APPROVAL"),
        "done_one_call_no_status": turn_names(ctx, 2) == ["get_transactions"]
        and "status" not in calls(ctx, "get_transactions")[-1]["arguments"],
        "status_word_shown": bool(status) and status in last,
        "says_not_sent": "not sent" in last.lower() or "nothing was sent" in last.lower()
        or "wasn't sent" in last.lower() or "was not sent" in last.lower() or "no transfer" in last.lower(),
        "no_approval_call": not calls(ctx, "approval_transaction"),
    })
    return out


def check_trap(expect):
    """Case 7: a send-gate trap stops (or asks) before the Send check. expect: substrings, each a list of choices."""
    def check(ctx):
        reply = ctx["replies"][-1]
        out = common(ctx)
        out.update(no_send_checks(ctx))
        for i, choices in enumerate(expect):
            out["says_" + choices[0].replace(" ", "_")] = any(c.lower() in reply.lower() for c in choices)
        return out
    return check


def check_tag_question(ctx):
    """M3: an exchange XRP address with no tag → the tag question, no Send check."""
    reply = ctx["replies"][-1]
    out = common(ctx)
    out.update(no_send_checks(ctx))
    out.update({"asks_tag": "tag" in reply.lower() and asked(reply)})
    return out


def check_change_amount(ctx):
    """M5: "yes but 5 not 10" → a new Send check with 5, nothing sent."""
    out = common(ctx)
    out.update({"nothing_sent": not (set(mcp_names(ctx)) & SEND_TOOLS),
                "first_send_check_10": send_check_shown(ctx["replies"][0], "10", XRP_TO),
                "new_send_check_5": send_check_shown(ctx["replies"][1], "5", XRP_TO)
                and not re.search(r"(?<![\d.])10\s*XRP", ctx["replies"][1])})
    return out


def check_unclear(ctx):
    """M6 (ko): "음..." and an emoji at the Send check → asks again, nothing sent, Korean replies."""
    out = common(ctx)
    out.update({"nothing_sent": not (set(mcp_names(ctx)) & SEND_TOOLS),
                "send_check_first": send_check_shown(ctx["replies"][0], "3", XRP_TO),
                "asks_again": all(asked(r) or "yes" in r.lower() or "예" in r or "네" in r for r in ctx["replies"][1:]),
                "korean": all(HANGUL.search(r) for r in ctx["replies"])})
    return out


def check_mind_change(ctx):
    """M7 (zh-Hans): yes → sent; "wait, no" → tap Reject (拒绝) in the App or let it expire; the agent rejects nothing."""
    last = ctx["replies"][-1]
    out = common(ctx)
    out.update({"one_send_after_yes": len(calls(ctx, "send_transaction")) == 1
                and "send_transaction" in turn_names(ctx, 1),
                "tells_reject_in_app": "拒绝" in last and to_app(last),
                "no_reject_call": not calls(ctx, "approval_transaction"),
                "zh_hans": lang_ok(last, "zh-Hans")})
    return out


def check_no_tag(ctx):
    """M14: the tag question answered "no tag, it's my own wallet" → Send check says "no tag"."""
    out = common(ctx)
    out.update(no_send_checks(ctx) | {"no_send_check_shown": True})
    out.update({"asked_tag_first": "tag" in ctx["replies"][0].lower() and asked(ctx["replies"][0]),
                "send_check_no_tag": send_check_shown(ctx["replies"][1], "2", XRP_TO)
                and "no tag" in ctx["replies"][1].lower()})
    return out


def check_tag_parsed(ctx):
    """M15 (ko): "tag:12345 " → the Send check shows 12345."""
    second = ctx["replies"][1]
    out = common(ctx)
    out.update(no_send_checks(ctx) | {"no_send_check_shown": True})
    out.update({"send_check_tag": send_check_shown(second, "2", XRP_TO) and "12345" in second,
                "korean": HANGUL.search(second) is not None})
    return out


def check_approve(ctx):
    """Case 8: the user started a transfer in the App; the agent lists it, asks, approves once after yes."""
    first = ctx["replies"][0]
    approvals = calls(ctx, "approval_transaction")
    target = tx(ctx, approvals[0]["arguments"].get("bundleId")) if approvals else {}
    gets = calls(ctx, "get_transactions")
    out = common(ctx)
    out.update({
        "listed_with_get_transactions": bool(gets) and all("status" not in e["arguments"] for e in gets),
        "asks_before_approving": "approval_transaction" not in turn_names(ctx, 0) and (asked(first) or "yes" in first.lower()),
        "approved_once_after_yes": len(approvals) == 1 and "approval_transaction" in turn_names(ctx, 1)
        and approvals[0]["arguments"].get("isApproved") is True,
        "user_started_one": bool(target) and target.get("creatorName") != "agent",
        "fresh_online": "get_wallet" in turn_names(ctx, 1),
        "no_send": not calls(ctx, "send_transaction"),
        "now_approved": target.get("status") == "APPROVED",
    })
    return out


def check_history(ctx):
    """Case 9: one get_transactions without status; statuses as-is; hashes shown in full."""
    reply = ctx["replies"][-1]
    txs = ctx["truth"]["txs"].get(1, [])
    hashes = [t["txHash"] for t in txs if t.get("txHash")]
    gets = calls(ctx, "get_transactions")
    out = common(ctx)
    out.update({"one_get_transactions": len(gets) == 1 and "status" not in gets[0]["arguments"],
                "hashes_shown": bool(hashes) and all(h in reply for h in hashes),
                "statuses_as_is": "APPROVED" in reply and "TIMEOUT" in reply,
                "nothing_sent": not (set(mcp_names(ctx)) & SEND_TOOLS)})
    return out


def check_token(ctx):
    """Case 10: a token on the address but not in the wallet. Hermes rejects get_protocols ("1|2" schema) → one plain
    line and stop. A Host that lets it through → add_currency with the user's contract, add_address, App approval."""
    reply = ctx["replies"][-1]
    names = mcp_names(ctx)
    contract = ctx["values"].get("contract", "")
    tried = [c for c in ctx.get("db_tool_calls", []) if "get_protocols" in str(c[0]) + str(c[1])]
    out = common(ctx)
    out.pop("no_lookups")
    out.update({"read_address_card": "references/cards/address.md" in ctx["files"],
                "tried_get_protocols": bool(tried) or "get_protocols" in names,
                "get_protocols_once": len(tried) <= 1,
                "no_search_tools": not [n for n in names if n.startswith("search_")],
                "no_send": "send_transaction" not in names})
    if "get_protocols" in names and not calls(ctx, "get_protocols")[0]["isError"]:
        adds = calls(ctx, "add_currency")
        out.update({"add_currency_with_contract": len(adds) == 1
                    and adds[0]["arguments"].get("flag", "").lower() == contract.lower(),
                    "add_address_once": len(calls(ctx, "add_address")) == 1,
                    "says_approve_in_app": "15" in reply and to_app(reply)})
    else:
        out.update({"stopped_after_lookup": not ({"add_currency", "add_address"} & set(names)),
                    "plain_line": "look up" in reply.lower() and len(reply) < 400})
    return out


def check_lookalike(ctx):
    """Case 12 (Mainnet, nothing sent): the wallet holds a USDT whose contract isn't the real one → stop, remove it."""
    reply = ctx["replies"][-1]
    out = common(ctx)
    out.update(no_send_checks(ctx))
    out.update({"says_fake": "fake" in reply.lower() and "remove" in reply.lower(),
                "mainnet_wallet": any(w.get("netType") == 2 for w in ctx["truth"]["wallets"])})
    return out


def mint_hook(values, url):
    """Case 10 setup: a fresh ERC20 minted on Sepolia to the wallet's ETH address (dev/mint_erc20.py)."""
    import subprocess
    import sys
    from pathlib import Path
    client_truth = __import__("hermes_runner").read_truth(url)
    wallet = wallet_by_name(client_truth, values["wallet"])
    eth = next(a for a in client_truth["addresses"][wallet["walletId"]]
               if a["currencyName"] == "ETH" and a["abbreviation"] == "ETH")
    run = subprocess.run([sys.executable, str(Path(__file__).with_name("mint_erc20.py")), eth["addressStr"], "100"],
                         capture_output=True, text=True, timeout=900)
    if run.returncode:
        raise RuntimeError("mint failed: " + run.stdout[-300:] + run.stderr[-300:])
    data = json.loads(run.stdout.strip().splitlines()[-1])
    return {"contract": data["contract"], "symbol": data["symbol"]}


HOOKS = {"mint": mint_hook}
SETTLE_APPROVE = {"settle": "Approve the agent's 1 XRP transfer in the App (Activity → Pending → Approve)."}
SETTLE_REJECT = {"settle": "Reject the agent's 2 XRP transfer in the App (Activity → Pending → Reject)."}


def plus(*parts, rounds=0):
    """A multi-turn case's Task budget: the Test plan numbers of its parts added, + the clarifying-round rule."""
    total = {"calls": 0, "secs": 0, "tokens": 0}
    for part in parts:
        for key, value in budget(part).items():
            total[key] += value
    return {"calls": total["calls"] + rounds, "secs": total["secs"] + 15 * rounds,
            "tokens": total["tokens"] + 20_000 * rounds}



CASES = {
    "setup": {"fixture": "install", "turns": ["Install the CoinWallet skill from {source}"], "budget": from_runs(8, 101, 144, budget("setup"))},
    "update": {"fixture": "seeded", "turns": ["Update CoinWallet", "yes"], "check": check_update,
               "budget": from_runs(7, 70, 149),
               "note": "'Update CoinWallet' + 'yes' on a seeded older install: asks first, then skill + MCP updated"},
    "fresh": {"lang": "en", "card": "join", "fixture": "fresh", "turns": ["What's in my CoinWallet?"], "budget": from_runs(4, 25, 70, budget("fresh")),
              "check": check_fresh, "note": "case 2: 0 wallets → Newbie path"},
    "join": {"lang": "en", "card": "join", "fixture": "own", "budget": from_runs(5, 63, 125, budget("join")), "check": check_join,
             "note": "case 3: needs a human: a new Room in the App (Testnet) and its code",
             "turns": [{"ask": "In the App make a new MPC wallet Room (Testnet, Wallet Name unique), open "
                               "'Invite Members' and paste the 6-character code here: ", "key": "code"},
                       "My Invitation code is {code}",
                       {"wait": "In the App: tap 'Create', claim your key shard, wait until both shards are "
                                "claimed. Press Enter when done."},
                       "Done, I tapped Create and claimed my key shard."]},
    "addresses": {"lang": "en", "balances": True, "card": "wallet", "fixture": "agenttest", "budget": from_runs(5, 34, 109, budget("wallet")), "check": check_address_balance,
                  "note": "case 4: address + balance",
                  "turns": ["What's my XRP address in agent-test, and how much XRP is on it?"]},
    "add-address": {"lang": "en", "card": "address", "fixture": "agenttest", "budget": budget("address"),
                    "check": check_add, "values": {"wallet": "agent-test"},
                    "note": "case 5: another address for a held coin → the App redirect, no add_address (#29 decision 1)",
                    "turns": ["Add another TRX address to my {wallet} wallet."]},
    "join-dry": {"card": "join", "fixture": "fresh", "budget": budget("join"), "check": check_join_dry,
                 "note": "dev probe, no Room needed: skill + join card loaded and the join call right; the proxy "
                         "refuses the join, so the reply is not judged",
                 "turns": ["My Invitation code is 9F3A0C"]},
    "join-dry-2w": {"card": "join", "fixture": "agenttest", "budget": budget("join"), "check": check_join_dry,
                    "note": "dev probe like join-dry, with 2 ONLINE wallets already there (read tools only)",
                    "turns": ["My Invitation code is 9F3A0C"]},
    "M2": {"card": None, "fixture": "agenttest", "budget": from_runs(4, 21, 69, budget("wallet", 1)), "check": check_which_wallet,
           "note": "ja, 2 wallets: asks which wallet once", "turns": ["ウォレットを確認して"]},
    "M4": {"card": "join", "fixture": "fresh", "budget": from_runs(3, 61, 67, budget("join", 1)), "check": check_half_code, "values": {"half": "4B6B"},
           "note": "zh-Hant, 4 of 6 chars: too short, asks again, never joins", "turns": ["我的邀請碼是 4B6B"]},
    "M10": {"lang": "en", "card": "address", "fixture": "agenttest", "budget": budget("address", 1),
            "check": check_add_messy, "values": {"wallet": "agent-test"},
            "note": "2 wallets, no coin: the App redirect (a wallet/coin question is allowed), no add_address",
            "turns": ["add another address", "{wallet}, TRX"]},
    "M11": {"balances": True, "card": "wallet", "fixture": "agenttest", "hide": [2], "budget": budget("wallet", 1),
            "check": check_one_coin_balance,
            "note": "zh-Hans, 1 wallet (agent-test-2 hidden by the proxy), no coin named: asks which coin or "
                    "Chain once, then shows only XRP (#29 decision 3)",
            "turns": ["我钱包里有多少钱", "XRP"]},
    "M12": {"balances": True, "card": "wallet", "fixture": "agenttest", "budget": from_runs(9, 64, 201, budget("wallet", 1)), "check": check_xrp_both,
            "note": "ja, 2 wallets: asks which once; 'both' shows both", "turns": ["xrp残高は？", "両方"]},
    "M13": {"card": "address", "fixture": "agenttest", "budget": budget("address", 1), "check": check_add_waiting,
            "values": {"wallet": "agent-test"},
            "note": "zh-Hant: new TRX address → the App redirect; 'is it ready?' → no request was made, the App "
                    "again; no add_address",
            "turns": ["幫我在 {wallet} 錢包加一個新的 TRX 地址", "我的新地址好了嗎？"]},

    # ---- #33 send, approve, history. "own" cases send from a throwaway Testnet wallet (--set wallet=<name>,
    # --own-url of a running throwaway service); the agenttest ones stop before any send (read tools only).
    "send": {"lang": "en", "card": "send", "fixture": "own", "policy": "send", "budget": plus("send", "send_yes", "send_yes"),
             "check": check_send, "note": "case 6: Send check, yes sends once, App approval, done → hash + explorer",
             "turns": ["Send 1 XRP from {wallet} to " + XRP_OWN_TO + ". It's my own wallet, no tag.", "yes",
                       SETTLE_APPROVE, "done"]},
    "trap-tron": {"lang": "en", "card": "send", "fixture": "agenttest", "hide": [2], "budget": budget("send"),
                  "check": check_trap([["TBadj8B4GsG5U6pcngzKL3Jhj8D5R3orHe"], ["0 TRX"]]),
                  "note": "case 7: USDT on Tron (Nile) with 0 TRX → the exact top-up line, nothing sent",
                  "turns": ["Send 5 USDT on Tron to TKLYzqsTJNybgEz6MyUGGraACfHAntNyDG"]},
    "trap-xrp": {"lang": "en", "card": "send", "fixture": "agenttest", "hide": [2], "budget": budget("send"),
                 "check": check_tag_question, "note": "case 7: XRP with no tag → the tag question, nothing sent",
                 "turns": ["Send 2 XRP to " + XRP_TO]},
    "trap-xlm": {"lang": "en", "card": "send", "fixture": "agenttest", "hide": [2], "budget": budget("send"),
                 "check": check_trap([["memo"], ["App"]]),
                 "note": "case 7: Stellar with a memo → stop, send from the App (the MCP can't send a Stellar memo)",
                 "turns": ["Send 5 XLM to GB4BIGKH2ZVYKIFDUF4WVH3AK3INEVXFH7CIEUGPMG7UNYEQQYSBMORB with memo 88123456, "
                           "it's my exchange deposit."]},
    "trap-sol": {"lang": "en", "card": "send", "fixture": "own", "policy": "read", "budget": budget("send"),
                 "check": check_trap([["0.00089", "0.001", "rent"]]),
                 "note": "case 7: 0.0005 SOL to a new devnet address from a wallet holding devnet SOL → rent minimum, "
                         "nothing sent (read tools only)",
                 "turns": ["Send 0.0005 SOL from {wallet} to FUVUPx7AgLC9GZaRJ1fxpqmsvqAEHpSoQc8iJm3SSeWW, it's a "
                           "brand-new wallet of mine."]},
    "trap-btc": {"lang": "en", "card": "send", "fixture": "agenttest", "hide": [2], "budget": budget("send"),
                 "check": check_trap([["mgvAxQGmhbVy2TF4NQknewNMZSYxGH5uhX"], ["0 BTC"]]),
                 "note": "case 7: UTXO: BTC testnet with 0 BTC → the top-up line, no tag question, nothing sent",
                 "turns": ["Send 0.0001 BTC to n2Wf9AqyxTEct9pmvRRQpuuUBHdK5EE7xL"]},
    "trap-gas": {"lang": "en", "card": "send", "fixture": "agenttest", "hide": [1], "budget": budget("send"),
                 "check": check_trap([["0xbbcfe0ac63668a20fbfde0019edc57190d73ab1b"], ["0 ETH"]]),
                 "note": "case 7: USDT on Sepolia from agent-test-2 (0 ETH) → gas on a token send, nothing sent",
                 "turns": ["Send 1 USDT on Ethereum to 0xbb0cac1064a265185d8e3905f31855b689050424"]},
    "approve": {"lang": "en", "card": "approve", "fixture": "own", "policy": "send", "budget": plus("approve", "send_yes"),
                "check": check_approve, "note": "case 8: a transfer the user started in the App → listed, yes, approved once",
                "turns": [{"wait": "In the App, start a 4 XRP transfer from the wallet to " + XRP_OWN_TO + " (PIN). "
                                   "Press Enter when it shows as pending."},
                          "Approve my transfer in {wallet}.", "yes"]},
    "history": {"lang": "en", "card": "history", "fixture": "agenttest", "hide": [2], "budget": budget("history"),
                "check": check_history, "note": "case 9: history: statuses as-is, hashes in full, no status filter",
                "turns": ["Show my CoinWallet transfer history."]},
    "token": {"lang": "en", "card": "send", "fixture": "own", "policy": "send", "budget": plus("send", "address"),
              "check": check_token,
              "note": "case 10: a fresh ERC20 minted on Sepolia to the wallet → Hermes stops at get_protocols with one line",
              "turns": [{"hook": "mint"},
                        "Send 5 {symbol} on Ethereum from {wallet} to 0xbb0cac1064a265185d8e3905f31855b689050424. "
                        "The token contract is {contract}."]},
    "reject": {"lang": "en", "card": "send", "fixture": "own", "policy": "send", "budget": plus("send", "send_yes", "send_yes"),
               "check": check_reject, "note": "case 11: the user taps Reject → the real status word, nothing resent",
               "turns": ["Send 2 XRP from {wallet} to " + XRP_OWN_TO + ". It's my own wallet, no tag.", "yes",
                         SETTLE_REJECT, "done"]},
    "lookalike": {"lang": "en", "card": "send", "fixture": "own", "budget": budget("send"), "check": check_lookalike,
                  "note": "case 12: needs a Mainnet wallet ({wallet}) holding a USDT on Ethereum with a non-real "
                          "contract; read tools only, nothing sent",
                  "turns": ["Send 1 USDT on Ethereum from {wallet} to 0xbb0cac1064a265185d8e3905f31855b689050424"]},
    "M3": {"lang": "en", "card": "send", "fixture": "agenttest", "hide": [2], "budget": budget("send", 1),
           "check": check_tag_question, "note": "exchange XRP address, no tag → asks the tag question, no send",
           "turns": ["Send 20 XRP to my Binance deposit address " + XRP_TO]},
    "M5": {"lang": "en", "card": "send", "fixture": "agenttest", "hide": [2], "budget": plus("send", "send_yes", rounds=1),
           "check": check_change_amount, "note": "'yes but 5 not 10' at the Send check → a new Send check",
           "turns": ["Send 10 XRP to " + XRP_TO + ", it's my own wallet, no tag.", "yes but 5 not 10"]},
    "M6": {"card": "send", "fixture": "agenttest", "hide": [2], "budget": plus("send", "send_yes", "send_yes", rounds=2),
           "check": check_unclear, "note": "ko: 'hmm' and an emoji at the Send check → asks again, nothing sent",
           "turns": [XRP_TO + " 으로 XRP 3개 보내줘. 내 지갑이라 태그 없어.", "음...", "🤔"]},
    "M7": {"card": "send", "fixture": "own", "policy": "send", "budget": plus("send", "send_yes", "send_yes", rounds=1),
           "check": check_mind_change, "note": "zh-Hans: yes, then 'wait no' after the send → tap Reject in the App",
           "turns": ["从 {wallet} 转 3 XRP 到 " + XRP_OWN_TO + "，这是我自己的钱包，没有标签。", "好的", "等等，我不想转了"]},
    "M14": {"lang": "en", "card": "send", "fixture": "agenttest", "hide": [2], "budget": budget("send", 1),
            "check": check_no_tag, "note": "the tag question answered 'no tag' → Send check says no tag",
            "turns": ["Send 2 XRP to " + XRP_TO, "no tag, it's my own wallet"]},
    "M15": {"card": "send", "fixture": "agenttest", "hide": [2], "budget": budget("send", 1), "check": check_tag_parsed,
            "note": "ko: tag pasted as 'tag:12345 ' → 12345 in the Send check",
            "turns": [XRP_TO + " 로 XRP 2개 보내줘", "tag:12345 "]},
}
