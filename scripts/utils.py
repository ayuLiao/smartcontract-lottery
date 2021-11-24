from brownie import accounts, network, config, Contract
from brownie import MockV3Aggregator, VRFCoordinatorMock, LinkToken

FORKED_LOCAL_ENVIRONMENTS = ["mainnet-fork", "mainnet-fork-dev"]
LOCAL_BLOCKCHAIN_ENVIRONMENTS = ["development", "ganache-local"]
DECIMALS = 8  # 小数
INITIAL_VALUE = 200000000000  # 初始值

contract_to_mock = {
    "eth_usd_price_feed": MockV3Aggregator,
    "vrf_coordinator": VRFCoordinatorMock,
    "link_token": LinkToken,
}


def get_account(index=None, id=None):
    # 获取account方式有2中
    # accounts[0]  通过下标
    # accounts.add("env") 如果通过add的方式添加了账号
    # accounts.load("id") 则可以通过load方法去获取该账号
    if index:
        return accounts[index]
    if id:
        return accounts.load(id)
    if (
            network.show_active() in LOCAL_BLOCKCHAIN_ENVIRONMENTS
            or network.show_active() in FORKED_LOCAL_ENVIRONMENTS
    ):
        return accounts[0]

    return accounts.add(config["wallets"]["from_key"])


def get_contract(contract_name):
    contract_type = contract_to_mock[contract_name]
    if network.show_active() in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        # 假设contract_type = MockV3Aggregator，len(contract_type) 相当于 MockV3Aggregator.length
        if len(contract_type) <= 0:
            # 本地网络，如果没有该合约，则部署对应的Mock形式合约
            deploy_mocks()
        contract = contract_type[-1]
    else:
        # 非本地网络，直接从配置文件中取合约的地址
        contract_address = config["networks"][network.show_active()][contract_name]
        # 通过ABI的形式构建出合约对象
        contract = Contract.from_abi(
            contract_type._name,  # 合约名称
            contract_address,  # 合约地址
            contract_type.abi  # 合约ABI
        )
    return contract


def deploy_mocks(decimals=DECIMALS, initial_value=INITIAL_VALUE):
    account = get_account()
    # MockV3Aggregator合约的constructor需要decimals和initial_value
    MockV3Aggregator.deploy(decimals, initial_value, {"from": account})
    link_token = LinkToken.deploy({"from": account})
    VRFCoordinatorMock.deploy(link_token.address, {"from": account})
    print('Mock contract deployed!')



def fund_with_link(contract_address, account=None, link_token=None, amount=100000000000000000):
    """
    将账号中的LINK代币转到合约中
    :param contract_address: 合约地址
    :param account: 账号
    :param link_token: link合约对象
    :param amount: 转账金额，默认0.1LINK
    :return:
    """
    account = account if account else get_account()
    link_token = link_token if link_token else get_contract('link_token')
    # link合约发起交易，将link合约中的代币发送到contract_address中，发送amount的数量，交易过程需要account账号签名
    tx = link_token.transfer(contract_address, amount, {"from": account})
    tx.wait(1)
    print("Fund contract")
    return tx