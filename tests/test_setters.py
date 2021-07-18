import brownie
from brownie import Contract
from brownie import config


def test_setters(
    gov, strategy, strategist, chain, whale
):

	# test our setters in baseStrategy and our main strategy
    strategy.setDebtThreshold(100, {"from": gov})
    strategy.setMaxReportDelay(0, {"from": gov})
    strategy.setMaxReportDelay(1e18, {"from": gov})
    strategy.setMetadataURI(0, {"from": gov})
    strategy.setMinReportDelay(100, {"from": gov})
    strategy.setProfitFactor(1000, {"from": gov})
    strategy.setRewards(strategist, {"from": strategist})
    strategy.setStrategist(strategist, {"from": strategist})
    name = strategy.name()
    print("Strategy Name:", name)
    
    # health check stuff
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)
    strategy.setDoHealthCheck(False, {"from": gov})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)
    strategy.setDoHealthCheck(False, {"from": gov})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)
    
    
    strategy.setMaxReportDelay(10, {"from": gov})
    zero = "0x0000000000000000000000000000000000000000"

    with brownie.reverts():
        strategy.setKeeper(zero, {"from": gov})
    with brownie.reverts():
        strategy.setRewards(zero, {"from": gov})
    with brownie.reverts():
        strategy.setStrategist(zero, {"from": gov})
    with brownie.reverts():
        strategy.setDoHealthCheck(False, {"from": whale})
    with brownie.reverts():
        strategy.setEmergencyExit({"from": whale})
    with brownie.reverts():
        strategy.setMaxReportDelay(1000, {"from": whale})
    with brownie.reverts():
        strategy.setRewards(strategist, {"from": whale})
    
    
    # set emergency exit last
    strategy.setEmergencyExit({"from": gov})
    with brownie.reverts():
    	strategy.setEmergencyExit({"from": gov})