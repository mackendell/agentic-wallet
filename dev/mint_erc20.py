#!/usr/bin/env python3
"""Dev only: deploy a fresh plain ERC20 on Sepolia and mint it to one address (Test plan case 10, #20).

Usage: python3 dev/mint_erc20.py <to address> [amount]   → prints {"contract": ..., "symbol": ..., "tx": ...}

Needs Foundry (`forge`) and a throwaway deployer key with a little Sepolia ETH in
~/.cache/coinwallet-dev/sepolia-deployer.key (or $SEPOLIA_DEPLOYER_KEY). RPC: $SEPOLIA_RPC or a public one.
Each call makes a new token (symbol T + 4 random letters), so the wallet never already lists it.
"""
import json
import os
import random
import re
import string
import subprocess
import sys
import tempfile
from pathlib import Path

RPC = os.environ.get("SEPOLIA_RPC", "https://ethereum-sepolia-rpc.publicnode.com")
KEY_FILE = Path.home() / ".cache" / "coinwallet-dev" / "sepolia-deployer.key"

SOURCE = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract TestToken {
    string public name; string public symbol; uint8 public constant decimals = 18; uint256 public totalSupply;
    mapping(address => uint256) public balanceOf; mapping(address => mapping(address => uint256)) public allowance;
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    constructor(string memory n, string memory s, address to, uint256 amount) {
        name = n; symbol = s; totalSupply = amount; balanceOf[to] = amount; emit Transfer(address(0), to, amount);
    }
    function transfer(address to, uint256 v) external returns (bool) { _move(msg.sender, to, v); return true; }
    function approve(address sp, uint256 v) external returns (bool) {
        allowance[msg.sender][sp] = v; emit Approval(msg.sender, sp, v); return true;
    }
    function transferFrom(address f, address to, uint256 v) external returns (bool) {
        require(allowance[f][msg.sender] >= v, "allowance"); allowance[f][msg.sender] -= v; _move(f, to, v); return true;
    }
    function _move(address f, address to, uint256 v) internal {
        require(balanceOf[f] >= v, "balance"); balanceOf[f] -= v; balanceOf[to] += v; emit Transfer(f, to, v);
    }
}
"""


def main():
    to = sys.argv[1]
    amount = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    key = os.environ.get("SEPOLIA_DEPLOYER_KEY") or KEY_FILE.read_text().strip()
    symbol = "T" + "".join(random.choice(string.ascii_uppercase) for _ in range(4))
    with tempfile.TemporaryDirectory() as work:
        (Path(work) / "src").mkdir()
        (Path(work) / "src" / "TestToken.sol").write_text(SOURCE)
        run = subprocess.run(["forge", "create", "src/TestToken.sol:TestToken", "--rpc-url", RPC, "--private-key", key,
                              "--broadcast", "--json", "--constructor-args", "Test " + symbol, symbol, to,
                              str(amount * 10 ** 18)], cwd=work, capture_output=True, text=True, timeout=600)
    if run.returncode:
        raise SystemExit("forge create failed: " + run.stdout[-800:] + run.stderr[-800:])
    found = re.search(r'"deployedTo"\s*:\s*"(0x[0-9a-fA-F]{40})"', run.stdout)
    tx = re.search(r'"transactionHash"\s*:\s*"(0x[0-9a-fA-F]{64})"', run.stdout)
    if not found:
        raise SystemExit("no deployedTo in forge output: " + run.stdout[-800:])
    print(json.dumps({"contract": found.group(1), "symbol": symbol, "tx": tx.group(1) if tx else None,
                      "to": to, "amount": amount}))


if __name__ == "__main__":
    main()
