import brownie
from brownie import Wei, accounts, Contract, config, ZERO_ADDRESS
import math

# test cloning our strategy, make sure the cloned strategy still works just fine by sending funds to it
def test_cloning(
    gov,
    token,
    token_wsteth,
    vault,
    vault_wsteth,
    vault_kwenta,
    strategist,
    whale,
    whale_wsteth,
    strategy,
    keeper,
    rewards,
    chain,
    contract_name,
    amount,
    pool,
    pool_wsteth,
    pool_kwenta,
    gauge,
    gauge_wsteth,
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
    other_wsteth,
    other_kwenta,
    healthCheck
):

    # skip this test if we don't clone
    if not is_clonable:
        return

    # tenderly doesn't work for "with brownie.reverts"
    if tests_using_tenderly:
        ## clone our strategy
        tx = strategy.cloneVeloWethVolatile(
            vault_wsteth,
            strategist,
            rewards,
            keeper,
            gauge_wsteth,
            pool_wsteth,
            other_wsteth,
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
        tx = strategy.cloneVeloWethVolatile(
            vault_wsteth,
            strategist,
            rewards,
            keeper,
            gauge_wsteth,
            pool_wsteth,
            other_wsteth,
            healthCheck,
            strategy_name,
            {"from": gov},
        )
        newStrategy = contract_name.at(tx.return_value)

        # Shouldn't be able to call initialize again
        with brownie.reverts():
            newStrategy.initialize(
                vault_wsteth,
                strategist,
                rewards,
                keeper,
                gauge_wsteth,
                pool_wsteth,
                other_wsteth,
                healthCheck,
                strategy_name,
                {"from": gov},
            )

        ## shouldn't be able to clone a clone
        with brownie.reverts():
            newStrategy.cloneVeloWethVolatile(
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
    vault_wsteth.addStrategy(newStrategy, 10_000, 0, 2 ** 256 - 1, 0, {"from": gov})

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
    before_pps = vault_wsteth.pricePerShare()
    startingWhale = token_wsteth.balanceOf(whale_wsteth)
    token_wsteth.approve(vault_wsteth, 2 ** 256 - 1, {"from": whale_wsteth})
    vault_wsteth.deposit(amount, {"from": whale_wsteth})

    print('newStrategy.want(): ', newStrategy.want())
    print('vault_wsteth.token(): ', vault_wsteth.token())
    assert newStrategy.want() == pool_wsteth
    assert vault_wsteth.token() == pool_wsteth

    # harvest, store asset amount
    newStrategy.harvest({"from": gov})
    chain.sleep(1)
    old_assets = vault_wsteth.totalAssets()
    assert old_assets > 0
    assert token_wsteth.balanceOf(newStrategy) == 0
    assert newStrategy.estimatedTotalAssets() > 0
    print("\nStarting Assets: ", old_assets / 1e18)

    # try and include custom logic here to check that funds are in the staking contract (if needed)
    assert newStrategy.stakedBalance() > 0
    print("\nAssets Staked: ", newStrategy.stakedBalance() / 1e18)

    # simulate some earnings
    chain.sleep(sleep_time)
    chain.mine(1)

    # harvest after a day, store new asset amount
    newStrategy.harvest({"from": gov})
    new_assets = vault_wsteth.totalAssets()

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

    # withdraw and confirm we made money, or at least that we have about the same
    vault_wsteth.withdraw({"from": whale_wsteth})
    if is_slippery and no_profit:
        assert (
            math.isclose(token_wsteth.balanceOf(whale_wsteth), startingWhale, abs_tol=10)
            or token_wsteth.balanceOf(whale_wsteth) >= startingWhale
        )
    else:
        assert token_wsteth.balanceOf(whale_wsteth) >= startingWhale
    assert vault_wsteth.pricePerShare() >= before_pps
