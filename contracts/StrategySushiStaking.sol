// SPDX-License-Identifier: AGPL-3.0
// Feel free to change the license, but this is what we use

// Feel free to change this version of Solidity. We support >=0.6.0 <0.7.0;
pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

// These are the core Yearn libraries
import {
    BaseStrategy,
    StrategyParams
} from "@yearnvaults/contracts/BaseStrategy.sol";
import {
    SafeERC20,
    SafeMath,
    IERC20,
    Address
} from "@openzeppelin/contracts/token/ERC20/SafeERC20.sol";
import "@openzeppelin/contracts/math/Math.sol";

interface IUniswapV2Router02 {
    function swapExactTokensForTokens(
        uint256 amountIn,
        uint256 amountOutMin,
        address[] calldata path,
        address to,
        uint256 deadline
    ) external returns (uint256[] memory amounts);

    function getAmountsOut(uint256 amountIn, address[] calldata path)
        external
        view
        returns (uint256[] memory amounts);
}

interface ISushiBar {
    function leave(uint256 _share) external; // this is withdrawing
    
    function enter(uint256 _amount) external; // this is depositing
        
}

contract StrategySushiStaking is BaseStrategy {
    using SafeERC20 for IERC20;
    using Address for address;
    using SafeMath for uint256;

    /* ========== STATE VARIABLES ========== */

    address public constant xsushi = 0x8798249c2E607446EfB7Ad49eC89dD1865Ff4272;
    IERC20 public constant sushi =
        IERC20(0x6B3595068778DD592e39A122f4f5a5cF09C90fE2);    
    uint256 sushiDeposited;

    /* ========== CONSTRUCTOR ========== */

    constructor(address _vault, address _farmingContract)
        public
        BaseStrategy(_vault)
    {
        // initialize variables
        minReportDelay = 0;
        maxReportDelay = 604800; // 7 days in seconds, if we hit this then harvestTrigger = True
        profitFactor = 400;
        debtThreshold = 4000 * 1e18; // we shouldn't ever have debt, but set a bit of a buffer
        healthCheck = address(0xDDCea799fF1699e98EDF118e0629A974Df7DF012); // health.ychad.eth

        // want is SUSHI
        want.safeApprove(address(xsushi), type(uint256).max);
    }


    /* ========== VIEWS ========== */

    function name() external view override returns (string memory) {
        return "StrategyUniverseStaking";
    }
    
    function _xsushiSharePrice() internal view returns (uint256) {
        return sushi.balanceOf(address(xsushi)).div(IERC20(xsushi).totalSupply());
    }
    
    function _balanceOfStaked() internal view returns (uint256) {
        return IERC20(xsushi).balanceOf(address(this)).mul(_xsushiSharePrice());
    }
    
    function _balanceOfWant() internal view returns (uint256) {
        return want.balanceOf(address(this));
    }
    
    function _xsushiBalance() internal view returns (uint256) {
        return IERC20(xsushi).balanceOf(address(this));
    }
    
    function estimatedTotalAssets() public view override returns (uint256) {
        // look at our staked tokens and any free tokens sitting in the strategy
        return _balanceOfStaked().add(_balanceOfWant());
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
        // withdraw from our xsushi to prove how much we've earned
        ISushiBar(xsushi).leave(_xsushiBalance());
        
        // serious loss should never happen, but if it does (for instance, if Curve is hacked), let's record it accurately
        uint256 assets = estimatedTotalAssets();
        uint256 debt = vault.strategies(address(this)).totalDebt;

        // if assets are greater than debt, things are working great! loss will be 0 by default
        if (assets > debt) {
            _profit = _balanceOfWant();
        } else {
            // if assets are less than debt, we are in trouble. profit will be 0 by default
            _loss = debt.sub(assets);
        }

        // debtOustanding will only be > 0 in the event of revoking or lowering debtRatio of a strategy
        if (_debtOutstanding > 0) {
             ISushiBar(xsushi).leave(
                Math.min(_xsushiBalance(), _debtOutstanding.div(_xsushiSharePrice()))
             );

            _debtPayment = Math.min(_debtOutstanding, _balanceOfWant());
            if (_debtPayment < _debtOutstanding) {
                _loss = _loss.add(_debtOutstanding.sub(_debtPayment));
                _profit = 0;
            }
        }
    }

    function adjustPosition(uint256 _debtOutstanding) internal override {
        if (emergencyExit) {
            return;
        }
        // send all of our want tokens to be deposited
        uint256 _toInvest = _balanceOfWant();
        // stake only if we have something to stake
        if (_toInvest > 0) {
            ISushiBar(xsushi).enter(_toInvest);
        }
    }

    function liquidatePosition(uint256 _amountNeeded)
        internal
        override
        returns (uint256 _liquidatedAmount, uint256 _loss)
    {
        uint256 wantBal = _balanceOfWant();
        if (_amountNeeded > wantBal) {
            ISushiBar(xsushi).leave(
                address(want),
                Math.min(_xsushiBalance(), (_amountNeeded - wantBal).div(_xsushiSharePrice()))
            );

            uint256 withdrawnBal = _balanceOfWant();
            _liquidatedAmount = Math.min(_amountNeeded, withdrawnBal);
            _loss = _amountNeeded.sub(_liquidatedAmount);
        } else {
            // we have enough balance to cover the liquidation available
            return (_amountNeeded, 0);
        }
    }

    function liquidateAllPositions() internal override returns (uint256) {
        if (_balanceOfStaked() > 0) {
            ISushiBar(xsushi).leave(_xsushiBalance());
        }
        return _balanceOfWant();
    }

    function prepareMigration(address _newStrategy) internal override {
        if (_balanceOfStaked() > 0) {
            ISushiBar(xsushi).leave(_xsushiBalance());
        }
    }

    function protectedTokens()
        internal
        view
        override
        returns (address[] memory)
    {
        address[] memory protected = new address[](1);
        protected[0] = address(xsushi);

        return protected;
    }

    // our main trigger is regarding our DCA since there is low liquidity for $XYZ
    function harvestTrigger(uint256 callCostinEth)
        public
        view
        override
        returns (bool)
    {
        StrategyParams memory params = vault.strategies(address(this));

        // Should not trigger if Strategy is not activated
        if (params.activation == 0) return false;

        // Should not trigger if we haven't waited long enough since previous harvest
        if (block.timestamp.sub(params.lastReport) < minReportDelay)
            return false;

        // Should trigger if hasn't been called in a while
        if (block.timestamp.sub(params.lastReport) >= maxReportDelay)
            return true;

        // If some amount is owed, pay it back
        // NOTE: Since debt is based on deposits, it makes sense to guard against large
        //       changes to the value from triggering a harvest directly through user
        //       behavior. This should ensure reasonable resistance to manipulation
        //       from user-initiated withdrawals as the outstanding debt fluctuates.
        uint256 outstanding = vault.debtOutstanding();
        if (outstanding > debtThreshold) return true;

        // Check for profits and losses
        uint256 total = estimatedTotalAssets();
        // Trigger if we have a loss to report
        if (total.add(debtThreshold) < params.totalDebt) return true;

        // Trigger if we haven't harvested in the last week
        uint256 week = 86400 * 7;
        if (block.timestamp.sub(params.lastReport) > week {
            return true;
        }
    }

    function ethToWant(uint256 _amtInWei)
        public
        view
        override
        returns (uint256)
    {
        address[] memory ethPath = new address[](2);
        ethPath[0] = address(weth);
        ethPath[1] = address(want);

        uint256[] memory callCostInWant =
            IUniswapV2Router02(sushiswapRouter).getAmountsOut(
                _amtInWei,
                ethPath
            );

        uint256 _ethToWant = callCostInWant[callCostInWant.length - 1];

        return _ethToWant;
    }

}
