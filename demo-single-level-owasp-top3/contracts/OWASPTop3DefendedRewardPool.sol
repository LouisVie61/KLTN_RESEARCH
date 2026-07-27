// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface ITop3DefendedToken {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
}

/// @notice Demonstrates defenses only for OWASP SC01, SC02, and SC05.
/// @dev This is not claimed to be production-ready or secure against every class of bug.
contract OWASPTop3DefendedRewardPool {
    ITop3DefendedToken public immutable stakingToken;
    ITop3DefendedToken public immutable rewardToken;
    address public owner;

    uint256 public totalDeposited;
    uint256 public rewardPerBlock;
    uint256 public depositFeeBps;
    uint256 public lastRewardBlock;
    uint256 public accRewardPerShare;

    mapping(address => uint256) public deposited;
    mapping(address => uint256) public rewardDebt;
    mapping(address => uint256) public unclaimedRewards;

    uint256 private constant ACC_PRECISION = 1e12;
    uint256 public constant MAX_DEPOSIT_FEE_BPS = 1_000; // 10%

    event RewardPerBlockChanged(uint256 oldRate, uint256 newRate);
    event DepositFeeChanged(uint256 oldFeeBps, uint256 newFeeBps);

    modifier onlyOwner() {
        require(msg.sender == owner, "only owner");
        _;
    }

    constructor(ITop3DefendedToken stakingToken_, ITop3DefendedToken rewardToken_, uint256 rewardPerBlock_) {
        require(address(stakingToken_) != address(0), "zero staking token");
        require(address(rewardToken_) != address(0), "zero reward token");
        stakingToken = stakingToken_;
        rewardToken = rewardToken_;
        owner = msg.sender;
        rewardPerBlock = rewardPerBlock_;
        lastRewardBlock = block.number;
    }

    function deposit(uint256 amount) external {
        require(amount > 0, "amount is zero");
        _updatePool();
        _harvest(msg.sender);

        require(stakingToken.transferFrom(msg.sender, address(this), amount), "stake transfer failed");

        uint256 fee = amount * depositFeeBps / 10_000;
        uint256 creditedAmount = amount - fee;
        require(creditedAmount > 0, "net amount is zero");

        if (fee > 0) {
            require(stakingToken.transfer(owner, fee), "fee transfer failed");
        }

        deposited[msg.sender] += creditedAmount;
        totalDeposited += creditedAmount;
        rewardDebt[msg.sender] = deposited[msg.sender] * accRewardPerShare / ACC_PRECISION;
    }

    function withdraw(uint256 amount) external {
        require(amount > 0, "amount is zero");
        require(deposited[msg.sender] >= amount, "insufficient deposit");
        _updatePool();
        _harvest(msg.sender);

        deposited[msg.sender] -= amount;
        totalDeposited -= amount;
        rewardDebt[msg.sender] = deposited[msg.sender] * accRewardPerShare / ACC_PRECISION;

        require(stakingToken.transfer(msg.sender, amount), "stake transfer failed");
    }

    function claim() external {
        _updatePool();
        _harvest(msg.sender);
        rewardDebt[msg.sender] = deposited[msg.sender] * accRewardPerShare / ACC_PRECISION;

        uint256 amount = unclaimedRewards[msg.sender];
        require(amount > 0, "no rewards");
        unclaimedRewards[msg.sender] = 0;
        require(rewardToken.transfer(msg.sender, amount), "reward transfer failed");
    }

    /// SC01: privileged configuration is restricted to the owner.
    /// SC02: the previous epoch is checkpointed before the new rate is stored.
    function setRewardPerBlock(uint256 newRewardPerBlock) external onlyOwner {
        require(newRewardPerBlock > 0, "rate is zero");
        _updatePool();
        uint256 oldRate = rewardPerBlock;
        rewardPerBlock = newRewardPerBlock;
        emit RewardPerBlockChanged(oldRate, newRewardPerBlock);
    }

    /// SC05: values outside the documented economic boundary are rejected.
    function setDepositFeeBps(uint256 newFeeBps) external onlyOwner {
        require(newFeeBps <= MAX_DEPOSIT_FEE_BPS, "fee too high");
        uint256 oldFeeBps = depositFeeBps;
        depositFeeBps = newFeeBps;
        emit DepositFeeChanged(oldFeeBps, newFeeBps);
    }

    function pendingReward(address user) external view returns (uint256) {
        uint256 currentAcc = accRewardPerShare;
        if (block.number > lastRewardBlock && totalDeposited > 0) {
            uint256 rewards = (block.number - lastRewardBlock) * rewardPerBlock;
            currentAcc += rewards * ACC_PRECISION / totalDeposited;
        }
        uint256 accumulated = deposited[user] * currentAcc / ACC_PRECISION;
        return unclaimedRewards[user] + accumulated - rewardDebt[user];
    }

    function _updatePool() internal {
        if (block.number <= lastRewardBlock) return;
        if (totalDeposited == 0) {
            lastRewardBlock = block.number;
            return;
        }
        uint256 rewards = (block.number - lastRewardBlock) * rewardPerBlock;
        accRewardPerShare += rewards * ACC_PRECISION / totalDeposited;
        lastRewardBlock = block.number;
    }

    function _harvest(address user) internal {
        uint256 accumulated = deposited[user] * accRewardPerShare / ACC_PRECISION;
        uint256 pending = accumulated - rewardDebt[user];
        if (pending > 0) unclaimedRewards[user] += pending;
    }
}
