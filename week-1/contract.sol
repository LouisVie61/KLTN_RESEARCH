// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract SymbolicExecutionDemo {
    address public owner;
    mapping(address => uint256) public balances;
    bool public locked;

    constructor() {
        owner = msg.sender;
    }

    // Deposit ETH
    function deposit() public payable {
        require(msg.value > 0, "Must send ETH");
        balances[msg.sender] += msg.value;
    }

    // Withdraw with a simple lock 
    function withdraw(uint256 amount) public {
        require(!locked, "Reentrant call detected");
        require(balances[msg.sender] >= amount, "Insufficient balance");

        locked = true;

        // Vulnerable external call
        (bool sent, ) = msg.sender.call{value: amount}("");
        require(sent, "Transfer failed");

        balances[msg.sender] -= amount;

        locked = false;
    }

    // Hidden condition
    function specialFunction(uint256 x) public pure returns (string memory) {
        if (x * 3 + 7 == 100) {
            return "Magic number found!";
        }
        return "Try again";
    }

    // Access control branch
    function restrictedAction(uint256 code) public view returns (string memory) {
        if (msg.sender == owner) {
            if (code == 42) {
                return "Admin secret unlocked";
            }
        }
        return "Access denied";
    }
}