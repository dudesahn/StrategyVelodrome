import brownie
from brownie import Wei, accounts, Contract, config, ZERO_ADDRESS
import math

# test cloning our strategy, make sure the cloned strategy still works just fine by sending funds to it
def test_cloning(
    gov,
    token,
    token_aleth,
    vault,
    vault_aleth,
    vault_kwenta,
    strategist,
    whale,
    whale_aleth,
    strategy,
    keeper,
    rewards,
    chain,
    contract_name,
    amount,
    pool,
    pool_aleth,
    pool_kwenta,
    gauge,
    gauge_aleth,
    gauge_kwenta,
    strategy_name,
    sleep_time,
    tests_using_tenderly,
    is_slippery,
    no_profit,
    vault_address,
    rewards_token,
    is_clonable,
    other,
    other_aleth,
    other_kwenta,
    healthCheck,
    velo,
    weth
):

    # skip this test if we don't clone
    if not is_clonable:
        return

    # tenderly doesn't work for "with brownie.reverts"
    if tests_using_tenderly:
        ## clone our strategy
        tx = strategy.cloneVeloWethStable(
            vault_aleth,
            strategist,
            rewards,
            keeper,
            gauge_aleth,
            pool_aleth,
            other_aleth,
            healthCheck,
            strategy_name,
            {"from": gov},
        )
        newStrategy = contract_name.at(tx.return_value)
    else:
        # Shouldn't be able to call initialize again
        with brownie.reverts():
            strategy.initialize(
                vault,
                strategist,
                rewards,
                keeper,
                gauge,
                pool,
                other,
                healthCheck,
                strategy_name,
                {"from": gov},
            )

        ## clone our strategy
        tx = strategy.cloneVeloWethStable(
            vault_aleth,
            strategist,
            rewards,
            keeper,
            gauge_aleth,
            pool_aleth,
            other_aleth,
            healthCheck,
            strategy_name,
            {"from": gov},
        )
        newStrategy = contract_name.at(tx.return_value)

        # Shouldn't be able to call initialize again
        with brownie.reverts():
            newStrategy.initialize(
                vault_aleth,
                strategist,
                rewards,
                keeper,
                gauge_aleth,
                pool_aleth,
                other_aleth,
                healthCheck,
                strategy_name,
                {"from": gov},
            )

        ## shouldn't be able to clone a clone
        with brownie.reverts():
            newStrategy.cloneVeloWethStable(
                vault_kwenta,
                strategist,
                rewards,
                keeper,
                gauge_kwenta,
                pool_kwenta,
                other_kwenta,
                healthCheck,
                strategy_name,
                {"from": gov},
            )

    # # revoke and get funds back into vault
    # currentDebt = vault.strategies(strategy)["debtRatio"]
    # vault.revokeStrategy(strategy, {"from": gov})
    # chain.sleep(1)
    # strategy.harvest({"from": gov})
    # chain.sleep(1)

    # attach our new strategy
    vault_aleth.addStrategy(newStrategy, 10_000, 0, 2 ** 256 - 1, 0, {"from": gov})

    # if vault_address == ZERO_ADDRESS:
    #     assert vault.withdrawalQueue(1) == newStrategy
    # else:
    #     if (
    #         vault.withdrawalQueue(2) == ZERO_ADDRESS
    #     ):  # only has convex, since we just added our clone to position index 1
    #         assert vault.withdrawalQueue(1) == newStrategy
    #     else:
    #         assert vault.withdrawalQueue(2) == newStrategy
    # assert vault.strategies(newStrategy)["debtRatio"] == currentDebt
    # assert vault.strategies(strategy)["debtRatio"] == 0

    ## deposit to the vault after approving; this is basically just our simple_harvest test
    before_pps = vault_aleth.pricePerShare()
    startingWhale = token_aleth.balanceOf(whale_aleth)
    token_aleth.approve(vault_aleth, 2 ** 256 - 1, {"from": whale_aleth})
    vault_aleth.deposit(amount, {"from": whale_aleth})

    print('newStrategy.want(): ', newStrategy.want())
    print('vault_aleth.token(): ', vault_aleth.token())
    assert newStrategy.want() == pool_aleth
    assert vault_aleth.token() == pool_aleth

    # harvest, store asset amount
    newStrategy.harvest({"from": gov})
    chain.sleep(1)
    old_assets = vault_aleth.totalAssets()
    assert old_assets > 0
    assert token_aleth.balanceOf(newStrategy) == 0
    assert newStrategy.estimatedTotalAssets() > 0
    print("\nStarting Assets: ", old_assets / 1e18)

    # try and include custom logic here to check that funds are in the staking contract (if needed)
    assert newStrategy.stakedBalance() > 0
    print("\nAssets Staked: ", newStrategy.stakedBalance() / 1e18)

    # simulate some earnings
    chain.sleep(sleep_time)
    chain.mine(1)

    # PRINTOUT
    print("\nearned: ", gauge.earned(velo, newStrategy) / 1e18)
    print("weth bal: ", weth.balanceOf(newStrategy) / 1e18)
    print("other bal: ", other.balanceOf(newStrategy) / 1e18)
    print("vault gauge bal: ", gauge.balanceOf(vault) / 1e18)
    print("vault token bal: ", token.balanceOf(vault) / 1e18)

    # harvest after a day, store new asset amount
    txh = newStrategy.harvest({"from": gov})
    new_assets = vault_aleth.totalAssets()

    # we can't use strategyEstimated Assets because the profits are sent to the vault
    assert new_assets >= old_assets
    print("\nAssets after 2 days: ", new_assets / 1e18)

    # Display estimated APR based on the two days before the pay out
    print(
        "\nEstimated APR: ",
        "{:.2%}".format(
            ((new_assets - old_assets) * (365 * (86400 / sleep_time)))
            / (newStrategy.estimatedTotalAssets())
        ),
    )

    # simulate a day of waiting for share price to bump back up
    chain.sleep(86400)
    chain.mine(1)

    # PRINTOUT
    print("\nearned: ", gauge.earned(velo, newStrategy) / 1e18)
    print("weth bal: ", weth.balanceOf(newStrategy) / 1e18)
    print("other bal: ", other.balanceOf(newStrategy) / 1e18)
    print("vault gauge bal: ", gauge.balanceOf(vault) / 1e18)
    print("vault token bal: ", token.balanceOf(vault) / 1e18)

    # withdraw and confirm we made money, or at least that we have about the same
    vault_aleth.withdraw({"from": whale_aleth})
    if is_slippery and no_profit:
        assert (
            math.isclose(token_aleth.balanceOf(whale_aleth), startingWhale, abs_tol=10)
            or token_aleth.balanceOf(whale_aleth) >= startingWhale
        )
    else:
        assert token_aleth.balanceOf(whale_aleth) >= startingWhale
    assert vault_aleth.pricePerShare() >= before_pps
