**Team Name:** Not Applicable  
**Team Members:**  
- Harshvardhan Choudhary (230002027)  
- Mayank Yadav (230002041)  
- Anuj Kothari (230008010)

## Project Workflow

1. **Environment Setup**  
   - Installed and configured bitcoind (Bitcoin Core) in Regtest mode.  
   - Updated `bitcoin.conf` with parameters like `regtest=1`, `rpcuser`, `rpcpassword`, and `rpcport`.  
   - Started the bitcoind server and verified that the node was running properly.  

2. **Wallet and Address Creation**  
   - Created or loaded a dedicated wallet using Bitcoin RPC.  
   - Generated Legacy addresses (P2PKH) for testing initial transactions.  
   - Generated SegWit addresses (P2SH-P2WPKH) for the second set of transactions.  

3. **Funding and Mining**  
   - Used the `sendtoaddress` command to fund the newly created addresses.  
   - Mined blocks (using `generatetoaddress`) to confirm transactions and ensure sufficient funds in the wallets.  

4. **Transaction Construction**  
   - Created raw transactions sending BTC from one address to another (e.g., A → B, then B → C).  
   - For Legacy transactions, used P2PKH outputs and unlocked them with corresponding signatures and public keys.  
   - For SegWit transactions, used P2SH-wrapped SegWit outputs, providing the redeem script and witness data.  

5. **Signing and Broadcasting**  
   - Used `signrawtransactionwithwallet` to produce valid signatures.  
   - Relayed the transactions with `sendrawtransaction`.  
   - Decoded each transaction using `decoderawtransaction` to verify script structure and correctness.  

6. **Validation**  
   - Confirmed transaction success by observing them in the Regtest blockchain.  
   - Ensured that the final stack evaluation for both Legacy and SegWit scripts returned a valid result.  
