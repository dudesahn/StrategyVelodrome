import brownie
from brownie import Contract
from brownie import config
import math

# test our harvest triggers
def test_triggers(
    gov,
    token,
    vault,
    whale,
    strategy,
    chain,
    amount,
    gasOracle,
    is_slippery,
    no_profit,
    sleep_time,
    oracle_gov
):

    gasOracle.setMaxAcceptableBaseFee(10000 * 1e9, {"from": oracle_gov})

    ## deposit to the vault after approving
    startingWhale = token.balanceOf(whale)
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(amount, {"from": whale})

    # harvest the credit
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)
    chain.mine(1)

    # simulate earnings
    chain.sleep(sleep_time)
    chain.mine(1)

    # set our max delay to 1 day so we trigger true, then set it back to 21 days
    strategy.setMaxReportDelay(sleep_time - 1)
    tx = strategy.harvestTrigger(0, {"from": gov})
    print("\nShould we harvest? Should be True.", tx)
    assert tx == True
    strategy.setMaxReportDelay(86400 * 21)

    # curve uses minDelay as well
    strategy.setMinReportDelay(sleep_time - 1)
    tx = strategy.harvestTrigger(0, {"from": gov})
    print("\nShould we harvest? Should be True.", tx)
    assert tx == True

    # harvest, wait
    chain.sleep(1)
    tx = strategy.harvest({"from": gov})
    print("Harvest info:", tx.events["Harvested"])
    chain.sleep(sleep_time)
    chain.mine(1)

    # harvest should trigger false due to high gas price
    gasOracle.setMaxAcceptableBaseFee(1 * 1e9, {"from": oracle_gov})
    tx = strategy.harvestTrigger(0, {"from": gov})
    print("\nShould we harvest? Should be false.", tx)
    # assert tx == False # fails because no baseFeeProvider on Optimism

    # withdraw and confirm we made money, or at least that we have about the same
    vault.withdraw({"from": whale})
    if is_slippery and no_profit:
        assert (
            math.isclose(token.balanceOf(whale), startingWhale, abs_tol=10)
            or token.balanceOf(whale) >= startingWhale
        )
    else:
        assert token.balanceOf(whale) >= startingWhale