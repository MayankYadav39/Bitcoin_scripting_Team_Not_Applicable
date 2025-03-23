import logging
import json
from decimal import Decimal
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException

logging.basicConfig(level=logging.INFO)

rpc_user = "Harsh"
rpc_password = "r123"
rpc_host = "127.0.0.1"
rpc_port = 8000
wallet_name = "my_segwit_wallet-2"

rpc_conn = AuthServiceProxy(f"http://{rpc_user}:{rpc_password}@{rpc_host}:{rpc_port}")

try:
    existing_wallets = rpc_conn.listwallets()
    logging.info(f"Existing wallets: {existing_wallets}")
except JSONRPCException as e:
    logging.error(f"Error listing wallets: {str(e)}")
    exit(1)

if wallet_name in existing_wallets:
    try:
        rpc_conn.loadwallet(wallet_name)
        logging.info(f"Loaded existing wallet: {wallet_name}")
    except JSONRPCException as e:
        if "already loaded" not in str(e):
            logging.error(f"Error loading wallet: {str(e)}")
            exit(1)
        else:
            logging.info("Wallet already loaded")
else:
    try:
        rpc_conn.createwallet(wallet_name)
        logging.info(f"Created new wallet: {wallet_name}")
    except JSONRPCException as e:
        logging.error(f"Error creating wallet: {str(e)}")
        exit(1)

rpc_conn = AuthServiceProxy(f"http://{rpc_user}:{rpc_password}@{rpc_host}:{rpc_port}/wallet/{wallet_name}")

try:
    wallet_info = rpc_conn.getwalletinfo()
    logging.info(f"Successfully connected to wallet: {wallet_info['walletname']}")
except JSONRPCException as e:
    logging.error(f"Failed to connect to wallet: {str(e)}")
    exit(1)

mining_address = rpc_conn.getnewaddress("mining", "p2sh-segwit")
try:
    blocks = rpc_conn.generatetoaddress(101, mining_address)
    logging.info(f"Generated 101 blocks. Last block hash: {blocks[-1]}")
    
    balance = rpc_conn.getbalance()
    logging.info(f"Wallet balance after mining: {balance} BTC")
except JSONRPCException as e:
    logging.warning(f"Could not mine blocks (this is okay if not on regtest): {str(e)}")

A_prim = rpc_conn.getnewaddress("", "p2sh-segwit")
B_prim = rpc_conn.getnewaddress("", "p2sh-segwit")
C_prim = rpc_conn.getnewaddress("", "p2sh-segwit")
logging.info(f"SegWit Addresses: A'={A_prim}, B'={B_prim}, C'={C_prim}")

try:
    fund_txid = rpc_conn.sendtoaddress(A_prim, 1)
    logging.info(f"Funded A' with txid={fund_txid}")
    
    fund_raw_tx = rpc_conn.getrawtransaction(fund_txid)
    logging.info(f"Fund A' raw transaction hex: {fund_raw_tx}")
except JSONRPCException as e:
    if "Fee estimation failed" in str(e):
        logging.error("Fee estimation failed. Try setting fallbackfee in bitcoin.conf")
        logging.info("Attempting to use explicit fee rate...")
        try:
            fund_txid = rpc_conn.sendtoaddress(A_prim, 1, "", "", False, True, 1, "economical")
            logging.info(f"Funded A' with explicit fee rate, txid={fund_txid}")
            
            fund_raw_tx = rpc_conn.getrawtransaction(fund_txid)
            logging.info(f"Fund A' raw transaction hex: {fund_raw_tx}")
        except JSONRPCException as e2:
            logging.error(f"Still failed with explicit fee rate: {str(e2)}")
            exit(1)
    else:
        logging.error(f"Error funding address A': {str(e)}")
        exit(1)

try:
    confirm_blocks = rpc_conn.generatetoaddress(1, rpc_conn.getnewaddress())
    logging.info("Generated 1 block to confirm transaction to A'")
except JSONRPCException as e:
    logging.error(f"Error generating block: {str(e)}")
    exit(1)

utxosA = [u for u in rpc_conn.listunspent() if u["address"] == A_prim]

if not utxosA:
    logging.info("No UTXOs for A'.")
    exit(1)

uA = utxosA[0]
inA = [{"txid": uA["txid"], "vout": uA["vout"]}]
outA = {B_prim: 0.5}
changeA = Decimal(str(uA["amount"])) - Decimal("0.5") - Decimal("0.00001")

if changeA > 0:
    outA[A_prim] = float(round(changeA, 8))

rawAB = rpc_conn.createrawtransaction(inA, outA)
logging.info(f"Raw A'->B' transaction hex (unsigned): {rawAB}")

decAB = rpc_conn.decoderawtransaction(rawAB)
logging.info(f"Decoded A'->B': {json.dumps(decAB, default=str, indent=2)}")

signedAB = rpc_conn.signrawtransactionwithwallet(rawAB)
logging.info(f"Raw A'->B' transaction hex (signed): {signedAB['hex']}")

if signedAB["complete"]:
    logging.info("Transaction A'->B' successfully signed")
else:
    logging.error("Failed to sign transaction A'->B'")
    exit(1)

try:
    txidAB = rpc_conn.sendrawtransaction(signedAB["hex"])
    logging.info(f"A'->B' broadcast, txid={txidAB}")
except JSONRPCException as e:
    logging.error(f"Failed to broadcast A'->B' transaction: {str(e)}")
    exit(1)

try:
    ab_block = rpc_conn.generatetoaddress(1, rpc_conn.getnewaddress())
    ab_block_hash = ab_block[0]
    logging.info(f"Generated 1 block to confirm transaction to B', hash={ab_block_hash}")
except JSONRPCException as e:
    logging.error(f"Error generating block: {str(e)}")
    exit(1)

utxosB = [u for u in rpc_conn.listunspent() if u["address"] == B_prim]
if not utxosB:
    logging.info("No UTXOs for B'.")
    exit(1)

uB = utxosB[0]
inB = [{"txid": uB["txid"], "vout": uB["vout"]}]
outB = {C_prim: 0.3}
changeB = Decimal(str(uB["amount"])) - Decimal("0.3") - Decimal("0.00001")

if changeB > 0:
    outB[B_prim] = float(round(changeB, 8))

rawBC = rpc_conn.createrawtransaction(inB, outB)
logging.info(f"Raw B'->C' transaction hex (unsigned): {rawBC}")

decBC = rpc_conn.decoderawtransaction(rawBC)
logging.info(f"Decoded B'->C': {json.dumps(decBC, default=str, indent=2)}")

signedBC = rpc_conn.signrawtransactionwithwallet(rawBC)
logging.info(f"Raw B'->C' transaction hex (signed): {signedBC['hex']}")

if signedBC["complete"]:
    logging.info("Transaction B'->C' successfully signed")
else:
    logging.error("Failed to sign transaction B'->C'")
    exit(1)

try:
    txidBC = rpc_conn.sendrawtransaction(signedBC["hex"])
    logging.info(f"B'->C' broadcast, txid={txidBC}")
except JSONRPCException as e:
    logging.error(f"Failed to broadcast B'->C' transaction: {str(e)}")
    exit(1)

try:
    bc_block = rpc_conn.generatetoaddress(1, rpc_conn.getnewaddress())
    bc_block_hash = bc_block[0]
    logging.info(f"Generated 1 block to confirm transaction to C', hash={bc_block_hash}")
except JSONRPCException as e:
    logging.error(f"Error generating block: {str(e)}")
    exit(1)

try:
    decodedBC = rpc_conn.getrawtransaction(txidBC, 1, bc_block_hash)
    logging.info(f"SegWit transaction details B'->C':")
    
    witnessData = []
    for vin in decodedBC["vin"]:
        if "txinwitness" in vin:
            witnessData.append({"input": vin["txid"] + ":" + str(vin["vout"]), "witness": vin["txinwitness"]})
        elif "scriptSig" in vin:
            witnessData.append({"input": vin["txid"] + ":" + str(vin["vout"]), "scriptSig": vin["scriptSig"]})

    logging.info(f"Witness data from B'->C': {json.dumps(witnessData, default=str, indent=2)}")
except JSONRPCException as e:
    logging.error(f"Error retrieving transaction details: {str(e)}")

balanceA = sum(u["amount"] for u in rpc_conn.listunspent() if u["address"] == A_prim)
balanceB = sum(u["amount"] for u in rpc_conn.listunspent() if u["address"] == B_prim)
balanceC = sum(u["amount"] for u in rpc_conn.listunspent() if u["address"] == C_prim)

logging.info(f"Final balances: A'={balanceA}, B'={balanceB}, C'={balanceC}")

try:
    txInfoAB = rpc_conn.getrawtransaction(txidAB, 1, ab_block_hash)
    txInfoBC = rpc_conn.getrawtransaction(txidBC, 1, bc_block_hash)
    
    logging.info(f"A'->B' transaction size: {txInfoAB['size']} bytes, vsize: {txInfoAB['vsize']} virtual bytes")
    logging.info(f"B'->C' transaction size: {txInfoBC['size']} bytes, vsize: {txInfoBC['vsize']} virtual bytes")
    
    logging.info(f"A'->B' transaction weight: {txInfoAB['weight']} weight units")
    logging.info(f"B'->C' transaction weight: {txInfoBC['weight']} weight units")
    
except JSONRPCException as e:
    logging.error(f"Error retrieving transaction details: {str(e)}")

logging.info("\n----- RAW TRANSACTION HEX SUMMARY (SEGWIT) -----")
logging.info(f"Transaction A'->B' (unsigned): {rawAB}")
logging.info(f"Transaction A'->B' (signed): {signedAB['hex']}")
logging.info(f"Transaction B'->C' (unsigned): {rawBC}")
logging.info(f"Transaction B'->C' (signed): {signedBC['hex']}")