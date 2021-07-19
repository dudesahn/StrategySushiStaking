import brownie
from brownie import Contract
from brownie import config
import math


def test_simple_harvest(
    gov,
    token,
    vault,
    strategist,
    whale,
    strategy,
    chain,
    strategist_ms,
    xsushi,
):
    ## deposit to the vault after approving
    startingWhale = token.balanceOf(whale)
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    token.approve(xsushi, 2 ** 256 - 1, {"from": whale})
    vault.deposit(1000e18, {"from": whale})
    newWhale = token.balanceOf(whale)

    # this is part of our check into the staking contract balance
    stakingBeforeHarvest = token.balanceOf(xsushi)

    # harvest, store asset amount
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)
    old_assets = vault.totalAssets()
    assert old_assets > 0
    assert token.balanceOf(strategy) == 0
    assert strategy.estimatedTotalAssets() > 0
    print("\nStarting Assets: ", old_assets / 1e18)

    # try and include custom logic here to check that funds are in the staking contract (if needed)
    assert token.balanceOf(xsushi) > stakingBeforeHarvest

    # simulate 7 days of earnings
    chain.sleep(86400 * 7)
    chain.mine(1)

    # harvest, store new asset amount
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)
    new_assets = vault.totalAssets()
    # we can't use strategyEstimated Assets because the profits are sent to the vault
    # in this case, we lose a few wei on xsushi. confirm we're no more than 5 wei off.
    assert new_assets >= old_assets or math.isclose(new_assets, old_assets, abs_tol=5)
    print("\nAssets after 7 days: ", new_assets / 1e18)

    # Display estimated APR
    print(
        "\nEstimated SUSHI APR: ",
        "{:.2%}".format(
            ((new_assets - old_assets) * (365 / 7)) / (strategy.estimatedTotalAssets())
        ),
    )

    # simulate a day of waiting for share price to bump back up
    chain.sleep(86400)
    chain.mine(1)

    # withdraw and confirm we made money, or at least that we have about the same
    vault.withdraw({"from": whale})
    assert token.balanceOf(whale) >= startingWhale or math.isclose(
        token.balanceOf(whale), startingWhale, abs_tol=5
    )
