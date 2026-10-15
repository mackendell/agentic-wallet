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
"""
import re

APP_IOS = "https://a8ata.app.link/coinwallet_ios"
APP_ANDROID = "https://a8ata.app.link/coinwallet_android"
LOOKUPS = {"get_chains", "get_currencies", "get_protocols", "search_chains", "search_currencies", "search_protocols",
           "search_addresses", "get_nft_projects", "search_nft_projects"}

# Task budget, worst of 3 runs on DeepSeek Flash. Messy cases: + 1 call, + 15 s, + 20K per needed clarifying round.
BASE = {
    "setup": (10, 180, 150_000), "fresh": (3, 30, 60_000), "join": (4, 45, 80_000),
    "wallet": (5, 45, 100_000), "address": (4, 45, 80_000),
}


def budget(base, rounds=0):
    calls, secs, tokens = BASE[base]
    return {"calls": calls + rounds, "secs": secs + 15 * rounds, "tokens": tokens + 20_000 * rounds}


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


def check_all_balances(ctx):
    reply = ctx["replies"][-1]
    nonzero, zero_only = [], []
    for a in ctx["truth"]["addresses"][1]:
        balance = ctx["truth"]["balances"][a["addressId"]]
        (nonzero if float(balance or 0) else zero_only).append((a["currencyName"], balance))
    shown_names = {n for n, _ in nonzero}
    out = common(ctx)
    out.update({
        "asks_nothing": "?" not in reply and "？" not in reply,
        "nonzero_shown": all(has_number(reply, b) for _, b in nonzero),
        "zero_hidden": all(not re.search(r"\b" + re.escape(n) + r"\b", reply) for n, _ in zero_only
                           if n not in shown_names),
        "zh_hans": lang_ok(reply, "zh-Hans"),
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


def add_checks(ctx, wallet_name, last_turn_add):
    wallet = next((w for w in ctx["truth"]["wallets"] if w["walletName"] == wallet_name), None)
    trx = addr(ctx, wallet["walletId"], "TRX", "TRX") if wallet else None
    adds = [e for e in ctx["mcp"] if e["tool"] == "add_address"]
    reply = ctx["replies"][last_turn_add]
    return {
        "wallet_known": bool(wallet and trx),
        "add_once_right_ids": len(adds) == 1 and bool(trx) and adds[0]["arguments"].get("walletId") == wallet["walletId"]
        and adds[0]["arguments"].get("currencyId") == trx["currencyId"],
        # Spec outcome: {"pending": 1} and "approve in the App within 15 minutes". MCP v1.0.8 answers
        # {"existed": 1} for a coin already in the wallet; then the right reply sends the user to the App.
        "service_said_pending": bool(adds) and '"pending":1' in adds[0].get("reply", "").replace(" ", ""),
        "right_next_step": bool(adds) and (bool(re.search(r"15\s*(min|分)", reply)) if '"pending":1' in
                                           adds[0].get("reply", "").replace(" ", "") else "App" in reply),
        "no_custom_path": "custom_address_path" not in mcp_names(ctx),
    }


def check_add(ctx):
    out = common(ctx)
    out.update(add_checks(ctx, ctx["values"]["wallet"], -1))
    return out


def check_add_messy(ctx):
    out = common(ctx)
    first = ctx["replies"][0]
    out.update({
        "asks_wallet_and_coin_once": all(n in first for n in wallet_names(ctx)) and not ctx["mcp_by_turn"][0][1:],
    })
    out.update(add_checks(ctx, ctx["values"]["wallet"], -1))
    return out


def check_add_waiting(ctx):
    out = common(ctx)
    out.update(add_checks(ctx, ctx["values"]["wallet"], 0))
    last = ctx["replies"][-1]
    out.update({
        "says_waiting_for_app": "App" in last or "app" in last,
        "no_retry": [e["tool"] for e in ctx["mcp_by_turn"][-1]].count("add_address") == 0,
        "zh_hant": lang_ok(ctx["replies"][0], "zh-Hant") and lang_ok(last, "zh-Hant"),
    })
    return out


CASES = {
    "setup": {"fixture": "install", "turns": ["Install the CoinWallet skill from {source}"], "budget": budget("setup")},
    "update": {"fixture": "seeded", "turns": ["Update CoinWallet", "yes"], "check": check_update,
               "note": "'Update CoinWallet' + 'yes' on a seeded older install: asks first, then skill + MCP updated"},
    "fresh": {"lang": "en", "card": "join", "fixture": "fresh", "turns": ["What's in my CoinWallet?"], "budget": budget("fresh"),
              "check": check_fresh, "note": "case 2: 0 wallets → Newbie path"},
    "join": {"lang": "en", "card": "join", "fixture": "own", "budget": budget("join"), "check": check_join,
             "note": "case 3: needs a human: a new Room in the App (Testnet) and its code",
             "turns": [{"ask": "In the App make a new MPC wallet Room (Testnet, Wallet Name unique), open "
                               "'Invite Members' and paste the 6-character code here: ", "key": "code"},
                       "My Invitation code is {code}",
                       {"wait": "In the App: tap 'Create', claim your key shard, wait until both shards are "
                                "claimed. Press Enter when done."},
                       "Done, I tapped Create and claimed my key shard."]},
    "addresses": {"lang": "en", "balances": True, "card": "wallet", "fixture": "agenttest", "budget": budget("wallet"), "check": check_address_balance,
                  "note": "case 4: address + balance",
                  "turns": ["What's my XRP address in agent-test, and how much XRP is on it?"]},
    "add-address": {"lang": "en", "card": "address", "fixture": "own", "budget": budget("address"), "check": check_add,
                    "note": "case 5: needs a human: an ONLINE wallet on the own account (--set wallet=NAME); "
                            "leaves one App approval waiting",
                    "turns": ["Add another TRX address to my {wallet} wallet."]},
    "join-dry": {"card": "join", "fixture": "fresh", "budget": budget("join"), "check": check_join_dry,
                 "note": "dev probe, no Room needed: skill + join card loaded and the join call right; the proxy "
                         "refuses the join, so the reply is not judged",
                 "turns": ["My Invitation code is 9F3A0C"]},
    "join-dry-2w": {"card": "join", "fixture": "agenttest", "budget": budget("join"), "check": check_join_dry,
                    "note": "dev probe like join-dry, with 2 ONLINE wallets already there (read tools only)",
                    "turns": ["My Invitation code is 9F3A0C"]},
    "M2": {"card": None, "fixture": "agenttest", "budget": budget("wallet", 1), "check": check_which_wallet,
           "note": "ja, 2 wallets: asks which wallet once", "turns": ["ウォレットを確認して"]},
    "M4": {"card": "join", "fixture": "fresh", "budget": budget("join", 1), "check": check_half_code, "values": {"half": "4B6B"},
           "note": "zh-Hant, 4 of 6 chars: too short, asks again, never joins", "turns": ["我的邀請碼是 4B6B"]},
    "M10": {"lang": "en", "card": "address", "fixture": "own", "budget": budget("address", 1), "check": check_add_messy,
            "note": "needs a human: 2+ ONLINE wallets on the own account (--set wallet=NAME); leaves one App "
                    "approval waiting",
            "turns": ["add another address", "{wallet}, TRX"]},
    "M11": {"balances": True, "card": "wallet", "fixture": "agenttest", "hide": [2], "budget": budget("wallet"), "check": check_all_balances,
            "note": "zh-Hans, 1 wallet (agent-test-2 hidden by the proxy): non-zero balances, asks nothing",
            "turns": ["我钱包里有多少钱"]},
    "M12": {"balances": True, "card": "wallet", "fixture": "agenttest", "budget": budget("wallet", 1), "check": check_xrp_both,
            "note": "ja, 2 wallets: asks which once; 'both' shows both", "turns": ["xrp残高は？", "両方"]},
    "M13": {"card": "address", "fixture": "own", "budget": budget("address", 1), "check": check_add_waiting,
            "note": "zh-Hant: new address asked about while it waits for App approval; no retry. Needs a human: "
                    "an ONLINE wallet (--set wallet=NAME); do not approve during the run",
            "turns": ["幫我在 {wallet} 錢包加一個新的 TRX 地址", "我的新地址好了嗎？"]},
}
