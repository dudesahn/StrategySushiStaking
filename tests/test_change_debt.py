import brownie
from brownie import Contract
from brownie import config
import math

# test passes as of 21-06-26
def test_change_debt(
    gov, token, vault, strategist, whale, strategy, chain,
):
    ## deposit to the vault after approving
    startingWhale = token.balanceOf(whale)
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(1000e18, {"from": whale})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)

    # evaluate our current total assets
    startingLive = strategy.estimatedTotalAssets()

    # debtRatio is in BPS (aka, max is 10,000, which represents 100%), and is a fraction of the funds that can be in the strategy
    currentDebt = 10000
    vault.updateStrategyDebtRatio(strategy, currentDebt / 2, {"from": gov})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)

    assert strategy.estimatedTotalAssets() <= (startingLive)

    # simulate nine days of earnings
    chain.sleep(86400 * 9)
    chain.mine(1)

    # set DebtRatio back to 100%
    vault.updateStrategyDebtRatio(strategy, currentDebt, {"from": gov})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)

    # normally, we would assert estimatedTotalAssets to be greater than or equal to startingLive
    # in this case, we don't profit and lose a few wei on xsushi. confirm we're no more than 5 wei off.
    assert math.isclose(strategy.estimatedTotalAssets(), startingLive, abs_tol=5)

    # simulate a day of waiting for share price to bump back up
    chain.sleep(86400)
    chain.mine(1)

    # withdraw and confirm we made money
    vault.withdraw({"from": whale})
    assert token.balanceOf(whale) >= startingWhale