// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract VulnerableVault {
    address public owner;
    mapping(address => uint256) public balances;
    uint256 public totalShares;

    constructor() {
        owner = msg.sender;
    }

    function deposit() public payable {
        require(msg.value > 0, "no value");
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) public {
        require(balances[msg.sender] >= amount, "insufficient");

        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "send failed");

        balances[msg.sender] -= amount;
    }

    function mintReward(address to, uint256 amount) public {
        _mint(to, amount);
    }

    function firstDeposit(uint256 amount) public {
        uint256 shares;
        if (totalSupply() == 0) {
            shares = amount;
        } else {
            shares = amount * totalSupply() / address(this).balance;
        }
        _mint(msg.sender, shares);
    }

    function protectedMint(address to, uint256 amount) public {
        require(msg.sender == owner, "only owner");
        _mint(to, amount);
    }

    function totalSupply() public view returns (uint256) {
        return totalShares;
    }

    function _mint(address to, uint256 amount) internal {
        balances[to] += amount;
        totalShares += amount;
    }
}

