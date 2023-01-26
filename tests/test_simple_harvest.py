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
    is_convex,
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
    print("Harvest info:", tx.events["Harvested"])
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

    # simulate profits
    chain.sleep(sleep_time)
    chain.mine(1)

    print("earned: ", gauge.earned(velo, strategy) / 1e18)

    # harvest, store new asset amount
    chain.sleep(1)
    tx = strategy.harvest({"from": gov})
    print("Harvest info:", tx.events["Harvested"])
    chain.sleep(1)
    new_assets = vault.totalAssets()
    # confirm we made money, or at least that we have about the same
    assert new_assets >= old_assets
    print("\nAssets after 1 day: ", new_assets / 1e18)
    print("gauge_deposit", gauge.balanceOf(strategy) / 1e18)
    print("earned: ", gauge.earned(velo, strategy) / 1e18)
    print("balanceofwant: ", strategy.balanceOfWant() / 1e18)
    staked2 = strategy.stakedBalance()
    print("stakingafterharvest2: ", staked2 / 1e18)
    print("usdc bal: ", usdc.balanceOf(strategy) / 1e6)
    print("other bal: ", other.balanceOf(strategy) / 1e18)
    print("vault gauge bal: ", gauge.balanceOf(vault) / 1e18)
    print("vault token bal: ", token.balanceOf(vault) / 1e18)

    # Display estimated APR
    print(
        "\nEstimated DAI APR: ",
        "{:.2%}".format(
            ((new_assets - old_assets) * (365 * 86400 / sleep_time))
            / (strategy.estimatedTotalAssets())
        ),
    )
    print("Harvest info:", tx.events["Harvested"])

    # simulate profits
    chain.sleep(sleep_time)
    chain.mine(1)

    print("earned: ", gauge.earned(velo, strategy) / 1e18)

    # harvest, store new asset amount
    chain.sleep(1)
    tx = strategy.harvest({"from": gov})
    print("Harvest info:", tx.events["Harvested"])
    chain.sleep(1)
    new_assets = vault.totalAssets()
    # confirm we made money, or at least that we have about the same
    assert new_assets >= old_assets
    print("\nAssets after 1 day: ", new_assets / 1e18)
    print("gauge_deposit", gauge.balanceOf(strategy) / 1e18)
    print("earned: ", gauge.earned(velo, strategy) / 1e18)
    print("balanceofwant: ", strategy.balanceOfWant() / 1e18)
    staked2 = strategy.stakedBalance()
    print("stakingafterharvest2: ", staked2 / 1e18)
    print("usdc bal: ", usdc.balanceOf(strategy) / 1e6)
    print("other bal: ", other.balanceOf(strategy) / 1e18)
    print("vault gauge bal: ", gauge.balanceOf(vault) / 1e18)
    print("vault token bal: ", token.balanceOf(vault) / 1e18)

    # Display estimated APR
    print(
        "\nEstimated DAI APR: ",
        "{:.2%}".format(
            ((new_assets - old_assets) * (365 * 86400 / (sleep_time * 2)))
            / (strategy.estimatedTotalAssets())
        ),
    )
    print("Harvest info:", tx.events["Harvested"])

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
        print("Harvest info:", tx.events["Harvested"])
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

        if is_convex:
            cvx = Contract("0x4e3FBD56CD56c3e72c1403e103b45Db9da5B9D2B")
            cvx_whale = accounts.at(
                "0x28C6c06298d514Db089934071355E5743bf21d60", force=True
            )
            cvx.transfer(strategy, 1000e18, {"from": cvx_whale})

            # harvest, store new asset amount, turn off health check since we're donating a lot
            old_assets = vault.totalAssets()
            chain.sleep(1)
            chain.mine(1)
            strategy.setDoHealthCheck(False, {"from": gov})
            tx = strategy.harvest({"from": gov})
            print("Harvest info:", tx.events["Harvested"])
            chain.sleep(1)
            chain.mine(1)
            new_assets = vault.totalAssets()
            # confirm we made money, or at least that we have about the same
            assert new_assets >= old_assets
            print("\nAssets after 1 day: ", new_assets / 1e18)

            # Display estimated APR
            print(
                "\nEstimated Simulated CVX APR: ",
                "{:.2%}".format(
                    ((new_assets - old_assets) * (365 * 86400 / sleep_time))
                    / (strategy.estimatedTotalAssets())
                ),
            )
            print("CVX harvest info:", tx.events["Harvested"])
            assert tx.events["Harvested"]["profit"] > 0

        # end here if no profit, no reason to test USDC and USDT
        return

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
