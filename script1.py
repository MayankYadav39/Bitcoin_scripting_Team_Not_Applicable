import logging
import json
from decimal import Decimal
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException

logging.basicConfig(level=logging.INFO)

rpc_user = "Harsh"
rpc_password = "r123"
rpc_host = "127.0.0.1"
rpc_port = 8000
wallet_name = "mywallet-5"

rpc_connection = AuthServiceProxy(f"http://{rpc_user}:{rpc_password}@{rpc_host}:{rpc_port}")

try:
    existing_wallets = rpc_connection.listwallets()
    logging.info(f"Existing wallets: {existing_wallets}")
except JSONRPCException as e:
    logging.error(f"Error listing wallets: {str(e)}")
    exit(1)

if wallet_name in existing_wallets:
    try:
        rpc_connection.loadwallet(wallet_name)
        logging.info(f"Loaded existing wallet: {wallet_name}")
    except JSONRPCException as e:
        if "already loaded" not in str(e):
            logging.error(f"Error loading wallet: {str(e)}")
            exit(1)
        else:
            logging.info("Wallet already loaded")
else:
    try:
        rpc_connection.createwallet(wallet_name)
        logging.info(f"Created new wallet: {wallet_name}")
    except JSONRPCException as e:
        logging.error(f"Error creating wallet: {str(e)}")
        exit(1)

rpc_connection = AuthServiceProxy(f"http://{rpc_user}:{rpc_password}@{rpc_host}:{rpc_port}/wallet/{wallet_name}")

try:
    wallet_info = rpc_connection.getwalletinfo()
    logging.info(f"Successfully connected to wallet: {wallet_info['walletname']}")
except JSONRPCException as e:
    logging.error(f"Failed to connect to wallet: {str(e)}")
    exit(1)

mining_address = rpc_connection.getnewaddress("mining", "legacy")
try:
    blocks = rpc_connection.generatetoaddress(101, mining_address)
    logging.info(f"Generated 101 blocks. Last block hash: {blocks[-1]}")
    
    balance = rpc_connection.getbalance()
    logging.info(f"Wallet balance after mining: {balance} BTC")
except JSONRPCException as e:
    logging.warning(f"Could not mine blocks (this is okay if not on regtest): {str(e)}")

A = rpc_connection.getnewaddress("", "legacy")
B = rpc_connection.getnewaddress("", "legacy")
C = rpc_connection.getnewaddress("", "legacy")
logging.info(f"Addresses: A={A}, B={B}, C={C}")

try:
    fund_txid = rpc_connection.sendtoaddress(A, 1)
    logging.info(f"Funded A with txid={fund_txid}")
    
    fund_raw_tx = rpc_connection.getrawtransaction(fund_txid)
    logging.info(f"Fund A raw transaction hex: {fund_raw_tx}")
except JSONRPCException as e:
    if "Fee estimation failed" in str(e):
        logging.error("Fee estimation failed. Try setting fallbackfee in bitcoin.conf")
        logging.info("Attempting to use explicit fee rate...")
        try:
            fund_txid = rpc_connection.sendtoaddress(A, 1, "", "", False, True, 1, "economical")
            logging.info(f"Funded A with explicit fee rate, txid={fund_txid}")
            
            fund_raw_tx = rpc_connection.getrawtransaction(fund_txid)
            logging.info(f"Fund A raw transaction hex: {fund_raw_tx}")
        except JSONRPCException as e2:
            logging.error(f"Still failed with explicit fee rate: {str(e2)}")
            exit(1)
    else:
        logging.error(f"Error funding address A: {str(e)}")
        exit(1)

try:
    a_block = rpc_connection.generatetoaddress(1, rpc_connection.getnewaddress())
    a_block_hash = a_block[0]
    logging.info(f"Generated 1 block to confirm transaction to A, hash={a_block_hash}")
except JSONRPCException as e:
    logging.error(f"Error generating block: {str(e)}")
    exit(1)

utxosA = [u for u in rpc_connection.listunspent() if u["address"] == A]

if not utxosA:
    logging.info("No UTXOs for A.")
    exit(1)

uA = utxosA[0]
inputsA = [{"txid": uA["txid"], "vout": uA["vout"]}]
outputsA = {B: 0.5}
changeA = Decimal(str(uA["amount"])) - Decimal("0.5") - Decimal("0.00001")

if changeA > 0:
    outputsA[A] = float(round(changeA, 8))

rawAB = rpc_connection.createrawtransaction(inputsA, outputsA)
logging.info(f"Raw A->B transaction hex (unsigned): {rawAB}")

decodedAB = rpc_connection.decoderawtransaction(rawAB)
logging.info(f"Decoded raw A->B: {json.dumps(decodedAB, default=str, indent=2)}")

signedAB = rpc_connection.signrawtransactionwithwallet(rawAB)
logging.info(f"Raw A->B transaction hex (signed): {signedAB['hex']}")

txidAB = rpc_connection.sendrawtransaction(signedAB["hex"])
logging.info(f"Broadcasted A->B, txid={txidAB}")

ab_block = rpc_connection.generatetoaddress(1, rpc_connection.getnewaddress())
ab_block_hash = ab_block[0]
logging.info(f"Generated 1 block to confirm transaction to B, hash={ab_block_hash}")

list_B_utxos = [u for u in rpc_connection.listunspent() if u["address"] == B]
if not list_B_utxos:
    logging.info("No UTXOs for B.")
    exit(1)

uB = list_B_utxos[0]
inputsB = [{"txid": uB["txid"], "vout": uB["vout"]}]
outputsB = {C: 0.3}
changeB = Decimal(str(uB["amount"])) - Decimal("0.3") - Decimal("0.00001")

if changeB > 0:
    outputsB[B] = float(round(changeB, 8))

rawBC = rpc_connection.createrawtransaction(inputsB, outputsB)
logging.info(f"Raw B->C transaction hex (unsigned): {rawBC}")

signedBC = rpc_connection.signrawtransactionwithwallet(rawBC)
logging.info(f"Raw B->C transaction hex (signed): {signedBC['hex']}")

txidBC = rpc_connection.sendrawtransaction(signedBC["hex"])
logging.info(f"Broadcasted B->C, txid={txidBC}")

bc_block = rpc_connection.generatetoaddress(1, rpc_connection.getnewaddress())
bc_block_hash = bc_block[0]
logging.info(f"Generated 1 block to confirm transaction to C, hash={bc_block_hash}")

try:
    decodedBC = rpc_connection.getrawtransaction(txidBC, 1, bc_block_hash)
    logging.info(f"Transaction details B->C:")
    
    scriptSigBtoC = []
    for vin in decodedBC["vin"]:
        if "txinwitness" in vin:
            scriptSigBtoC.append(vin["txinwitness"])
        elif "scriptSig" in vin:
            scriptSigBtoC.append(vin["scriptSig"])
    logging.info(f"ScriptSig or Witness from B->C: {scriptSigBtoC}")
except JSONRPCException as e:
    logging.error(f"Error retrieving transaction details: {str(e)}")

balanceA = sum(u["amount"] for u in rpc_connection.listunspent() if u["address"] == A)
balanceB = sum(u["amount"] for u in rpc_connection.listunspent() if u["address"] == B)
balanceC = sum(u["amount"] for u in rpc_connection.listunspent() if u["address"] == C)

logging.info(f"Final balances: A={balanceA}, B={balanceB}, C={balanceC}")

try:
    txInfoAB = rpc_connection.getrawtransaction(txidAB, 1, ab_block_hash)
    txInfoBC = rpc_connection.getrawtransaction(txidBC, 1, bc_block_hash)
    
    logging.info(f"A->B transaction size: {txInfoAB['size']} bytes")
    logging.info(f"B->C transaction size: {txInfoBC['size']} bytes")
except JSONRPCException as e:
    logging.error(f"Error retrieving transaction details: {str(e)}")

logging.info("\n----- RAW TRANSACTION HEX SUMMARY -----")
logging.info(f"Transaction A->B (unsigned): {rawAB}")
logging.info(f"Transaction A->B (signed): {signedAB['hex']}")
logging.info(f"Transaction B->C (unsigned): {rawBC}")
logging.info(f"Transaction B->C (signed): {signedBC['hex']}")