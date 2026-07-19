const fs = require("fs");
const path = require("path");
const hre = require("hardhat");

async function main() {
  const [deployer, alice] = await hre.ethers.getSigners();
  const Token = await hre.ethers.getContractFactory("MockToken");
  const stakeToken = await Token.deploy("Demo Stake Token", "DST");
  const rewardToken = await Token.deploy("Demo Reward Token", "DRW");
  await Promise.all([stakeToken.waitForDeployment(), rewardToken.waitForDeployment()]);

  const Pool = await hre.ethers.getContractFactory("SingleRewardPool");
  const pool = await Pool.deploy(
    await stakeToken.getAddress(),
    await rewardToken.getAddress(),
    hre.ethers.parseEther("1")
  );
  await pool.waitForDeployment();

  // The first two accounts printed by `npm run node` can immediately transact.
  await (await stakeToken.mint(deployer.address, hre.ethers.parseEther("1000"))).wait();
  await (await stakeToken.mint(alice.address, hre.ethers.parseEther("1000"))).wait();
  await (await rewardToken.mint(await pool.getAddress(), hre.ethers.parseEther("10000"))).wait();

  const deployment = {
    chainId: 31337,
    stakeToken: await stakeToken.getAddress(),
    rewardToken: await rewardToken.getAddress(),
    pool: await pool.getAddress(),
    fundedAccounts: [deployer.address, alice.address]
  };
  fs.writeFileSync(path.join(__dirname, "..", "frontend", "deployment.json"), JSON.stringify(deployment, null, 2));
  console.log("Local deployment written to frontend/deployment.json:");
  console.table(deployment);
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
