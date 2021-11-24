from scripts.utils import get_account, get_contract, fund_with_link
from brownie import network, config, Lottery
import time

# https://eth-brownie.readthedocs.io/en/stable/api-network.html?highlight=wait#TransactionReceipt.wait
# 将等待交易的 n 个确认。 如果 n 小于当前的确认数量，则这不起作用。
with_confirmation = 1

def deploy_lottery():
    account = get_account()
    # Lottery合约构造函数需要的参数
    lottery = Lottery.deploy(
        get_contract("eth_usd_price_feed").address,
        get_contract("vrf_coordinator").address,
        get_contract("link_token").address,
        config["networks"][network.show_active()]["fee"],
        config["networks"][network.show_active()]["keyhash"],
        {"from": account},
        publish_source=config["networks"][network.show_active()].get("verify", False),
    )
    print("Deployed lottery!")
    return lottery


def start_lottery():
    account = get_account()
    lottery = Lottery[-1]
    starting_tx = lottery.startLottery({"from": account})
    # wait(n):等待交易的n个
    starting_tx.wait(with_confirmation)
    print("The lottery is started")


def enter_lottery():
    account = get_account()
    lottery = Lottery[-1]
    value = lottery.getEntranceFee() + 100000000
    tx = lottery.enter({"from": account, "value": value})
    tx.wait(with_confirmation)
    print("You entered the lottery!")


def end_lottery():
    account = get_account()
    lottery = Lottery[-1]
    # 将账号中的LINK代币转到合约中
    tx = fund_with_link(lottery.address)
    tx.wait(with_confirmation)
    ending_transaction = lottery.endLottery({"from": account})
    ending_transaction.wait(with_confirmation)
    # 获取随机数，等待VRF Coordinator回调，从文档可知，回调会在第二次出块时带上相应的随机值
    time.sleep(60)
    winner = lottery.recentWinner()
    print(f"{winner} is the new winner!")


def main():
    deploy_lottery()
    start_lottery()
    enter_lottery()
    end_lottery()
