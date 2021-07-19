import brownie
from brownie import Contract
from brownie import config
import math


def test_migration(
    StrategySushiStaking,
    gov,
    token,
    vault,
    guardian,
    strategist,
    whale,
    strategy,
    chain,
    strategist_ms,
):

    ## deposit to the vault after approving
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(1000e18, {"from": whale})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)

    # deploy our new strategy
    new_strategy = strategist.deploy(StrategySushiStaking, vault)
    total_old = strategy.estimatedTotalAssets()

    # can we harvest an unactivated strategy? should be no
    tx = new_strategy.harvestTrigger(0, {"from": gov})
    print("\nShould we harvest? Should be False.", tx)
    assert tx == False

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
