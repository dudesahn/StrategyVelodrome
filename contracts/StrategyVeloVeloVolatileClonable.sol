// SPDX-License-Identifier: AGPL-3.0
pragma solidity ^0.8.15;

// These are the core Yearn libraries
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/utils/math/Math.sol";
import "@yearnvaults/contracts/BaseStrategy.sol";

interface IVelodromeRouter {
    function addLiquidity(
        address,
        address,
        bool,
        uint256,
        uint256,
        uint256,
        uint256,
        address,
        uint256
    )
        external
        returns (
            uint256 amountA,
            uint256 amountB,
            uint256 liquidity
        );

    function swapExactTokensForTokensSimple(
        uint256 amountIn,
        uint256 amountOutMin,
        address tokenFrom,
        address tokenTo,
        bool stable,
        address to,
        uint256 deadline
    ) external returns (uint256[] memory amounts);

    function getAmountOut(
        uint256 amountIn,
        address tokenIn,
        address tokenOut
    ) external view returns (uint256 amount, bool stable);
}

interface IGauge {
    function deposit(uint256 amount, uint256 tokenId) external;

    function balanceOf(address) external view returns (uint256);

    function withdraw(uint256 amount) external;

    function getReward(address account, address[] memory tokens) external;

    function stake() external view returns (address);
}

abstract contract StrategyVeloBase is BaseStrategy {
    /* ========== STATE VARIABLES ========== */
    // these should stay the same across different wants.

    // Velodrome stuff
    address public pool; // This is our velodrome pool specific to this vault
    address public gauge; // gauge address

    // swap stuff
    address internal constant velodromeRouter =
        0xa132DAB612dB5cB9fC9Ac426A0Cc215A3423F9c9;
    IERC20 internal constant velo =
        IERC20(0x3c8B650257cFb5f272f799F5e2b4e65093a11a05);

    address[] public rewardsTokens;

    string internal stratName;

    /* ========== CONSTRUCTOR ========== */

    constructor(address _vault) BaseStrategy(_vault) {}

    /* ========== VIEWS ========== */

    function name() external view override returns (string memory) {
        return stratName;
    }

    ///@notice How much want we have staked in Velodrome's gauge
    function stakedBalance() public view returns (uint256) {
        return IGauge(gauge).balanceOf(address(this));
    }

    ///@notice Balance of want sitting in our strategy
    function balanceOfWant() public view returns (uint256) {
        return want.balanceOf(address(this));
    }

    function estimatedTotalAssets() public view override returns (uint256) {
        return balanceOfWant() + stakedBalance();
    }

    /* ========== MUTATIVE FUNCTIONS ========== */

    function adjustPosition(uint256 _debtOutstanding) internal override {
        if (emergencyExit) {
            return;
        }
        // Deposit all of our LP tokens in the gauge, if we have any
        uint256 _toInvest = balanceOfWant();
        if (_toInvest > 0) {
            IGauge(gauge).deposit(_toInvest, 0); // tokenId = 0
        }
    }

    function liquidatePosition(uint256 _amountNeeded)
        internal
        override
        returns (uint256 _liquidatedAmount, uint256 _loss)
    {
        uint256 _wantBal = balanceOfWant();
        if (_amountNeeded > _wantBal) {
            // check if we have enough free funds to cover the withdrawal
            uint256 _stakedBal = stakedBalance();
            if (_stakedBal > 0) {
                IGauge(gauge).withdraw(
                    Math.min(_stakedBal, _amountNeeded - _wantBal)
                );
            }
            uint256 _withdrawnBal = balanceOfWant();
            _liquidatedAmount = Math.min(_amountNeeded, _withdrawnBal);
            unchecked {
                _loss = _amountNeeded - _liquidatedAmount;
            }
        } else {
            // we have enough balance to cover the liquidation available
            return (_amountNeeded, 0);
        }
    }

    // fire sale, get rid of it all!
    function liquidateAllPositions() internal override returns (uint256) {
        uint256 _stakedBal = stakedBalance();
        if (_stakedBal > 0) {
            // don't bother withdrawing zero
            IGauge(gauge).withdraw(_stakedBal);
        }
        return balanceOfWant();
    }

    function protectedTokens()
        internal
        view
        override
        returns (address[] memory)
    {}
}

contract StrategyVeloVeloVolatileClonable is StrategyVeloBase {
    using SafeERC20 for IERC20;
    /* ========== STATE VARIABLES ========== */
    // these will likely change across different wants.

    address public other; // address of the other (non-velo) token in the volatile pool

    uint256 public maxSlippageVeloOther;

    // check for cloning
    bool internal isOriginal = true;

    /* ========== CONSTRUCTOR ========== */

    constructor(
        address _vault,
        address _gauge,
        address _veloPool,
        address _otherToken,
        address _healthCheck,
        string memory _name
    ) StrategyVeloBase(_vault) {
        _initializeStrat(_gauge, _veloPool, _otherToken, _healthCheck, _name);
    }

    /* ========== CLONING ========== */

    event Cloned(address indexed clone);

    // we use this to clone our original strategy to other vaults
    function cloneVeloVeloVolatile(
        address _vault,
        address _strategist,
        address _rewards,
        address _keeper,
        address _gauge,
        address _veloPool,
        address _otherToken,
        address _healthCheck,
        string memory _name
    ) external returns (address newStrategy) {
        // don't clone a clone
        if (!isOriginal) {
            revert();
        }

        // Copied from https://github.com/optionality/clone-factory/blob/master/contracts/CloneFactory.sol
        bytes20 addressBytes = bytes20(address(this));
        assembly {
            // EIP-1167 bytecode
            let clone_code := mload(0x40)
            mstore(
                clone_code,
                0x3d602d80600a3d3981f3363d3d373d3d3d363d73000000000000000000000000
            )
            mstore(add(clone_code, 0x14), addressBytes)
            mstore(
                add(clone_code, 0x28),
                0x5af43d82803e903d91602b57fd5bf30000000000000000000000000000000000
            )
            newStrategy := create(0, clone_code, 0x37)
        }

        StrategyVeloVeloVolatileClonable(newStrategy).initialize(
            _vault,
            _strategist,
            _rewards,
            _keeper,
            _gauge,
            _veloPool,
            _otherToken,
            _healthCheck,
            _name
        );

        emit Cloned(newStrategy);
    }

    // this will only be called by the clone function above
    function initialize(
        address _vault,
        address _strategist,
        address _rewards,
        address _keeper,
        address _gauge,
        address _veloPool,
        address _otherToken,
        address _healthCheck,
        string memory _name
    ) public {
        _initialize(_vault, _strategist, _rewards, _keeper);
        _initializeStrat(_gauge, _veloPool, _otherToken, _healthCheck, _name);
    }

    // this is called by our original strategy, as well as any clones
    function _initializeStrat(
        address _gauge,
        address _veloPool,
        address _otherToken,
        address _healthCheck,
        string memory _name
    ) internal {
        // make sure that we haven't initialized this before
        require(address(pool) == address(0)); // already initialized
        require(IGauge(_gauge).stake() == _veloPool); // incorrect gauge

        // You can set these parameters on deployment to whatever you want
        maxReportDelay = 28 days; // 28 days in seconds
        minReportDelay = 7 days; // 7 days in seconds
        creditThreshold = 10000 * 1e18;
        maxSlippageVeloOther = 50; // 0.5% default

        // set state vars 1:1
        gauge = _gauge;
        pool = _veloPool;
        healthCheck = _healthCheck;

        // set the other (non-USDC) token in our pool
        other = _otherToken;

        // set our strategy's name
        stratName = _name;

        // these are our standard approvals. want = Velodrome pool token
        want.approve(gauge, type(uint256).max);

        // these are our approvals and path specific to this contract
        velo.approve(velodromeRouter, type(uint256).max);
        IERC20(other).approve(velodromeRouter, type(uint256).max);

        rewardsTokens.push(address(velo));
    }

    /* ========== MUTATIVE FUNCTIONS ========== */

    function prepareReturn(uint256 _debtOutstanding)
        internal
        override
        returns (
            uint256 _profit,
            uint256 _loss,
            uint256 _debtPayment
        )
    {
        // claim our velo
        IGauge(gauge).getReward(address(this), rewardsTokens);
        uint256 _veloBalance = velo.balanceOf(address(this));

        // deposit our VELO balance to Velodrome, if we have at least 1
        if (_veloBalance > 1e18) {
            uint256 _otherBalance = IERC20(other).balanceOf(address(this));
            uint256 _veloB = velo.balanceOf(pool);
            uint256 _otherB = IERC20(other).balanceOf(pool);

            // determine how much velo to sell for other for balanced add liquidity
            uint256 _veloToSell = _veloBalance / 2;

            // swap velo for other
            _sellvelo(_veloToSell);

            _veloBalance = velo.balanceOf(address(this));
            _otherBalance = IERC20(other).balanceOf(address(this));

            if (_otherBalance > 0 && _veloBalance > 0) {
                uint256 _velo98 = (_veloBalance * 98) / 100;
                uint256 _other98 = (_otherBalance * 98) / 100;
                // deposit into lp
                IVelodromeRouter(velodromeRouter).addLiquidity(
                    address(velo), // tokenA
                    address(other), // tokenB
                    false, // stable
                    _veloBalance, // amountADesired
                    _otherBalance, // amountBDesired
                    _velo98, // amountAMin
                    _other98, // amountBMin
                    address(this), // to
                    block.timestamp // deadline
                );
            }
        }

        // debtOustanding will only be > 0 in the event of revoking or if we need to rebalance from a withdrawal or lowering the debtRatio
        if (_debtOutstanding > 0) {
            uint256 _stakedBal = stakedBalance();
            // don't bother withdrawing if we don't have staked funds
            if (_stakedBal > 0) {
                IGauge(gauge).withdraw(Math.min(_stakedBal, _debtOutstanding));
            }
            uint256 _withdrawnBal = balanceOfWant();
            _debtPayment = Math.min(_debtOutstanding, _withdrawnBal);
        }

        // serious loss should never happen, but if it does (for instance, if Velodrome is hacked), let's record it accurately
        uint256 assets = estimatedTotalAssets();
        uint256 debt = vault.strategies(address(this)).totalDebt;

        // if assets are greater than debt, things are working great!
        if (assets > debt) {
            unchecked {
                _profit = assets - debt;
            }
            uint256 _wantBal = balanceOfWant();
            if (_profit + _debtPayment > _wantBal) {
                // this should only be hit following donations to strategy
                liquidateAllPositions();
            }
        }
        // if assets are less than debt, we are in trouble
        else {
            unchecked {
                _loss = debt - assets;
            }
        }
    }

    function prepareMigration(address _newStrategy) internal override {
        uint256 _stakedBal = stakedBalance();
        if (_stakedBal > 0) {
            IGauge(gauge).withdraw(_stakedBal);
        }
        velo.safeTransfer(_newStrategy, velo.balanceOf(address(this)));
    }

    // sells VELO for OTHER
    function _sellvelo(uint256 _veloAmount) internal {
        (uint256 _expectedOut, ) =
            IVelodromeRouter(velodromeRouter).getAmountOut(
                _veloAmount, // amountIn
                address(velo), // tokenIn
                address(other) // tokenOut
            );
        uint256 _amountOutMin =
            (_expectedOut * (10_000 - maxSlippageVeloOther)) / 10_000;

        IVelodromeRouter(velodromeRouter).swapExactTokensForTokensSimple(
            _veloAmount, // amountIn
            _amountOutMin, // amountOutMin
            address(velo), // tokenFrom
            address(other), // tokenTo
            false, // stable
            address(this), // to
            block.timestamp // deadline
        );
    }

    // Use to add or update rewards
    // VELO plus any others that may have been added to the gauge
    function updateRewardsTokens(address[] memory _rewards)
        external
        onlyVaultManagers
    {
        rewardsTokens = _rewards;
    }

    /* ========== KEEP3RS ========== */
    // use this to determine when to harvest
    function harvestTrigger(uint256 callCostinEth)
        public
        view
        override
        returns (bool)
    {
        // should not trigger if strategy is not active (no assets and no debtRatio). This means we don't need to adjust keeper job.
        if (!isActive()) {
            return false;
        }

        StrategyParams memory params = vault.strategies(address(this));
        // harvest no matter what once we reach our maxDelay
        if (block.timestamp - params.lastReport > maxReportDelay) {
            return true;
        }

        // check if the base fee gas price is higher than we allow. if it is, block harvests.
        if (!isBaseFeeAcceptable()) {
            return false;
        }

        // trigger if we want to manually harvest, but only if our gas price is acceptable
        if (forceHarvestTriggerOnce) {
            return true;
        }

        // harvest if we hit our minDelay, but only if our gas price is acceptable
        if (block.timestamp - params.lastReport > minReportDelay) {
            return true;
        }

        // harvest our credit if it's above our threshold
        if (vault.creditAvailable() > creditThreshold) {
            return true;
        }

        // otherwise, we don't harvest
        return false;
    }

    function setMaxSlippage(uint256 _maxSlippageVeloOther)
        external
        onlyVaultManagers
    {
        require(_maxSlippageVeloOther <= 10_000, "SLIPPAGE_LIMIT_EXCEEDED");
        maxSlippageVeloOther = _maxSlippageVeloOther;
    }

    // convert our keeper's eth cost into want, we don't need this anymore since we don't use baseStrategy harvestTrigger
    function ethToWant(uint256 _ethAmount)
        public
        view
        override
        returns (uint256)
    {}
}
