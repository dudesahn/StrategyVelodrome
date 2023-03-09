import brownie
from brownie import Contract
from brownie import config
import math

# test the our strategy's ability to deposit, harvest, and withdraw
def test_simple_harvest(
    gov,
    token,
    vault,
    whale,
    strategy,
    chain,
    gauge,
    amount,
    sleep_time,
    is_slippery,
    no_profit,
    velo,
    accounts,
    usdc,
    other
):
    ## deposit to the vault after approving
    startingWhale = token.balanceOf(whale)
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(amount, {"from": whale})
    print("vault token bal: ", token.balanceOf(vault) / 1e18)
    chain.sleep(1)
    chain.mine(1)

    # this is part of our check into the staking contract balance
    stakingBeforeHarvest = strategy.stakedBalance()
    print("stakingbeforeharvest: ", stakingBeforeHarvest / 1e18)

    # harvest, store asset amount
    tx = strategy.harvest({"from": gov})
    print("Harvest info 1:", tx.events["Harvested"])
    chain.sleep(1)
    chain.mine(1)
    old_assets = vault.totalAssets()
    assert old_assets > 0
    assert token.balanceOf(strategy) == 0
    print("gauge_deposit", gauge.balanceOf(strategy) / 1e18)
    assert strategy.estimatedTotalAssets() > 0
    print("Starting Assets: ", old_assets / 1e18)

    # try and include custom logic here to check that funds are in the staking contract (if needed)
    stakingBeforeHarvest < strategy.stakedBalance()
    staked1 = strategy.stakedBalance()

    # try an extra harvest to get the velo pumping ???
    tx = strategy.harvest({"from": gov})
    print("Harvest info 1a:", tx.events["Harvested"])

    # simulate profits
    chain.sleep(sleep_time)
    chain.mine(1)
    print("\nearned: ", gauge.earned(velo, strategy) / 1e18)
    # harvest, store new asset amount
    chain.sleep(1)
    tx = strategy.harvest({"from": gov})
    print("Harvest info 2:", tx.events["Harvested"])
    chain.sleep(1)
    new_assets = vault.totalAssets()
    # confirm we made money, or at least that we have about the same
    assert new_assets >= old_assets
    print("Assets after 1 day: ", new_assets / 1e18)
    print("gauge_deposit", gauge.balanceOf(strategy) / 1e18)
    print("balanceofwant: ", strategy.balanceOfWant() / 1e18)
    staked2 = strategy.stakedBalance()
    print("stakingafterharvest2: ", staked2 / 1e18)
    print("usdc bal: ", usdc.balanceOf(strategy) / 1e6)
    print("other bal: ", other.balanceOf(strategy) / 1e18)
    print("vault gauge bal: ", gauge.balanceOf(vault) / 1e18)
    print("vault token bal: ", token.balanceOf(vault) / 1e18)
    # Display estimated APR
    print(
        "Estimated DAI APR: ",
        "{:.2%}".format(
            ((new_assets - old_assets) * (365 * 86400 / sleep_time))
            / (strategy.estimatedTotalAssets())
        ),
    )

    # simulate profits
    chain.sleep(sleep_time * 1)
    chain.mine(1)
    print("\nearned: ", gauge.earned(velo, strategy) / 1e18)
    # harvest, store new asset amount
    chain.sleep(1)
    tx = strategy.harvest({"from": gov})
    print("Harvest info 3:", tx.events["Harvested"])
    chain.sleep(1)
    new_new_assets = vault.totalAssets()
    # confirm we made money, or at least that we have about the same
    assert new_new_assets >= new_assets
    print("Assets after 1 day: ", new_new_assets / 1e18)
    print("gauge_deposit", gauge.balanceOf(strategy) / 1e18)
    print("balanceofwant: ", strategy.balanceOfWant() / 1e18)
    staked2 = strategy.stakedBalance()
    print("stakingafterharvest2: ", staked2 / 1e18)
    print("usdc bal: ", usdc.balanceOf(strategy) / 1e6)
    print("other bal: ", other.balanceOf(strategy) / 1e18)
    print("vault gauge bal: ", gauge.balanceOf(vault) / 1e18)
    print("vault token bal: ", token.balanceOf(vault) / 1e18)
    # Display estimated APR
    print(
        "Estimated DAI APR: ",
        "{:.2%}".format(
            ((new_new_assets - new_assets) * (365 * 86400 / (sleep_time * 1)))
            / (strategy.estimatedTotalAssets())
        ),
    )

    if not no_profit:
        assert tx.events["Harvested"]["profit"] > 0

    # simulate some profits if we don't have any to make sure everything else works
    if no_profit:
        velo_whale = accounts.at(
            "0xb5a9621b0397bfc5b45896cae5998b6111bcdce6", force=True
        )
        velo.transfer(strategy, 10_000e18, {"from": velo_whale})

        # harvest, store new asset amount, turn off health check since we're donating a lot
        old_assets = vault.totalAssets()
        chain.sleep(1)
        chain.mine(1)
        strategy.setDoHealthCheck(False, {"from": gov})
        tx = strategy.harvest({"from": gov})
        print("Harvest info 6:", tx.events["Harvested"])
        chain.sleep(1)
        chain.mine(1)
        new_assets = vault.totalAssets()
        # confirm we made money, or at least that we have about the same
        assert new_assets >= old_assets
        print("\nAssets after 1 day: ", new_assets / 1e18)

        # Display estimated APR
        print(
            "\nEstimated Simulated CRV APR: ",
            "{:.2%}".format(
                ((new_assets - old_assets) * (365 * 86400 / sleep_time))
                / (strategy.estimatedTotalAssets())
            ),
        )
        print("CRV harvest info:", tx.events["Harvested"])
        assert tx.events["Harvested"]["profit"] > 0

    # simulate a day of waiting for share price to bump back up
    chain.sleep(86400)
    chain.mine(1)

    # withdraw and confirm we made money, or at least that we have about the same
    vault.withdraw({"from": whale})
    if is_slippery and no_profit:
        assert (
            math.isclose(token.balanceOf(whale), startingWhale, abs_tol=10)
            or token.balanceOf(whale) >= startingWhale
        )
    else:
        assert token.balanceOf(whale) >= startingWhale
