import brownie
from brownie import Contract
from brownie import config
import math


def test_revoke_strategy_from_vault(
    gov, token, vault, whale, chain, strategy,
):

    ## deposit to the vault after approving
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(1000e18, {"from": whale})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)

    vaultAssets_starting = vault.totalAssets()
    vault_holdings_starting = token.balanceOf(vault)
    strategy_starting = strategy.estimatedTotalAssets()
    vault.revokeStrategy(strategy.address, {"from": gov})
    
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)
    vaultAssets_after_revoke = vault.totalAssets()

    # normally, we would assert value to be greater than or equal to value deposited
    # in this case, we don't profit and lose a few wei on xsushi. confirm we're no more than 5 wei off.
    assert math.isclose(vaultAssets_after_revoke, vaultAssets_starting, abs_tol=5)
    assert strategy.estimatedTotalAssets() == 0
    assert token.balanceOf(vault) >= vault_holdings_starting + strategy_starting

    # simulate a day of waiting for share price to bump back up
    chain.sleep(86400)
    chain.mine(1)

    # normally, we would assert value to be greater than or equal to value deposited
    # in this case, we don't profit and lose a few wei on xsushi. confirm we're no more than 5 wei off.
    assert math.isclose(vault.totalAssets(), vaultAssets_after_revoke, abs_tol=5)
