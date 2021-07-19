import brownie
from brownie import chain
import math

# test passes as of 21-06-26
def test_change_debt_with_profit(
    gov,
    token,
    vault,
    strategist,
    whale,
    strategy,
    chain,
):

    ## deposit to the vault after approving
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(10000e18, {"from": whale})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)

    # simulate seven days of earnings
    chain.sleep(86400 * 7)
    chain.mine(1)

    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)
    chain.sleep(60 * 60 * 10)
    chain.mine(1)

    prev_params = vault.strategies(strategy).dict()

    currentDebt = vault.strategies(strategy)[2]
    vault.updateStrategyDebtRatio(strategy, currentDebt / 2, {"from": gov})
    assert vault.strategies(strategy)[2] == 5000

    tx = strategy.harvestTrigger(0, {"from": gov})
    print("\nShould we harvest? Should be true.", tx)
    assert tx == True

    # our whale donates 20 tokens to the vault, what a nice person!
    donation = 20e18
    token.transfer(strategy, donation, {"from": whale})

    # have our whale withdraw half of his donation
    vault.withdraw(donation / 2, {"from": whale})

    # simulate seven days of earnings
    chain.sleep(86400 * 7)
    chain.mine(1)

    # we harvest twice here because the first harvest sends the "profit" 10 SUSHI to our vault, the second
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)
    chain.sleep(60 * 60 * 24)
    chain.mine(1)
    new_params = vault.strategies(strategy).dict()

    # check that we've recorded a gain
    assert new_params["totalGain"] > prev_params["totalGain"]

    # specifically check that our gain is greater than our donation
    # for all of these, we lose a few wei going in and out of xsushi, so we use our isclose function. confirm we're no more than 5 wei off.
    assert new_params["totalGain"] - prev_params[
        "totalGain"
    ] > donation or math.isclose(
        new_params["totalGain"] - prev_params["totalGain"], donation, abs_tol=5
    )

    # check to make sure that our debtRatio is about half of our previous debt
    assert new_params["debtRatio"] == currentDebt / 2

    # check that we didn't add any more loss, or at least no more than 2 wei
    assert new_params["totalLoss"] == prev_params["totalLoss"] or math.isclose(
        new_params["totalLoss"], prev_params["totalLoss"], abs_tol=2
    )

    # assert that our vault total assets, multiplied by our debtRatio, is about equal to our estimated total assets (within 5 wei)
    # we multiply this by the debtRatio of our strategy out of 1 total (we've gone down to 50% above)
    assert math.isclose(
        vault.totalAssets() * 0.5, strategy.estimatedTotalAssets(), abs_tol=5
    )
