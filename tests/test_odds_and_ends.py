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
    ## pretend we're the vault, send all funds away
    vault.setEmergencyShutdown(True, {"from": gov})
    strategy.setEmergencyExit({"from": gov})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)
    to_send = token.balanceOf(vault)
    token.transfer(gov, to_send, {"from": vault_person})
    assert vault.totalAssets() == 0

    # now we can try and harvest when the vault is completely empty
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
    # normally we would want this to be greater than what we started with
    # in this case, we don't profit and lose a few wei on xsushi. confirm we're no more than 5 wei off.
    assert math.isclose(new_strat_balance, total_old, abs_tol=5)

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
    # normally we would want this to be greater than what we started with
    # in this case, we don't profit and lose a few wei on xsushi. confirm we're no more than 5 wei off.
    assert math.isclose(vaultAssets_2, startingVault, abs_tol=5)
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