// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
}

contract SingleRewardPool {
    IERC20 public immutable stakingToken;
    IERC20 public immutable rewardToken;
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

    event Deposit(address indexed user, uint256 amount);
    event Withdraw(address indexed user, uint256 amount);
    event Claim(address indexed user, uint256 amount);
    event RewardPerBlockChanged(uint256 oldRewardPerBlock, uint256 newRewardPerBlock);
    event DepositFeeChanged(uint256 oldFeeBps, uint256 newFeeBps);

    modifier onlyOwner() {
        require(msg.sender == owner, "only owner");
        _;
    }

    constructor(IERC20 _stakingToken, IERC20 _rewardToken, uint256 _rewardPerBlock) {
        stakingToken = _stakingToken;
        rewardToken = _rewardToken;
        owner = msg.sender;
        rewardPerBlock = _rewardPerBlock;
        lastRewardBlock = block.number;
    }

    function deposit(uint256 amount) external {
        require(amount > 0, "amount is zero");

        _updatePool();
        _harvestToAccounting(msg.sender);

        deposited[msg.sender] += amount;
        totalDeposited += amount;
        rewardDebt[msg.sender] = (deposited[msg.sender] * accRewardPerShare) / ACC_PRECISION;

        require(stakingToken.transferFrom(msg.sender, address(this), amount), "stake transfer failed");
        emit Deposit(msg.sender, amount);
    }

    function withdraw(uint256 amount) external {
        require(deposited[msg.sender] >= amount, "insufficient deposit");

        _updatePool();
        _harvestToAccounting(msg.sender);

        deposited[msg.sender] -= amount;
        totalDeposited -= amount;
        rewardDebt[msg.sender] = (deposited[msg.sender] * accRewardPerShare) / ACC_PRECISION;

        require(stakingToken.transfer(msg.sender, amount), "stake transfer failed");
        emit Withdraw(msg.sender, amount);
    }

    function claim() external {
        _updatePool();
        _harvestToAccounting(msg.sender);
        rewardDebt[msg.sender] = (deposited[msg.sender] * accRewardPerShare) / ACC_PRECISION;

        uint256 amount = unclaimedRewards[msg.sender];
        require(amount > 0, "no rewards");
        unclaimedRewards[msg.sender] = 0;

        require(rewardToken.transfer(msg.sender, amount), "reward transfer failed");
        emit Claim(msg.sender, amount);
    }

    function pendingReward(address user) external view returns (uint256) {
        uint256 currentAccRewardPerShare = accRewardPerShare;

        if (block.number > lastRewardBlock && totalDeposited != 0) {
            uint256 blocksElapsed = block.number - lastRewardBlock;
            uint256 rewards = blocksElapsed * rewardPerBlock;
            currentAccRewardPerShare += (rewards * ACC_PRECISION) / totalDeposited;
        }

        uint256 accumulated = (deposited[user] * currentAccRewardPerShare) / ACC_PRECISION;
        return unclaimedRewards[user] + accumulated - rewardDebt[user];
    }

    function setRewardPerBlock(uint256 newRewardPerBlock) external onlyOwner {
        uint256 oldRewardPerBlock = rewardPerBlock;

        // VULNERABILITY: this function should call _updatePool() before changing
        // rewardPerBlock. Without that checkpoint, all blocks since lastRewardBlock
        // are accounted later using newRewardPerBlock instead of the rate that was
        // active during those blocks, so users can receive incorrect rewards.
        rewardPerBlock = newRewardPerBlock;

        emit RewardPerBlockChanged(oldRewardPerBlock, newRewardPerBlock);
    }

    function setDepositFeeBps(uint256 newFeeBps) external onlyOwner {
        require(newFeeBps <= 1_000, "fee too high");
        uint256 oldFeeBps = depositFeeBps;
        depositFeeBps = newFeeBps;
        emit DepositFeeChanged(oldFeeBps, newFeeBps);
    }

    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "zero owner");
        owner = newOwner;
    }

    /// @dev BUG-2: when a non-zero fee is configured, this intentionally credits
    /// the user with `amount` although `fee` tokens leave the pool. The accounting
    /// invariant totalDeposited <= stakingToken.balanceOf(pool) can be broken and
    /// the final withdrawal may revert. This is included only for semantic-bug demos.
    function depositWithFeeBug(uint256 amount) external {
        require(amount > 0, "amount is zero");

        _updatePool();
        _harvestToAccounting(msg.sender);
        deposited[msg.sender] += amount;
        totalDeposited += amount;
        rewardDebt[msg.sender] = (deposited[msg.sender] * accRewardPerShare) / ACC_PRECISION;

        require(stakingToken.transferFrom(msg.sender, address(this), amount), "stake transfer failed");
        uint256 fee = (amount * depositFeeBps) / 10_000;
        if (fee != 0) require(stakingToken.transfer(owner, fee), "fee transfer failed");
        emit Deposit(msg.sender, amount);
    }

    function _updatePool() internal {
        if (block.number <= lastRewardBlock) {
            return;
        }

        if (totalDeposited == 0) {
            lastRewardBlock = block.number;
            return;
        }

        uint256 blocksElapsed = block.number - lastRewardBlock;
        uint256 rewards = blocksElapsed * rewardPerBlock;
        accRewardPerShare += (rewards * ACC_PRECISION) / totalDeposited;
        lastRewardBlock = block.number;
    }

    function _harvestToAccounting(address user) internal {
        uint256 accumulated = (deposited[user] * accRewardPerShare) / ACC_PRECISION;
        uint256 pending = accumulated - rewardDebt[user];

        if (pending != 0) {
            unclaimedRewards[user] += pending;
        }
    }
}
