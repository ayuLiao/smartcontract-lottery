"""
单元测试 - 在本地测试网络对每个方法都进行测试
"""

from web3 import Web3
from brownie import accounts, network, config, Lottery, exceptions
from scripts.utils import *
from scripts.deploy_lottery import deploy_lottery
import pytest


def test_get_entrance_fee():
    """
    测试EHT与USD的汇率是否正常
    :return:
    """
    # 不是本地网络，则跳过test，比如使用了Rinkeby测试网络，则skip test
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()
        # Arrange
    lottery = deploy_lottery()
    # Act
    # 2,000 eth / usd
    # usdEntryFee is 50
    # 2000/1 == 50/x == 0.025
    expected_entrance_fee = Web3.toWei(0.025, "ether")
    entrance_fee = lottery.getEntranceFee()
    # Assert
    assert expected_entrance_fee == entrance_fee


def test_cant_enter_unless_started():
    """
    测试抽奖活动未开始时，是否可以参加（即充钱进去）
    :return:
    """
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()
    lottery = deploy_lottery()
    # Act / Assert
    with pytest.raises(exceptions.VirtualMachineError):
        lottery.enter({"from": get_account(), "value": lottery.getEntranceFee() + 100000000})


def test_can_start_and_enter_lottery():
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()
    lottery = deploy_lottery()
    account = get_account()
    lottery.startLottery({"from": account})
    # Act
    lottery.enter({"from": account, "value": lottery.getEntranceFee()})
    # Assert
    assert lottery.players(0) == account


def test_can_end_lottery():
    """
    判断结束抽奖时，抽奖合约的状态是否为2，即有人胜出了
    :return:
    """
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()
    lottery = deploy_lottery()
    account = get_account()
    lottery.startLottery({"from": account})
    lottery.enter({"from": account, "value": lottery.getEntranceFee()})
    fund_with_link(lottery)
    lottery.endLottery({"from": account})
    assert lottery.lottery_state() == 2


def test_can_pick_winner_correctly():
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()
    lottery = deploy_lottery()
    account = get_account()
    # 开始抽奖游戏
    lottery.startLottery({"from": account})
    # 3个玩家分别花费50 usd参与抽奖游戏
    lottery.enter({"from": account, "value": lottery.getEntranceFee()})
    lottery.enter({"from": get_account(index=1), "value": lottery.getEntranceFee()})
    lottery.enter({"from": get_account(index=2), "value": lottery.getEntranceFee()})
    # 想合约充LINK代币
    fund_with_link(lottery)
    # 账号中拥有的代币
    starting_balance_of_account = account.balance()
    # 抽奖合约中拥有的代码（相当于奖池里的钱）
    balance_of_lottery = lottery.balance()
    transaction = lottery.endLottery({"from": account})
    # 获取事件日志中存放的requestId，通过该requestId去触发Mock的vrf_coordinator合约中的callBackWithRandomness方法
    # 通过这种方式，模拟真实的回调
    request_id = transaction.events["RequestedRandomness"]["requestId"]
    STATIC_RNG = 3
    # 使用Mock的合约，假装成vrf_coordinator，完成回调，获得随机数，从而获得胜利者
    get_contract("vrf_coordinator").callBackWithRandomness(request_id, STATIC_RNG, lottery.address, {"from": account})
    # 3 % 3 = 0，按合约的规则，会取第一个用户
    assert lottery.recentWinner() == account  # 胜利者是第一个账号
    assert lottery.balance() == 0  # lottery合约里的钱都转给胜利者了，所以合约里应该没钱了
    assert account.balance() == starting_balance_of_account + balance_of_lottery  # 胜利者用户账号的钱 = 用户已有的钱 + 合约里的钱

