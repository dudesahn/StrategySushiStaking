import brownie
from brownie import Contract
from brownie import config
import math

# test passes as of 21-06-26
def test_emergency_shutdown_from_vault(
    gov, token, vault, whale, strategy, chain,
):
    ## deposit to the vault after approving
    startingWhale = token.balanceOf(whale)
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(1000e18, {"from": whale})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)

    # simulate nine days of earnings
    chain.sleep(86400 * 9)
    chain.mine(1)
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)

    # set emergency and exit, then confirm that the strategy has no funds
    vault.setEmergencyShutdown(True, {"from": gov})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)
    assert strategy.estimatedTotalAssets() == 0

    # simulate a day of waiting for share price to bump back up
    chain.sleep(86400)
    chain.mine(1)

    # normally, we would assert value withdrawn to be greater than or equal to value deposited
    # in this case, we don't profit and lose a few wei on xsushi. confirm we're no more than 5 wei off.
    vault.withdraw({"from": whale})
    assert math.isclose(token.balanceOf(whale), startingWhale, abs_tol=5)
