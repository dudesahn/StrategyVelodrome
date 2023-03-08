import pytest
from brownie import config, Wei, Contract, chain, ZERO_ADDRESS
import requests

# Snapshots the chain before each test and reverts after test completion.
@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


# set this for if we want to use tenderly or not; mostly helpful because with brownie.reverts fails in tenderly forks.
use_tenderly = False


################################################## TENDERLY DEBUGGING ##################################################

# change autouse to True if we want to use this fork to help debug tests
@pytest.fixture(scope="session", autouse=use_tenderly)
def tenderly_fork(web3, chain):
    fork_base_url = "https://simulate.yearn.network/fork"
    payload = {"network_id": str(chain.id)}
    resp = requests.post(fork_base_url, headers={}, json=payload)
    fork_id = resp.json()["simulation_fork"]["id"]
    fork_rpc_url = f"https://rpc.tenderly.co/fork/{fork_id}"
    print(fork_rpc_url)
    tenderly_provider = web3.HTTPProvider(fork_rpc_url, {"timeout": 600})
    web3.provider = tenderly_provider
    print(f"https://dashboard.tenderly.co/yearn/yearn-web/fork/{fork_id}")


################################################ UPDATE THINGS BELOW HERE ################################################


@pytest.fixture(scope="session")
def tests_using_tenderly():
    yes_or_no = use_tenderly
    yield yes_or_no


# use this to set what chain we use. 1 for ETH, 250 for fantom, 10 for optimism
chain_used = 10


# this is the amount of funds we have our whale deposit. adjust this as needed based on their wallet balance
@pytest.fixture(scope="session")
def amount():
    amount = 0.1e18
    yield amount


@pytest.fixture(scope="session")
def whale(accounts, amount, token):
    # Totally in it for the tech
    # Update this with a large holder of your want token (the largest EOA holder of LP)
    # MIM 0xe896e539e557BC751860a7763C8dD589aF1698Ce, FRAX 0x839Bb033738510AA6B4f78Af20f066bdC824B189
    whale = accounts.at("0x099b3368eb5bbe6f67f14a791ecaef8bc1628a7f", force=True) # usdc-snx gauge
    if token.balanceOf(whale) < 2 * amount:
        raise ValueError(
            "Our whale needs more funds. Find another whale or reduce your amount variable."
        )
    yield whale

@pytest.fixture(scope="session")
def whale_dola(accounts, amount, token_dola):
    # Totally in it for the tech
    # Update this with a large holder of your want token (the largest EOA holder of LP)
    # MIM 0xe896e539e557BC751860a7763C8dD589aF1698Ce, FRAX 0x839Bb033738510AA6B4f78Af20f066bdC824B189
    whale_dola = accounts.at("0xAFD2c84b9d1cd50E7E18a55e419749A6c9055E1F", force=True)
    if token_dola.balanceOf(whale_dola) < 2 * amount:
        raise ValueError(
            "Our whale needs more funds. Find another whale or reduce your amount variable."
        )
    yield whale_dola

# use this if your vault is already deployed
@pytest.fixture(scope="session")
def vault_address():
    vault_address = ZERO_ADDRESS
    # MIM 0x2DfB14E32e2F8156ec15a2c21c3A6c053af52Be8
    # FRAX 0xB4AdA607B9d6b2c9Ee07A275e9616B84AC560139
    yield vault_address


# curve deposit pool for old pools, set to ZERO_ADDRESS otherwise
@pytest.fixture(scope="session")
def old_pool():
    old_pool = ZERO_ADDRESS
    yield old_pool


# this is the name we want to give our strategy
@pytest.fixture(scope="session")
def strategy_name():
    strategy_name = "StrategyCurveOptimismSUSD"
    yield strategy_name


# this is the name of our strategy in the .sol file
@pytest.fixture(scope="session")
def contract_name(StrategyVeloUsdcVolatileClonable):
    contract_name = StrategyVeloUsdcVolatileClonable
    yield contract_name


# this is the address of our rewards token
@pytest.fixture(scope="session")
def rewards_token():  # VELO
    yield Contract("0x3c8B650257cFb5f272f799F5e2b4e65093a11a05")


# whether or not we should try a test donation of our rewards token to make sure the strategy handles them correctly
# if you want to bother with whale and amount below, this needs to be true
@pytest.fixture(scope="session")
def test_donation():
    test_donation = True
    yield test_donation


# whether or not a strategy is clonable. if true, don't forget to update what our cloning function is called in test_cloning.py
@pytest.fixture(scope="session")
def is_clonable():
    is_clonable = True
    yield is_clonable


# if our gauge deposits aren't tokenized (older pools), we can't as easily do some tests and we skip them
@pytest.fixture(scope="session")
def gauge_is_not_tokenized():
    gauge_is_not_tokenized = True
    yield gauge_is_not_tokenized


# use this to test our strategy in case there are no profits
@pytest.fixture(scope="session")
def no_profit():
    no_profit = False
    yield no_profit


# use this when we might lose a few wei on conversions between want and another deposit token
# generally this will always be true if no_profit is true, even for curve/convex since we can lose a wei converting
@pytest.fixture(scope="session")
def is_slippery(no_profit):
    is_slippery = False
    if no_profit:
        is_slippery = True
    yield is_slippery


# use this to set the standard amount of time we sleep between harvests.
# generally 1 day, but can be less if dealing with smaller windows (oracles) or longer if we need to trigger weekly earnings.
@pytest.fixture(scope="session")
def sleep_time():
    hour = 3600 # seconds

    # change this one right here
    hours_to_sleep = 24

    sleep_time = hour * hours_to_sleep
    yield sleep_time


################################################ UPDATE THINGS ABOVE HERE ################################################

# Only worry about changing things above this line, unless you want to make changes to the vault or strategy.
# ----------------------------------------------------------------------- #

# if chain_used == 1:  # mainnet

    # @pytest.fixture(scope="session")
    # def sushi_router():  # use this to check our allowances
    #     yield Contract("0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F")

    # # # all contracts below should be able to stay static based on the pid
    # # @pytest.fixture(scope="session")
    # # def booster():  # this is the deposit contract
    # #     yield Contract("0xF403C135812408BFbE8713b5A23a04b3D48AAE31")

    # @pytest.fixture(scope="session")
    # def voter():
    #     yield Contract("0xF147b8125d2ef93FB6965Db97D6746952a133934")

    # @pytest.fixture(scope="session")
    # def convexToken():
    #     yield Contract("0x4e3FBD56CD56c3e72c1403e103b45Db9da5B9D2B")

    # @pytest.fixture(scope="session")
    # def crv():
    #     yield Contract("0xD533a949740bb3306d119CC777fa900bA034cd52")

    # @pytest.fixture(scope="session")
    # def other_vault_strategy():
    #     yield Contract("0x8423590CD0343c4E18d35aA780DF50a5751bebae")

    # # @pytest.fixture(scope="session")
    # # def proxy():
    # #     yield Contract("0xA420A63BbEFfbda3B147d0585F1852C358e2C152")

    # @pytest.fixture(scope="session")
    # def curve_registry():
    #     yield Contract("0x90E00ACe148ca3b23Ac1bC8C240C2a7Dd9c2d7f5")

    # @pytest.fixture(scope="session")
    # def curve_cryptoswap_registry():
    #     yield Contract("0x4AacF35761d06Aa7142B9326612A42A2b9170E33")

    # @pytest.fixture(scope="session")
    # def healthCheck():
    #     yield Contract("0xDDCea799fF1699e98EDF118e0629A974Df7DF012")

    # @pytest.fixture(scope="session")
    # def farmed():
    #     # this is the token that we are farming and selling for more of our want.
    #     yield Contract("0xD533a949740bb3306d119CC777fa900bA034cd52")

    # # @pytest.fixture(scope="session")
    # # def token(pid):
    # #     # this should be the address of the ERC-20 used by the strategy/vault
    # #     #token_address = booster.poolInfo(pid)[0]
    # #     yield Contract(token_address)

    # @pytest.fixture(scope="session")
    # def cvxDeposit(pid):
    #     # this should be the address of the convex deposit token
    #     #cvx_address = booster.poolInfo(pid)[1]
    #     yield Contract(cvx_address)

    # @pytest.fixture(scope="session")
    # def rewardsContract(pid):
    #     #rewardsContract = booster.poolInfo(pid)[3]
    #     yield Contract(rewardsContract)

    # # gauge for the curve pool
    # @pytest.fixture(scope="session")
    # def gauge():
    #     yield Contract("0xb03f52D2DB3e758DD49982Defd6AeEFEa9454e80") #USDC/sUSD gauge

    # # curve deposit pool
    # @pytest.fixture(scope="session")
    # def pool(token, curve_registry, curve_cryptoswap_registry, old_pool):
    #     if old_pool == ZERO_ADDRESS:
    #         if curve_registry.get_pool_from_lp_token(token) == ZERO_ADDRESS:
    #             if (
    #                 curve_cryptoswap_registry.get_pool_from_lp_token(token)
    #                 == ZERO_ADDRESS
    #             ):
    #                 poolContract = token
    #             else:
    #                 poolAddress = curve_cryptoswap_registry.get_pool_from_lp_token(
    #                     token
    #                 )
    #                 poolContract = Contract(poolAddress)
    #         else:
    #             poolAddress = curve_registry.get_pool_from_lp_token(token)
    #             poolContract = Contract(poolAddress)
    #     else:
    #         poolContract = Contract(old_pool)
    #     yield poolContract

    # @pytest.fixture(scope="session")
    # def gasOracle():
    #     yield Contract("0xb5e1CAcB567d98faaDB60a1fD4820720141f064F")

    # # Define any accounts in this section
    # # for live testing, governance is the strategist MS; we will update this before we endorse
    # # normal gov is ychad, 0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52
    # @pytest.fixture(scope="session")
    # def gov(accounts):
    #     yield accounts.at("0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52", force=True)

    # @pytest.fixture(scope="session")
    # def strategist_ms(accounts):
    #     # like governance, but better
    #     yield accounts.at("0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7", force=True)

    # # set all of these accounts to SMS as well, just for testing
    # @pytest.fixture(scope="session")
    # def keeper(accounts):
    #     yield accounts.at("0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7", force=True)

    # @pytest.fixture(scope="session")
    # def rewards(accounts):
    #     yield accounts.at("0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7", force=True)

    # @pytest.fixture(scope="session")
    # def guardian(accounts):
    #     yield accounts.at("0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7", force=True)

    # @pytest.fixture(scope="session")
    # def management(accounts):
    #     yield accounts.at("0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7", force=True)

    # @pytest.fixture(scope="session")
    # def strategist(accounts):
    #     yield accounts.at("0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7", force=True)

    

if chain_used == 10:  # optimism

    @pytest.fixture(scope="session")
    def velo():
        yield Contract("0x3c8B650257cFb5f272f799F5e2b4e65093a11a05")

    @pytest.fixture(scope="session")
    def other_vault_strategy():
        yield Contract("0xf8aD69d578bd58c7d3Ff643A22355f0BFd5cA12A")

    # @pytest.fixture(scope="session")
    # def curve_registry():
    #     yield Contract("0x90E00ACe148ca3b23Ac1bC8C240C2a7Dd9c2d7f5")

    @pytest.fixture(scope="session")
    def healthCheck():
        yield Contract("0x3d8F58774611676fd196D26149C71a9142C45296")

    # this is the token that we are farming and selling for more of our want.
    @pytest.fixture(scope="session")
    def farmed():
        yield Contract("0x3c8B650257cFb5f272f799F5e2b4e65093a11a05")

    # our velodrome usdc-snx lp token
    @pytest.fixture(scope="session")	
    def token():
        yield Contract("0x9056EB7Ca982a5Dd65A584189994e6a27318067D")
    
    # our velodrome dola lp token
    @pytest.fixture(scope="session")	
    def token_dola():
        yield Contract("0x6C5019D345Ec05004A7E7B0623A91a0D9B8D590d")
    
    # our velodrome mai lp token
    @pytest.fixture(scope="session")	
    def token_mai():
        yield Contract("0xd62C9D8a3D4fd98b27CaaEfE3571782a3aF0a737")

    # gauge for the velodrome pool token
    @pytest.fixture(scope="session")	
    def gauge():	
        yield Contract("0x099b3368eb5bbe6f67f14a791ecaef8bc1628a7f") #USDC/SNX gauge
    
    # gauge for the velodrome pool token
    @pytest.fixture(scope="session")	
    def gauge_dola():	
        yield Contract("0xAFD2c84b9d1cd50E7E18a55e419749A6c9055E1F") #USDC/DOLA gauge
    
    # gauge for the velodrome pool token
    @pytest.fixture(scope="session")	
    def gauge_mai():	
        yield Contract("0xDF479E13E71ce207CE1e58D6f342c039c3D90b7D") #USDC/DOLA gauge

    # gauge for the velodrome pool token
    @pytest.fixture(scope="session")	
    def gauge_addr(accounts):	
        yield accounts.at("0x099b3368eb5bbe6f67f14a791ecaef8bc1628a7f", force=True) #USDC/snx gauge
    
    @pytest.fixture(scope="session")
    def pool():	
        yield Contract("0x9056EB7Ca982a5Dd65A584189994e6a27318067D") # same as token

    @pytest.fixture(scope="session")
    def pool_dola():	
        yield Contract("0x6C5019D345Ec05004A7E7B0623A91a0D9B8D590d") # same as token

    @pytest.fixture(scope="session")
    def pool_mai():	
        yield Contract("0xd62C9D8a3D4fd98b27CaaEfE3571782a3aF0a737") # same as token

    @pytest.fixture(scope="session")
    def pool_addr(accounts):	
        yield accounts.at("0x9056EB7Ca982a5Dd65A584189994e6a27318067D", force=True) # same as token

    @pytest.fixture(scope="session")
    def usdc():	
        yield Contract("0x7F5c764cBc14f9669B88837ca1490cCa17c31607") # usdc

    @pytest.fixture(scope="session")
    def other():	
        yield Contract("0x8700dAec35aF8Ff88c16BdF0418774CB3D7599B4") # snx

    @pytest.fixture(scope="session")
    def other_dola():	
        yield Contract("0x8aE125E8653821E851F12A49F7765db9a9ce7384") # dola
    
    @pytest.fixture(scope="session")
    def other_mai():	
        yield Contract("0xdFA46478F9e5EA86d57387849598dbFB2e964b02") # mai

    @pytest.fixture(scope="session")
    def dai():
        yield Contract("0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1")

    @pytest.fixture(scope="session")
    def other_addr(accounts):	
        yield accounts.at("0x8700dAec35aF8Ff88c16BdF0418774CB3D7599B4", force=True) # snx

    @pytest.fixture(scope="session")	
    def gasOracle():	
        yield Contract("0xbf4A735F123A9666574Ff32158ce2F7b7027De9A")

    # Define any accounts in this section
    # for live testing, governance is the strategist MS; we will update this before we endorse
    # normal gov is ychad, 0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52
    @pytest.fixture(scope="session")
    def gov(accounts):
        yield accounts.at("0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52", force=True)

    @pytest.fixture(scope="session")
    def strategist_ms(accounts):
        # like governance, but better
        yield accounts.at("0xea3a15df68fCdBE44Fdb0DB675B2b3A14a148b26", force=True)

    # oracle gov on optimism is currently set to an eoa
    @pytest.fixture(scope="session")
    def oracle_gov(accounts):
        yield accounts.at("0xc6387e937bcef8de3334f80edc623275d42457ff", force=True)

    @pytest.fixture(scope="session")
    def keeper(accounts):
        yield accounts.at("0xD222297173C67f4967FFa61efE860047D6460780", force=True) # not updated for optimism

    @pytest.fixture(scope="session")
    def rewards(accounts):
        yield accounts.at("0x84654e35E504452769757AAe5a8C7C6599cBf954", force=True)

    @pytest.fixture(scope="session")
    def guardian(accounts):
        yield accounts[2]

    @pytest.fixture(scope="session")
    def management(accounts):
        yield accounts[3]

    @pytest.fixture(scope="session")
    def strategist(accounts):
        yield accounts.at("0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7", force=True)

    @pytest.fixture(scope="module")
    def vault(pm, gov, rewards, guardian, management, token, chain, vault_address):
        if vault_address == ZERO_ADDRESS:
            Vault = pm(config["dependencies"][0]).Vault
            vault = guardian.deploy(Vault)
            vault.initialize(token, gov, rewards, "", "", guardian)
            vault.setDepositLimit(2 ** 256 - 1, {"from": gov})
            vault.setManagement(management, {"from": gov})
            chain.sleep(1)
            chain.mine(1)
        else:
            vault = Contract(vault_address)
        yield vault

    @pytest.fixture(scope="module")
    def vault_dola(pm, gov, rewards, guardian, management, token_dola, chain, vault_address):
        if vault_address == ZERO_ADDRESS:
            Vault = pm(config["dependencies"][0]).Vault
            vault_dola = guardian.deploy(Vault)
            vault_dola.initialize(token_dola, gov, rewards, "", "", guardian)
            vault_dola.setDepositLimit(2 ** 256 - 1, {"from": gov})
            vault_dola.setManagement(management, {"from": gov})
            chain.sleep(1)
            chain.mine(1)
        else:
            vault_dola = Contract(vault_address)
        yield vault_dola
    
    @pytest.fixture(scope="module")
    def vault_mai(pm, gov, rewards, guardian, management, token_mai, chain, vault_address):
        if vault_address == ZERO_ADDRESS:
            Vault = pm(config["dependencies"][0]).Vault
            vault = guardian.deploy(Vault)
            vault.initialize(token_mai, gov, rewards, "", "", guardian)
            vault.setDepositLimit(2 ** 256 - 1, {"from": gov})
            vault.setManagement(management, {"from": gov})
            chain.sleep(1)
            chain.mine(1)
        else:
            vault = Contract(vault_address)
        yield vault

    # replace the first value with the name of your strategy
    @pytest.fixture(scope="module")
    def strategy(
        contract_name,
        strategist,
        keeper,
        vault,
        gov,
        healthCheck,
        chain,
        pool,
        other,
        strategy_name,
        gasOracle,
        oracle_gov,
        gauge,
        vault_address,
    ):
        # make sure to include all constructor parameters needed here
        strategy = strategist.deploy(
            contract_name,
            vault,
            gauge,
            pool,
            other,
            healthCheck,
            strategy_name,
        )
        print("\nCurve strategy")

        strategy.setKeeper(keeper, {"from": gov})

        # set our management fee to zero so it doesn't mess with our profit checking
        vault.setManagementFee(0, {"from": gov})

        # start with other_strat as zero
        other_strat = ZERO_ADDRESS

        # do slightly different if vault is existing or not
        if vault_address == ZERO_ADDRESS:
            vault.addStrategy(
                strategy, 10_000, 0, 2 ** 256 - 1, 0, {"from": gov}
            )
            print("New Vault, Velodrome Strategy")
            chain.sleep(1)
            chain.mine(1)
        else:
            if vault.withdrawalQueue(1) == ZERO_ADDRESS:  # only has convex
                other_strat = Contract(vault.withdrawalQueue(0))
                vault.updateStrategyDebtRatio(other_strat, 5000, {"from": gov})
                vault.addStrategy(
                    strategy, 5000, 0, 2 ** 256 - 1, 0, {"from": gov}
                )

                # reorder so curve first, convex second
                queue = [strategy.address, other_strat.address]
                for x in range(18):
                    queue.append(ZERO_ADDRESS)
                assert len(queue) == 20
                vault.setWithdrawalQueue(queue, {"from": gov})

                # turn off health check just in case it's a big harvest
                other_strat.setDoHealthCheck(False, {"from": gov})
                other_strat.harvest({"from": gov})
                chain.sleep(1)
                chain.mine(1)
            else:
                other_strat = Contract(vault.withdrawalQueue(1))
                # remove 50% of funds from our convex strategy
                vault.updateStrategyDebtRatio(other_strat, 5000, {"from": gov})

                # turn off health check just in case it's a big harvest
                try:
                    other_strat.setDoHealthCheck(False, {"from": gov})
                except:
                    print("This strategy doesn't have health check")
                other_strat.harvest({"from": gov})
                chain.sleep(1)
                chain.mine(1)

                # give our curve strategy 50% of our debt and migrate it
                old_strategy = Contract(vault.withdrawalQueue(0))
                vault.migrateStrategy(old_strategy, strategy, {"from": gov})
                vault.updateStrategyDebtRatio(strategy, 5000, {"from": gov})

        # make all harvests permissive unless we change the value lower
        gasOracle.setMaxAcceptableBaseFee(2000 * 1e9, {"from": oracle_gov})
        strategy.setHealthCheck(healthCheck, {"from": gov})

        # set up custom params and setters
        strategy.setMaxReportDelay(86400 * 21, {"from": gov})

        # harvest to send our funds into the strategy and fix any triggers already true
        if vault_address != ZERO_ADDRESS:
            tx = strategy.harvest({"from": gov})
            print(
                "Profits on first harvest (should only be on migrations):",
                tx.events["Harvested"]["profit"] / 1e18,
            )
        chain.sleep(10 * 3600)  # normalize share price
        chain.mine(1)

        # print assets in each strategy
        if vault_address != ZERO_ADDRESS and other_strat != ZERO_ADDRESS:
            print("Other strat assets:", other_strat.estimatedTotalAssets() / 1e18)
        print("Main strat assets:", strategy.estimatedTotalAssets() / 1e18)

        yield strategy

# commented-out fixtures to be used with live testing

# # list any existing strategies here
# @pytest.fixture(scope="session")
# def LiveStrategy_1():
#     yield Contract("0xC1810aa7F733269C39D640f240555d0A4ebF4264")


# use this if your strategy is already deployed
# @pytest.fixture(scope="module")
# def strategy():
#     # parameters for this are: strategy, vault, max deposit, minTimePerInvest, slippage protection (10000 = 100% slippage allowed),
#     strategy = Contract("0xC1810aa7F733269C39D640f240555d0A4ebF4264")
#     yield strategy