import pytest
from brownie import config, Wei, Contract

# Snapshots the chain before each test and reverts after test completion.
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


# Define relevant tokens and contracts in this section
@pytest.fixture(scope="module")
def token():
    # this should be the address of the ERC-20 used by the strategy/vault. In this case, SUSHI
    token_address = "0x6B3595068778DD592e39A122f4f5a5cF09C90fE2"
    yield Contract(token_address)


@pytest.fixture(scope="module")
def healthCheck():
    yield Contract("0xDDCea799fF1699e98EDF118e0629A974Df7DF012")


@pytest.fixture(scope="module")
def farmed():
    # this is the token that we are farming and selling for more of our want. In this case, we don't have one (this contract is xyz, from old strat).
    yield Contract("0x618679dF9EfCd19694BB1daa8D00718Eacfa2883")


# Add any extra contracts we need here, such as staking contracts
# here, I add xsushi, because this is essentially our staking contract
@pytest.fixture(scope="module")
def xsushi():
    yield Contract("0x8798249c2E607446EfB7Ad49eC89dD1865Ff4272")


# Define any accounts in this section
# for live testing, governance is the strategist MS; we will update this before we endorse
# normal gov is ychad, 0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52
@pytest.fixture(scope="module")
def gov(accounts):
    yield accounts.at("0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7", force=True)


@pytest.fixture(scope="module")
def strategist_ms(accounts):
    # like governance, but better
    yield accounts.at("0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7", force=True)


@pytest.fixture(scope="module")
def keeper(accounts):
    yield accounts.at("0xBedf3Cf16ba1FcE6c3B751903Cf77E51d51E05b8", force=True)


@pytest.fixture(scope="module")
def rewards(accounts):
    yield accounts.at("0x8Ef63b525fceF7f8662D98F77f5C9A86ae7dFE09", force=True)


@pytest.fixture(scope="module")
def guardian(accounts):
    yield accounts[2]


@pytest.fixture(scope="module")
def management(accounts):
    yield accounts[3]


@pytest.fixture(scope="module")
def strategist(accounts):
    yield accounts.at("0xBedf3Cf16ba1FcE6c3B751903Cf77E51d51E05b8", force=True)


@pytest.fixture(scope="module")
def vault_person(accounts):
    yield accounts.at("0x497590d2d57f05cf8B42A36062fA53eBAe283498", force=True)


@pytest.fixture(scope="module")
def whale(accounts):
    # Totally in it for the tech
    # Update this with a large holder of your want token (largest EOA holder of SUSHI, binance wallet)
    whale = accounts.at("0x28C6c06298d514Db089934071355E5743bf21d60", force=True)
    yield whale


# list any existing strategies here
@pytest.fixture(scope="module")
def LiveStrategy_1():
    yield Contract("0xC1810aa7F733269C39D640f240555d0A4ebF4264")


# use this if you need to deploy the vault
# @pytest.fixture(scope="function")
# def vault(pm, gov, rewards, guardian, management, token, chain):
#     Vault = pm(config["dependencies"][0]).Vault
#     vault = guardian.deploy(Vault)
#     vault.initialize(token, gov, rewards, "", "", guardian)
#     vault.setDepositLimit(2 ** 256 - 1, {"from": gov})
#     vault.setManagement(management, {"from": gov})
#     chain.sleep(1)
#     yield vault

# use this if your vault is already deployed
@pytest.fixture(scope="function")
def vault(pm, gov, rewards, guardian, management, token, chain):
    vault = Contract("0x497590d2d57f05cf8B42A36062fA53eBAe283498")
    yield vault


# replace the first value with the name of your strategy
@pytest.fixture(scope="function")
def strategy(
    StrategySushiStaking,
    strategist,
    keeper,
    vault,
    gov,
    guardian,
    token,
    healthCheck,
    chain,
    LiveStrategy_1,
):
    # parameters for this are: strategy, vault, max deposit, minTimePerInvest, slippage protection (10000 = 100% slippage allowed),
    strategy = strategist.deploy(StrategySushiStaking, vault)
    strategy.setKeeper(keeper, {"from": gov})
    # set our management fee to zero so it doesn't mess with our profit checking
    vault.setManagementFee(0, {"from": gov})
    # reduce our current strategy's debtRatio to 0 and harvest
    vault.updateStrategyDebtRatio(LiveStrategy_1, 0, {"from": gov})
    LiveStrategy_1.harvest({"from": gov})
    # add our new strategy
    vault.addStrategy(strategy, 10_000, 0, 2 ** 256 - 1, 1_000, {"from": gov})
    strategy.setHealthCheck(healthCheck, {"from": gov})
    strategy.setDoHealthCheck(True, {"from": gov})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)
    yield strategy


# use this if your strategy is already deployed
# @pytest.fixture(scope="function")
# def strategy():
#     # parameters for this are: strategy, vault, max deposit, minTimePerInvest, slippage protection (10000 = 100% slippage allowed),
#     strategy = Contract("0xC1810aa7F733269C39D640f240555d0A4ebF4264")
#     yield strategy
