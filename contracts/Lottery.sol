// SPDX-License-Identifier: MIT
pragma solidity ^0.6.6;

import "@chainlink/contracts/src/v0.6/interfaces/AggregatorV3Interface.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@chainlink/contracts/src/v0.6/VRFConsumerBase.sol";

// is：继承另一个合约，可以访问父合约中所有的非私有成员
// https://learnblockchain.cn/docs/solidity/contracts.html#index-15
contract Lottery is VRFConsumerBase, Ownable {
    // 地址需要接受以太币，则使用address payable，不需要则使用address，如果想address实例化的地址中转以太币，会报编译错误
    // http://blog.hubwiz.com/2019/05/18/solidity-address-payable/
    address payable[] public players;
    address payable public recentWinner;
    uint256 public usdEntryFee;
    AggregatorV3Interface internal ethUsdPriceFeed;

    // 枚举 - 易于阅读，其中OPEN等价于0，CLOSE等价于1，以此类推
    enum LOTTERY_STATE {
        OPEN,
        CLOSE,
        CALCULATING_WINNER
    }
    LOTTERY_STATE public lottery_state;
    uint256 fee; // 调用时需要的费用
    bytes32 keyhash; // 用户确认VRF Coordinator唯一身份
    uint256 randomness;
    // 事件 - 将数据记录到事件日志的
    // https://learnblockchain.cn/2018/05/09/solidity-event/
    event RequestedRandomness(bytes32 requestId);

    // 当前合约的constructor
    constructor(
        address _priceFeedAddress,
        address _vrfCoordinator,
        address _link,
        uint256 _fee,
        bytes32 _keyhash
    ) public
    // 当前合约继承了 VRFConsumerBase 合约，该合约也有constructor，当前合约public后可以跟随任意继承合约的constructor
    VRFConsumerBase(_vrfCoordinator, _link){
        // 参与彩票的报名费：50 usd
        usdEntryFee = 50 * (10 ** 18);
        lottery_state = LOTTERY_STATE.CLOSE;
        // USD 与 ETH 比率预言机
        ethUsdPriceFeed = AggregatorV3Interface(_priceFeedAddress);
        fee = _fee;
        keyhash = _keyhash;
    }
    // function中有payable修饰符，可以让合约收到ETH
    function enter() public payable {
        // msg.value：方法调用者的value是否大于
        require(msg.value >= getEntranceFee());
        require(lottery_state == LOTTERY_STATE.OPEN);
        players.push(msg.sender);
    }

    function getEntranceFee() public view returns (uint256) {
        // 获得 1ETH 对应的美元（price）
        (, int256 price, , ,) = ethUsdPriceFeed.latestRoundData();
        // int256强转成uint256
        uint256 adjustedPrice = uint256(price) * 10 ** 10;
        // 18位小数
        // 50美元与1ETH的比值 => 50美元是多少ETH
        uint256 costToEnter = (usdEntryFee * 10 ** 18) / adjustedPrice;
        return costToEnter;
    }

    // 使用了onlyOwner修饰符
    // onlyOwner来自外部合约，其作用是让startLottery方法只能被合约创建人调用
    function startLottery() public onlyOwner {
        require(
            // 枚举值，默认是OPEN
            // 这里判断，如果抽奖合约状态不为CLOSE，则不允许再次开启
            lottery_state == LOTTERY_STATE.CLOSE,
            "Can't start a new lottery yet!"
        );
        lottery_state = LOTTERY_STATE.OPEN;
    }


    function endLottery() public onlyOwner {
        lottery_state = LOTTERY_STATE.CALCULATING_WINNER;
        // 请求外部合约，外部合约会通过预言机生成一个可验证的随机值（VRF），但这次请求，只会返回一个requestId，
        // VRF Coordinator会主动回调合约里的方法
        // 这个过程，类似于，我们的合约发送request，然后等待对方callback回对应的函数
        // 调用requestRandomness函数时，传入keyhash用于验证身份，传入fee支付调用外部合约需要支付的金额
        // fee是当前合约调用其他合约时，需要支付的金额，一开始，当前合约是没有LINK代币的，此时需要我们从自己的账户中转入相应的LINK到当前合约中
        bytes32 requestId = requestRandomness(keyhash, fee);
        // 触发RandomnessRequest事件，将requestId传入
        emit RequestedRandomness(requestId);
    }

    // fulfillRandomness函数名称是固定的，因为外部合约callback时，会通过该名称调用相应的方法
    // 为了避免任何人调用该方法，通过internal关键字将方法设置为内部方法，因为我们import了VRFConsumerBase，所以回调时，该方法可以掉用成功
    // override关键字是覆盖同名方法，即将VRFConsumerBase中的同名方法覆盖了，重新再实现
    function fulfillRandomness(bytes32 _requestId, uint256 _randomness) internal override {
        require(lottery_state == LOTTERY_STATE.CALCULATING_WINNER, "You aren't there yet!");
        require(_randomness > 0, "random-not-found");
        // _randomness 随机值
        // players.length 玩家个数
        // 通过取模的方式，从参与抽奖的玩家中，随机选择一个玩家作为胜利者
        uint256 indexOfWinner = _randomness % players.length;
        recentWinner = players[indexOfWinner];
        // 胜利者获得当前合约地址中，所有的金额
        recentWinner.transfer(address(this).balance);
        // 清理数据 - 重启抽奖
        players = new address payable[](0);
        lottery_state = LOTTERY_STATE.CLOSE;
        // 记录这一次的随机值
        randomness = _randomness;
    }
}
