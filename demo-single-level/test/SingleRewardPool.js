const { expect } = require("chai");
const { ethers, network } = require("hardhat");

describe("SingleRewardPool (educational semantic-bug demo)", function () {
  async function deployFixture() {
    const [owner, alice] = await ethers.getSigners();
    const Token = await ethers.getContractFactory("MockToken");
    const stake = await Token.deploy("Stake", "STK");
    const reward = await Token.deploy("Reward", "RWD");
    const Pool = await ethers.getContractFactory("SingleRewardPool");
    const pool = await Pool.deploy(await stake.getAddress(), await reward.getAddress(), ethers.parseEther("1"));
    await stake.mint(alice.address, ethers.parseEther("100"));
    await reward.mint(await pool.getAddress(), ethers.parseEther("1000"));
    await stake.connect(alice).approve(await pool.getAddress(), ethers.MaxUint256);
    return { owner, alice, stake, reward, pool };
  }

  it("deposits and withdraws tokens normally", async function () {
    const { alice, stake, pool } = await deployFixture();
    await pool.connect(alice).deposit(ethers.parseEther("25"));
    expect(await pool.deposited(alice.address)).to.equal(ethers.parseEther("25"));
    await pool.connect(alice).withdraw(ethers.parseEther("25"));
    expect(await stake.balanceOf(alice.address)).to.equal(ethers.parseEther("100"));
  });

  it("demonstrates BUG-1: a rate change retrospectively prices old blocks", async function () {
    const { owner, alice, reward, pool } = await deployFixture();
    await pool.connect(alice).deposit(ethers.parseEther("100"));
    const start = await ethers.provider.getBlockNumber();
    await network.provider.send("hardhat_mine", ["0xa"]);
    await pool.connect(owner).setRewardPerBlock(ethers.parseEther("10"));
    await network.provider.send("hardhat_mine", ["0x5"]);
    await pool.connect(alice).claim();

    // Correct reward would be roughly 60 tokens; the vulnerable path pays old blocks at the new rate.
    expect((await reward.balanceOf(alice.address)) > ethers.parseEther("100")).to.equal(true);
    expect((await ethers.provider.getBlockNumber()) > start).to.equal(true);
  });

  it("demonstrates BUG-2: fee-bearing deposits are over-credited", async function () {
    const { owner, alice, stake, pool } = await deployFixture();
    await pool.connect(owner).setDepositFeeBps(1_000); // 10%
    await pool.connect(alice).depositWithFeeBug(ethers.parseEther("100"));
    expect(await pool.deposited(alice.address)).to.equal(ethers.parseEther("100"));
    expect(await stake.balanceOf(await pool.getAddress())).to.equal(ethers.parseEther("90"));
  });
});
