"""
集成测试 - 在Rinkeby测试网络中，过一遍业务流程
"""
import time
import pytest
from brownie import network
from scripts.utils import *
from scripts.deploy_lottery import deploy_lottery


def test_can_pick_winner():
    """
    在rinkeby网络上，运行该测试方法
    brownie test -k test_can_pick_winner --network rinkeby

    :return:
    """
    if network.show_active() in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        # 如果是本地网络，跳过测试
        pytest.skip()
    lottery = deploy_lottery()
    account = get_account()
    # 测试网络（属于线上网络），此时我们只有account一个账号，所以我们使用单个账号来模拟多个玩家参与游戏的过程
    lottery.startLottery({"from": account})
    lottery.enter({"from": account, "value": lottery.getEntranceFee()})
    lottery.enter({"from": account, "value": lottery.getEntranceFee()})
    fund_with_link(lottery)
    lottery.endLottery({"from": account})
    # 国内环境，等待实际久一点
    time.sleep(120)
    assert lottery.recentWinner() == account
    assert lottery.balance() == 0
