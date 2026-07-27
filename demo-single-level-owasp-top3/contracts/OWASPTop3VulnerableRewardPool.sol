// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface ITop3Token {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
}

/// @notice Educational contract containing three intentional vulnerabilities.
/// @dev Never deploy with real funds.
contract OWASPTop3VulnerableRewardPool {
    ITop3Token public immutable stakingToken;
    ITop3Token public immutable rewardToken;
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

    modifier onlyOwner() {
        require(msg.sender == owner, "only owner");
        _;
    }

    constructor(ITop3Token stakingToken_, ITop3Token rewardToken_, uint256 rewardPerBlock_) {
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

        deposited[msg.sender] += amount;
        totalDeposited += amount;
        rewardDebt[msg.sender] = deposited[msg.sender] * accRewardPerShare / ACC_PRECISION;

        require(stakingToken.transferFrom(msg.sender, address(this), amount), "stake transfer failed");
    }

    function withdraw(uint256 amount) external {
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

    /// SC01: anyone can change a critical economic parameter.
    /// The checkpoint is present so this function isolates access-control failure.
    function setRewardPerBlockUnauthorized(uint256 newRewardPerBlock) external {
        _updatePool();
        rewardPerBlock = newRewardPerBlock;
    }

    /// SC02: caller is authorized, but old blocks are later valued at the new rate.
    function setRewardPerBlockRetroactive(uint256 newRewardPerBlock) external onlyOwner {
        rewardPerBlock = newRewardPerBlock;
    }

    /// SC05: no upper bound; 10_000 means a 100% deposit fee.
    function setDepositFeeBpsUnchecked(uint256 newFeeBps) external onlyOwner {
        depositFeeBps = newFeeBps;
    }

    /// An unchecked 10_000 bps configuration makes the net deposit zero and sends
    /// the entire user amount to the owner. The accounting remains internally
    /// consistent, which isolates the missing input-boundary problem from BUG-2.
    function depositWithConfiguredFee(uint256 amount) external {
        require(amount > 0, "amount is zero");
        _updatePool();
        _harvest(msg.sender);

        require(stakingToken.transferFrom(msg.sender, address(this), amount), "stake transfer failed");
        uint256 fee = amount * depositFeeBps / 10_000;
        uint256 creditedAmount = amount - fee;

        if (fee > 0) {
            require(stakingToken.transfer(owner, fee), "fee transfer failed");
        }

        deposited[msg.sender] += creditedAmount;
        totalDeposited += creditedAmount;
        rewardDebt[msg.sender] = deposited[msg.sender] * accRewardPerShare / ACC_PRECISION;
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
