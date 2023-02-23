import brownie
from brownie import Wei, accounts, Contract, config, ZERO_ADDRESS
import math

# test cloning our strategy, make sure the cloned strategy still works just fine by sending funds to it
def test_cloning(
    gov,
    token,
    token_dola,
    vault,
    vault_dola,
    vault_mai,
    strategist,
    whale,
    whale_dola,
    strategy,
    keeper,
    rewards,
    chain,
    contract_name,
    amount,
    pool,
    pool_dola,
    pool_mai,
    gauge,
    gauge_dola,
    gauge_mai,
    strategy_name,
    sleep_time,
    tests_using_tenderly,
    is_slippery,
    no_profit,
    vault_address,
    rewards_token,
    is_clonable,
    other,
    other_dola,
    other_mai,
    healthCheck
):

    # skip this test if we don't clone
    if not is_clonable:
        return

    # tenderly doesn't work for "with brownie.reverts"
    if tests_using_tenderly:
        ## clone our strategy
        tx = strategy.cloneVeloUsdc(
            vault_dola,
            strategist,
            rewards,
            keeper,
            gauge_dola,
            pool_dola,
            other_dola,
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
        tx = strategy.cloneVeloUsdc(
            vault_dola,
            strategist,
            rewards,
            keeper,
            gauge_dola,
            pool_dola,
            other_dola,
            healthCheck,
            strategy_name,
            {"from": gov},
        )
        newStrategy = contract_name.at(tx.return_value)

        # Shouldn't be able to call initialize again
        with brownie.reverts():
            newStrategy.initialize(
                vault_dola,
                strategist,
                rewards,
                keeper,
                gauge_dola,
                pool_dola,
                other_dola,
                healthCheck,
                strategy_name,
                {"from": gov},
            )

        ## shouldn't be able to clone a clone
        with brownie.reverts():
            newStrategy.cloneVeloUsdc(
                vault_mai,
                strategist,
                rewards,
                keeper,
                gauge_mai,
                pool_mai,
                other_mai,
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
    vault_dola.addStrategy(newStrategy, 10_000, 0, 2 ** 256 - 1, 0, {"from": gov})

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
    before_pps = vault_dola.pricePerShare()
    startingWhale = token_dola.balanceOf(whale_dola)
    token_dola.approve(vault_dola, 2 ** 256 - 1, {"from": whale_dola})
    vault_dola.deposit(amount, {"from": whale_dola})

    print('newStrategy.want(): ', newStrategy.want())
    print('vault_dola.token(): ', vault_dola.token())
    assert newStrategy.want() == pool_dola
    assert vault_dola.token() == pool_dola

    # harvest, store asset amount
    newStrategy.harvest({"from": gov})
    chain.sleep(1)
    old_assets = vault_dola.totalAssets()
    assert old_assets > 0
    assert token_dola.balanceOf(newStrategy) == 0
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
    new_assets = vault_dola.totalAssets()

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
    vault_dola.withdraw({"from": whale_dola})
    if is_slippery and no_profit:
        assert (
            math.isclose(token_dola.balanceOf(whale_dola), startingWhale, abs_tol=10)
            or token_dola.balanceOf(whale_dola) >= startingWhale
        )
    else:
        assert token_dola.balanceOf(whale_dola) >= startingWhale
    assert vault_dola.pricePerShare() >= before_pps
