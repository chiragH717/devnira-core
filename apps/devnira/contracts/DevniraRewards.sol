// SPDX-License-Identifier: MIT
pragma solidity ^0.8.30;
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable2Step.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/// @notice Separate app token. Virtual equipment is not chain PoW.
/// @dev An operator chooses reward recipients off-chain. This contract only
/// enforces issuance, sequence and timing, not fair winner selection.
contract DevniraRewards is ERC20, Ownable2Step {
    uint256 public constant MAX_SUPPLY = 2_000_000_000 * 10**8;
    uint256 public constant INITIAL_REWARD = 2_400 * 10**8;
    uint256 public constant ROUND_SECONDS = 120;
    uint256 public round;
    uint256 public lastRoundAt;
    address public operator;
    bool public rewardsPaused = true;
    event RewardRound(uint256 indexed round, address indexed recipient,
        bytes32 indexed publicHandleHash, uint256 amount, bytes32 allocationDigest);
    event OperatorChanged(address indexed operator);
    event RewardsPaused(bool paused);
    constructor(address initialOwner) ERC20("Devnira App", "DVN") Ownable(initialOwner) {
        lastRoundAt = block.timestamp;
    }
    function decimals() public pure override returns(uint8) { return 8; }
    function setOperator(address value) external onlyOwner {
        require(value != address(0), "zero operator");
        operator=value; emit OperatorChanged(value);
    }
    function setRewardsPaused(bool paused) external onlyOwner {
        rewardsPaused=paused; emit RewardsPaused(paused);
    }
    function issuedAt(uint256 n) public pure returns(uint256) {
        // Bounded input avoids overflow even if called with arbitrary public data.
        require(n <= type(uint64).max, "round out of range");
        return MAX_SUPPLY*n*INITIAL_REWARD/(MAX_SUPPLY-INITIAL_REWARD+n*INITIAL_REWARD);
    }
    function rewardAt(uint256 n) public pure returns(uint256) {
        require(n>0, "round zero");
        return issuedAt(n)-issuedAt(n-1);
    }
    function settleRound(uint256 expectedRound, address recipient, bytes32 handleHash,
        bytes32 allocationDigest) external {
        require(msg.sender==operator,"operator only");
        require(!rewardsPaused,"rewards paused");
        require(expectedRound==round+1,"wrong round");
        require(block.timestamp>=lastRoundAt+ROUND_SECONDS,"round too early");
        require(recipient!=address(0)&&handleHash!=bytes32(0)&&allocationDigest!=bytes32(0),"invalid allocation");
        uint256 amount=rewardAt(expectedRound);
        require(amount>0&&totalSupply()+amount<=MAX_SUPPLY,"supply limit");
        round=expectedRound;lastRoundAt=block.timestamp;
        _mint(recipient,amount);
        emit RewardRound(expectedRound,recipient,handleHash,amount,allocationDigest);
    }
}
