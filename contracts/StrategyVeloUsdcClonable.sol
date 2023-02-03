// SPDX-License-Identifier: AGPL-3.0
pragma solidity ^0.8.15;
pragma experimental ABIEncoderV2;

// These are the core Yearn libraries
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/utils/math/Math.sol";

import "./interfaces/yearn.sol";
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
    ) external returns (uint256 amountA, uint256 amountB, uint256 liquidity);

    function swapExactTokensForTokensSimple(
        uint amountIn,
        uint amountOutMin,
        address tokenFrom,
        address tokenTo,
        bool stable,
        address to,
        uint deadline
    ) external returns (uint[] memory amounts);
}

interface IGauge {
    function deposit(
        uint amount,
        uint tokenId
    ) external;

    function balanceOf(
        address 
    ) external view returns (uint256);

    function withdraw(
        uint amount
    ) external;

    function derivedBalance(
        address account
    ) external view returns (uint);

    function getReward(
        address account,
        address[] memory tokens
    ) external;

    function stake(
    ) external view returns (address);
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

    address[] public onlyVelo;

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
                IGauge(gauge).withdraw(Math.min(_stakedBal, _amountNeeded - _wantBal));
            }
            uint256 _withdrawnBal = balanceOfWant();
            _liquidatedAmount = Math.min(_amountNeeded, _withdrawnBal);
            _loss = _amountNeeded - _liquidatedAmount;
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

contract StrategyVeloUsdcClonable is StrategyVeloBase {
    using SafeERC20 for IERC20;
    /* ========== STATE VARIABLES ========== */
    // these will likely change across different wants.

    address public other; // address of the other (non-usdc) token in the stable pool
    
    IVelodromeRouter internal constant velousdc =
        IVelodromeRouter(0x8301AE4fc9c624d1D396cbDAa1ed877821D7C511); // velodrome pool to sell our velo for usdc

    // we use these to deposit to our velodrome pool
    IERC20 internal constant usdc =
        IERC20(0x7F5c764cBc14f9669B88837ca1490cCa17c31607);

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
    function cloneVeloUsdc(
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

        StrategyVeloUsdcClonable(newStrategy).initialize(
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
        creditThreshold = 0.005 * 1e18; // $10,000 because gas is cheap

        // set our velodrome gauge contract
        gauge = address(_gauge);
        
        // this is the pool specific to this vault, but we only use it as an address
        pool = address(_veloPool);

        // set the other (non-USDC) token in our pool
        other = address(_otherToken);

        healthCheck = address(_healthCheck);

        // set our strategy's name
        stratName = _name;

        // these are our standard approvals. want = Velodrome pool token
        want.approve(address(gauge), type(uint256).max);
        velo.approve(address(velousdc), type(uint256).max);

        // these are our approvals and path specific to this contract
        usdc.approve(address(velodromeRouter), type(uint256).max);
        velo.approve(address(velodromeRouter), type(uint256).max);
        IERC20(other).approve(address(velodromeRouter), type(uint256).max);

        onlyVelo.push(address(velo));
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
        uint256 _stakedBal = stakedBalance();
        uint256 _veloBalance = velo.balanceOf(address(this));
        // if we have anything in the gauge, then harvest VELO from the gauge
        if (_stakedBal > 0) {
            // claim our velo
            IGauge(gauge).getReward(address(this), onlyVelo);
            _veloBalance = velo.balanceOf(address(this));
        }
        // if we have any VELO, then sell it for USDC
        if (_veloBalance > 0) {
            _sell(_veloBalance);
        }        

        // check for balances of tokens to deposit
        uint256 _usdcBalance = usdc.balanceOf(address(this));

        // deposit our USDC balance to Velodrome, if we have any
        if (_usdcBalance > 0) {
            uint256 _otherBalance = IERC20(other).balanceOf(address(this));
            uint256 _usdcB = usdc.balanceOf(pool);
            uint256 _otherB = IERC20(other).balanceOf(pool);
            
            // usdc has 6 decimals so we will need to scale decimals
            address _usdc_addr = address(usdc);
            uint256 _otherBScaled = _scaleDecimals(_otherB, ERC20(_usdc_addr), ERC20(other));

            // determine how much usdc to sell for other for balanced add liquidity
            uint256 _usdcToSell = _usdcBalance * _otherBScaled / (_usdcB + _otherBScaled);

            if (_usdcToSell > 10e6) {
                // swap usdc for other
                _sellusdc(_usdcToSell);
            }

            _usdcBalance = usdc.balanceOf(address(this));
            _otherBalance = IERC20(other).balanceOf(address(this));
           
            if (_otherBalance > 0 && _usdcBalance > 0) {
                uint256 _usdc98 = _usdcBalance * 98 / 100;
                uint256 _other98 = _otherBalance * 98 / 100;
                // deposit into lp
                IVelodromeRouter(velodromeRouter).addLiquidity(
                    address(usdc), // tokenA
                    address(other), // tokenB
                    true, // stable
                    _usdcBalance, // amountADesired
                    _otherBalance, // amountBDesired
                    _usdc98, // amountAMin
                    _other98, // amountBMin
                    address(this), // to
                    block.timestamp // deadline
                );
            }
        }

        // debtOustanding will only be > 0 in the event of revoking or if we need to rebalance from a withdrawal or lowering the debtRatio
        if (_debtOutstanding > 0) {
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
            _profit = assets - debt;
            uint256 _wantBal = balanceOfWant();
            if (_profit + _debtPayment > _wantBal) {
                // this should only be hit following donations to strategy
                liquidateAllPositions();
            }
        }
        // if assets are less than debt, we are in trouble
        else {
            _loss = debt - assets;
        }
    }

    function prepareMigration(address _newStrategy) internal override {
        uint256 _stakedBal = stakedBalance();
        if (_stakedBal > 0) {
            IGauge(gauge).withdraw(_stakedBal);
        }
        velo.safeTransfer(_newStrategy, velo.balanceOf(address(this)));
    }

    // Sells VELO for USDC
    function _sell(uint256 _veloAmount) internal {      
        IVelodromeRouter(velodromeRouter).swapExactTokensForTokensSimple(
            _veloAmount, // amountIn
            0, // amountOutMin
            address(velo), // tokenFrom
            address(usdc), // tokenTo
            false, // stable
            address(this), // to
            block.timestamp // deadline
        );
    }

    // Sells USDC for OTHER
    function _sellusdc(uint256 _usdcAmount) internal {      
        IVelodromeRouter(velodromeRouter).swapExactTokensForTokensSimple(
            _usdcAmount, // amountIn
            0, // amountOutMin
            address(usdc), // tokenFrom
            address(other), // tokenTo
            true, // stable
            address(this), // to
            block.timestamp // deadline
        );
    }


    function _scaleDecimals(uint256 _amount, ERC20 _fromToken, ERC20 _toToken) internal view returns (uint256 _scaled){
        uint256 decFrom = _fromToken.decimals();
        uint256 decTo = _toToken.decimals();
        return decTo > decFrom ? _amount / 10 ** (decTo - decFrom) : _amount * 10 ** (decFrom - decTo);
}

    /* ========== KEEP3RS ========== */
    // use this to determine when to harvest
    function harvestTrigger(uint256 callCostinEth)
        public
        view
        override
        returns (bool)
    {
        // Should not trigger if strategy is not active (no assets and no debtRatio). This means we don't need to adjust keeper job.
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

    // convert our keeper's eth cost into want, we don't need this anymore since we don't use baseStrategy harvestTrigger
    function ethToWant(uint256 _ethAmount)
        public
        view
        override
        returns (uint256)
    {}
}