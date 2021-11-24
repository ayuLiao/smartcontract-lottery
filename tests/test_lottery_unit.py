from web3 import Web3
from brownie import accounts, network, config, Lottery


def test_get_entrance_fee():
    account = accounts[0]
    lottery = Lottery.deploy(
        config["networks"][network.show_active()]["eth_usd_price_feed"],
        {"from": account}
    )
    # 搜索可知，当下1ETH = 4300.6
    # 50 usd / 4300 usd = 0.11
    # 确保getEntranceFee方法获得的值在这个范围内
    assert lottery.getEntranceFee() > Web3.toWei(0.010, "ether")
    assert lottery.getEntranceFee() < Web3.toWei(0.022, "ether")


