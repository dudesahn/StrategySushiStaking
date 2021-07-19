import brownie
from brownie import Contract
from brownie import config
import math


def test_odds_and_ends(
    gov,
    token,
    vault,
    strategist,
    whale,
    strategy,
    chain,
    strategist_ms,
    xsushi,
    vault_person,
    StrategySushiStaking,
):
    ## pretend we're the vault, send all funds away (oopsie!) turn off health checks because of this
    strategy.setDoHealthCheck(False, {"from": gov})
    to_send = xsushi.balanceOf(strategy)
    print("xSUSHI Balance of Vault", to_send)
    xsushi.transfer(gov, to_send, {"from": strategy})
    assert strategy.estimatedTotalAssets() == 0
    vault.approve(strategist_ms, 1e25, {"from": whale})

    tx = strategy.harvestTrigger(0, {"from": gov})
    print("\nShould we harvest? Should be true.", tx)
    assert tx == True

    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)

    # we can also withdraw from an empty vault as well
    vault.withdraw({"from": strategist})

    # we can try to migrate too, lol
    # deploy our new strategy
    new_strategy = strategist.deploy(StrategySushiStaking, vault)
    total_old = strategy.estimatedTotalAssets()

    # migrate our old strategy
    vault.migrateStrategy(strategy, new_strategy, {"from": gov})

    # assert that our old strategy is empty
    updated_total_old = strategy.estimatedTotalAssets()
    assert updated_total_old == 0

    # harvest to get funds back in strategy
    new_strategy.harvest({"from": gov})
    new_strat_balance = new_strategy.estimatedTotalAssets()
    assert new_strat_balance >= total_old

    startingVault = vault.totalAssets()
    print("\nVault starting assets with new strategy: ", startingVault)

    # simulate seven days of earnings
    chain.sleep(86400 * 7)
    chain.mine(1)

    # simulate a day of waiting for share price to bump back up
    chain.sleep(86400)
    chain.mine(1)

    # Test out our migrated strategy, confirm we're making a profit
    new_strategy.harvest({"from": gov})
    vaultAssets_2 = vault.totalAssets()
    assert vaultAssets_2 >= startingVault
    print("\nAssets after 1 day harvest: ", vaultAssets_2)

    # check our oracle
    one_eth_in_want = strategy.ethToWant(1e18)
    print("This is how much want one ETH buys:", one_eth_in_want)
    zero_eth_in_want = strategy.ethToWant(0)

    # check our views
    strategy.apiVersion()
    strategy.isActive()

    # tend stuff
    chain.sleep(1)
    strategy.tend({"from": gov})
    chain.sleep(1)
    strategy.tendTrigger(0, {"from": gov})


def test_odds_and_ends_2(
    gov,
    token,
    vault,
    strategist,
    whale,
    strategy,
    chain,
    strategist_ms,
    xsushi,
    vault_person,
    StrategySushiStaking,
):

    # major shutdown, want to trigger withdrawal from empty strategy
    strategy.setDoHealthCheck(False, {"from": gov})
    to_send = xsushi.balanceOf(strategy)
    print("SUSHI Balance of Vault", to_send)
    xsushi.transfer(gov, to_send, {"from": strategy})
    strategy.setEmergencyExit({"from": gov})

    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)

    # we can also withdraw from an empty vault as well
    vault.withdraw({"from": strategist})


def test_weird_reverts(
    gov,
    token,
    vault,
    strategist,
    whale,
    strategy,
    chain,
    strategist_ms,
    xsushi,
    vault_person,
    StrategySushiStaking,
    other_vault_strategy,
):

    # only vault can call this
    with brownie.reverts():
        strategy.migrate(strategist_ms, {"from": gov})

    # can't migrate to a different vault
    with brownie.reverts():
        vault.migrateStrategy(strategy, other_vault_strategy, {"from": gov})

    # can't withdraw from a non-vault address
    with brownie.reverts():
        strategy.withdraw(1e18, {"from": gov})

    # can't do health check with a non-health check contract
    with brownie.reverts():
        strategy.withdraw(1e18, {"from": gov})
