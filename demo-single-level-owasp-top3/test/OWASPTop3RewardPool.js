const { expect } = require("chai");
const { ethers, network } = require("hardhat");

describe("OWASP Top 3 applicable to SingleRewardPool", function () {
  async function expectRevert(promise, expectedMessage) {
    try {
      await promise;
      expect.fail("expected transaction to revert");
    } catch (error) {
      expect(String(error)).to.include(expectedMessage);
    }
  }

  async function deployFixture() {
    const [owner, alice, attacker] = await ethers.getSigners();

    const Token = await ethers.getContractFactory("MockToken");
    const stake = await Token.deploy("Demo Stake Token", "DST");
    const reward = await Token.deploy("Demo Reward Token", "DRW");

    const Vulnerable = await ethers.getContractFactory("OWASPTop3VulnerableRewardPool");
    const vulnerable = await Vulnerable.deploy(
      await stake.getAddress(),
      await reward.getAddress(),
      ethers.parseEther("1")
    );

    const Defended = await ethers.getContractFactory("OWASPTop3DefendedRewardPool");
    const defended = await Defended.deploy(
      await stake.getAddress(),
      await reward.getAddress(),
      ethers.parseEther("1")
    );

    await stake.mint(alice.address, ethers.parseEther("400"));
    await reward.mint(await vulnerable.getAddress(), ethers.parseEther("5000"));
    await reward.mint(await defended.getAddress(), ethers.parseEther("5000"));

    await stake.connect(alice).approve(await vulnerable.getAddress(), ethers.MaxUint256);
    await stake.connect(alice).approve(await defended.getAddress(), ethers.MaxUint256);

    return { owner, alice, attacker, stake, reward, vulnerable, defended };
  }

  describe("SC01 - Access Control", function () {
    it("vulnerable pool lets an attacker change the reward rate", async function () {
      const { attacker, vulnerable } = await deployFixture();
      const maliciousRate = ethers.parseEther("1000");

      await vulnerable.connect(attacker).setRewardPerBlockUnauthorized(maliciousRate);

      expect(await vulnerable.rewardPerBlock()).to.equal(maliciousRate);
    });

    it("defended pool rejects an unauthorized configuration change", async function () {
      const { attacker, defended } = await deployFixture();

      await expectRevert(
        defended.connect(attacker).setRewardPerBlock(ethers.parseEther("1000")),
        "only owner"
      );
    });
  });

  describe("SC02 - Business Logic", function () {
    it("vulnerable pool applies the new rate to old blocks", async function () {
      const { owner, alice, reward, vulnerable } = await deployFixture();

      await vulnerable.connect(alice).deposit(ethers.parseEther("100"));
      await network.provider.send("hardhat_mine", ["0xa"]); // 10 blocks
      await vulnerable.connect(owner).setRewardPerBlockRetroactive(ethers.parseEther("10"));
      await network.provider.send("hardhat_mine", ["0x5"]); // 5 blocks
      await vulnerable.connect(alice).claim();

      const paid = await reward.balanceOf(alice.address);
      expect(paid > ethers.parseEther("100")).to.equal(true);
    });

    it("defended pool checkpoints the old rate before changing it", async function () {
      const { owner, alice, reward, defended } = await deployFixture();

      await defended.connect(alice).deposit(ethers.parseEther("100"));
      await network.provider.send("hardhat_mine", ["0xa"]); // 10 blocks
      await defended.connect(owner).setRewardPerBlock(ethers.parseEther("10"));
      await network.provider.send("hardhat_mine", ["0x5"]); // 5 blocks
      await defended.connect(alice).claim();

      const paid = await reward.balanceOf(alice.address);
      expect(paid > ethers.parseEther("50")).to.equal(true);
      expect(paid < ethers.parseEther("100")).to.equal(true);
    });
  });

  describe("SC05 - Lack of Input Validation", function () {
    it("vulnerable pool accepts a 100% fee and confiscates the deposit", async function () {
      const { owner, alice, stake, vulnerable } = await deployFixture();
      const ownerBefore = await stake.balanceOf(owner.address);

      await vulnerable.connect(owner).setDepositFeeBpsUnchecked(10_000);
      await vulnerable.connect(alice).depositWithConfiguredFee(ethers.parseEther("100"));

      expect(await vulnerable.deposited(alice.address)).to.equal(0n);
      expect(await vulnerable.totalDeposited()).to.equal(0n);
      expect(await stake.balanceOf(await vulnerable.getAddress())).to.equal(0n);
      expect(await stake.balanceOf(owner.address)).to.equal(ownerBefore + ethers.parseEther("100"));
    });

    it("defended pool rejects an out-of-range fee", async function () {
      const { owner, defended } = await deployFixture();

      await expectRevert(
        defended.connect(owner).setDepositFeeBps(10_000),
        "fee too high"
      );
    });

    it("defended pool credits only the net amount for a valid fee", async function () {
      const { owner, alice, stake, defended } = await deployFixture();

      await defended.connect(owner).setDepositFeeBps(1_000); // 10%
      await defended.connect(alice).deposit(ethers.parseEther("100"));

      expect(await defended.deposited(alice.address)).to.equal(ethers.parseEther("90"));
      expect(await defended.totalDeposited()).to.equal(ethers.parseEther("90"));
      expect(await stake.balanceOf(await defended.getAddress())).to.equal(ethers.parseEther("90"));

      await defended.connect(alice).withdraw(ethers.parseEther("90"));
      expect(await defended.deposited(alice.address)).to.equal(0n);
    });
  });
});
