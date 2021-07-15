import brownie
from brownie import Contract
from brownie import config

# test passes as of 21-06-26
def test_simple_harvest(
    gov,
    token,
    vault,
    dudesahn,
    strategist,
    whale,
    strategy,
    chain,
    strategist_ms,
    staking,
):
    ## deposit to the vault after approving
    startingWhale = token.balanceOf(whale)
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(1000e18, {"from": whale})
    newWhale = token.balanceOf(whale)

    # harvest, store asset amount
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)
    old_assets_dai = vault.totalAssets()
    assert old_assets_dai > 0
    assert token.balanceOf(strategy) == 0
    assert strategy.estimatedTotalAssets() > 0
    assert staking.balanceOf(strategy, token) > 0
    print("\nStarting Assets: ", old_assets_dai / 1e18)
    print("\nAssets Staked: ", staking.balanceOf(strategy, token) / 1e18)

    # simulate 9 days of earnings
    chain.sleep(86400 * 9)
    chain.mine(1)

    # harvest after a day, store new asset amount
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)
    new_assets_dai = vault.totalAssets()
    # we can't use strategyEstimated Assets because the profits are sent to the vault
    assert new_assets_dai >= old_assets_dai
    print("\nAssets after 2 days: ", new_assets_dai / 1e18)

    # Display estimated APR
    print(
        "\nEstimated SUSHI APR: ",
        "{:.2%}".format(
            ((new_assets_dai - old_assets_dai) * (365 / 7))
            / (strategy.estimatedTotalAssets())
        ),
    )

    # simulate a day of waiting for share price to bump back up
    chain.sleep(86400)
    chain.mine(1)

    # withdraw and confirm we made money
    vault.withdraw({"from": whale})
    assert token.balanceOf(whale) >= startingWhale
