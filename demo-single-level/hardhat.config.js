require("@nomicfoundation/hardhat-ethers");

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: {
    version: "0.8.20",
    settings: { optimizer: { enabled: true, runs: 200 } }
  },
  paths: {
    // Do not use "." here: Hardhat would recursively treat node_modules/*.sol
    // (including hardhat/console.sol) as local source files.
    sources: "./contracts",
    tests: "./test",
    cache: "./cache",
    artifacts: "./artifacts"
  },
  networks: {
    // Ten deterministic, pre-funded development accounts are created by
    // `npx hardhat node`. Import any two printed private keys into MetaMask.
    hardhat: {
      chainId: 31337,
      accounts: { count: 10, accountsBalance: "10000000000000000000000" }
    },
    localhost: {
      url: "http://127.0.0.1:8545",
      chainId: 31337
    }
  }
};
