#!/usr/bin/env python3
"""Test fixture (dev only): a stdio MCP server that forwards to a running HTTP MCP service, with a tool policy.

Usage (Hermes registers it as the `coinwallet` MCP server for one test run):
  python3 dev/mcp_proxy.py --url http://localhost:18081/mcp --policy read --log run/mcp.jsonl [--hide-wallet 2]

--policy read   only read tools reach the service (for runs on real wallets: nothing can change)
--policy own    read tools + join_mpc_wallet + add_address (for runs on a throwaway service account)
--hide-wallet   drop this walletId from get_wallets and refuse calls that name it (a 1-wallet fixture)

Every tools/call is logged as one JSON line: tool, arguments, blocked, isError, short reply.
A refused call answers isError with "Blocked by the test harness"; the runner counts it as a fail.
Also imported by dev/hermes_runner.py for direct read-only calls (HttpMcp).
"""
import argparse
import json
import sys
import time
import urllib.request

READ_TOOLS = {"get_wallets", "get_wallet", "get_addresses", "get_address_balance", "query_address_balance", "status",
              "get_transactions", "get_transaction", "get_chains", "get_currencies", "get_protocols", "search_chains",
              "search_currencies", "search_protocols", "search_addresses", "get_nft_projects", "search_nft_projects"}
OWN_TOOLS = READ_TOOLS | {"join_mpc_wallet", "add_address"}
POLICIES = {"read": READ_TOOLS, "own": OWN_TOOLS}


class HttpMcp:
    """Minimal streamable-HTTP MCP client (the CoinsDo service answers plain JSON)."""

    def __init__(self, url):
        self.url, self.session, self.next_id = url, None, 100

    def post(self, message):
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if self.session:
            headers["Mcp-Session-Id"] = self.session
        request = urllib.request.Request(self.url, data=json.dumps(message).encode(), headers=headers, method="POST")
        with urllib.request.urlopen(request, timeout=120) as response:
            self.session = response.headers.get("Mcp-Session-Id") or self.session
            body = response.read().decode("utf-8", "replace")
        if not body.strip():
            return None
        if body.lstrip().startswith("{"):
            return json.loads(body)
        for line in body.splitlines():  # text/event-stream
            if line.startswith("data:") and line[5:].strip().startswith("{"):
                return json.loads(line[5:])
        return None

    def connect(self):
        self.post({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                   "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                              "clientInfo": {"name": "coinwallet-test", "version": "1"}}})
        self.post({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return self

    def call(self, tool, arguments=None):
        """Structured reply of one read tool, or raise."""
        self.next_id += 1
        reply = self.post({"jsonrpc": "2.0", "id": self.next_id, "method": "tools/call",
                           "params": {"name": tool, "arguments": arguments or {}}})
        result = (reply or {}).get("result") or {}
        if result.get("isError") or "error" in (reply or {}):
            raise RuntimeError(tool + " failed: " + json.dumps(reply)[:300])
        if result.get("structuredContent") is not None:
            return result["structuredContent"]
        text = " ".join(c.get("text", "") for c in result.get("content", []))
        try:
            return json.loads(text)
        except ValueError:
            return text


def text_result(msg_id, text, is_error):
    return {"jsonrpc": "2.0", "id": msg_id,
            "result": {"content": [{"type": "text", "text": text}], "isError": is_error}}


def hide_wallets(reply, hidden):
    result = (reply or {}).get("result") or {}
    data = result.get("structuredContent")
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        data["items"] = [w for w in data["items"] if w.get("walletId") not in hidden]
        if "total" in data:
            data["total"] = len(data["items"])
        result["content"] = [{"type": "text", "text": json.dumps(data, separators=(",", ":"))}]
    return reply


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--policy", choices=sorted(POLICIES), required=True)
    parser.add_argument("--log", required=True)
    parser.add_argument("--hide-wallet", type=int, action="append", default=[])
    args = parser.parse_args()
    allowed, hidden = POLICIES[args.policy], set(args.hide_wallet)
    upstream = HttpMcp(args.url)

    def log(**entry):
        entry["time"] = round(time.time(), 2)
        with open(args.log, "a", encoding="utf-8") as stream:
            stream.write(json.dumps(entry, ensure_ascii=False) + "\n")

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except ValueError:
            continue
        msg_id = message.get("id")
        if message.get("method") == "tools/call":
            params = message.get("params") or {}
            tool, arguments = params.get("name", ""), params.get("arguments") or {}
            if tool not in allowed or arguments.get("walletId") in hidden:
                text = "Blocked by the test harness: " + tool + " is not allowed in this test."
                if tool in allowed:
                    text = "wallet not found"
                log(tool=tool, arguments=arguments, blocked=tool not in allowed, isError=True, reply=text)
                reply = text_result(msg_id, text, True)
            else:
                try:
                    reply = upstream.post(message)
                except Exception as exc:  # noqa: BLE001 - report any upstream failure as a tool error
                    reply = text_result(msg_id, "service error: " + str(exc), True)
                if tool == "get_wallets" and hidden:
                    reply = hide_wallets(reply, hidden)
                result = (reply or {}).get("result") or {}
                short = " ".join(c.get("text", "") for c in result.get("content", []) if isinstance(c, dict))
                log(tool=tool, arguments=arguments, blocked=False, isError=bool(result.get("isError")),
                    reply=short[:400])
        else:
            try:
                reply = upstream.post(message)
            except Exception as exc:  # noqa: BLE001
                reply = {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32000, "message": str(exc)}}
        if msg_id is not None and reply is not None:
            sys.stdout.write(json.dumps(reply) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
