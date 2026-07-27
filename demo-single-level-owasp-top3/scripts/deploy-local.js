const fs = require("fs");
const path = require("path");
const hre = require("hardhat");

async function main() {
  const [owner, alice, attacker] = await hre.ethers.getSigners();
  const Token = await hre.ethers.getContractFactory("MockToken");
  const stake = await Token.deploy("Demo Stake Token", "DST");
  const reward = await Token.deploy("Demo Reward Token", "DRW");
  await Promise.all([stake.waitForDeployment(), reward.waitForDeployment()]);

  const Vulnerable = await hre.ethers.getContractFactory("OWASPTop3VulnerableRewardPool");
  const vulnerable = await Vulnerable.deploy(
    await stake.getAddress(), await reward.getAddress(), hre.ethers.parseEther("1")
  );
  await vulnerable.waitForDeployment();

  const Defended = await hre.ethers.getContractFactory("OWASPTop3DefendedRewardPool");
  const defended = await Defended.deploy(
    await stake.getAddress(), await reward.getAddress(), hre.ethers.parseEther("1")
  );
  await defended.waitForDeployment();

  for (const account of [owner, alice, attacker]) {
    await (await stake.mint(account.address, hre.ethers.parseEther("400"))).wait();
  }
  await (await reward.mint(await vulnerable.getAddress(), hre.ethers.parseEther("5000"))).wait();
  await (await reward.mint(await defended.getAddress(), hre.ethers.parseEther("5000"))).wait();

  const deployment = {
    chainId: 31337,
    stakeToken: await stake.getAddress(),
    rewardToken: await reward.getAddress(),
    vulnerablePool: await vulnerable.getAddress(),
    defendedPool: await defended.getAddress(),
    owner: owner.address,
    fundedAccounts: [owner.address, alice.address, attacker.address]
  };
  const output = path.join(__dirname, "..", "frontend", "deployment.json");
  fs.mkdirSync(path.dirname(output), { recursive: true });
  fs.writeFileSync(output, JSON.stringify(deployment, null, 2));
  console.log("Local OWASP Top 3 deployment written to frontend/deployment.json");
  console.table(deployment);
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
