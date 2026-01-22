# NTAG424 DNA ChangeFileSettings (0x5F) - Technical Report

**Date:** January 22, 2026  
**Author:** Claude (Anthropic) with David @ DLT  
**Status:** ✅ RESOLVED  

---

## Executive Summary

After extensive debugging and analysis, the NTAG424 DNA `ChangeFileSettings` command (0x5F) has been successfully implemented. The root cause was **incorrect secure messaging framing** - specifically, the FileNo byte was being included in the encrypted payload when it should only appear as an unencrypted command header.

**Key Result:** `SW=9100` (Success) achieved with CmdData `00E0EE` for File 02.

---

## 1. Problem Statement

The CORA Provisioner v1.9 was failing to execute the `ChangeFileSettings` command on NTAG424 DNA cards, consistently receiving error codes:
- `0x9E` - Parameter Error
- `0x7E` - Length Error  
- `0x1E` - Integrity Error (MAC verification failed)
- `0xF0` - Unknown Error

Despite successful authentication (confirmed by `0x9100` response to AuthenticateEV2First), the secure messaging for ChangeFileSettings was being rejected.

---

## 2. Investigation Timeline

### Phase 1: Brute Force Approach (Failed)
- Created exhaustive testing tool to try all possible 3-byte CmdData combinations
- Tested 25,333+ smart patterns across multiple KeyNo and FileNo combinations
- **Result:** 0 successes, but valuable insight: `0x9E` (crypto OK, params invalid) confirmed encryption framing was partially correct

### Phase 2: Datasheet Analysis (Breakthrough)
- Retrieved NXP Application Note AN12196 (NTAG 424 DNA features and hints)
- Discovered Section 6.9 "Change NDEF File Settings" with exact byte-level examples
- Identified critical differences between our implementation and the specification

### Phase 3: Root Cause Identification
- Used `GetFileSettings` (0xF5) to read actual tag configuration
- Discovered SDM was **disabled** (FileOption=0x00), meaning 3-byte CmdData was correct
- Identified 4 separate bugs in secure messaging implementation

---

## 3. Root Cause Analysis

### The Four Bugs

#### Bug 1: Encrypted Payload Content
```
WRONG:  Encrypt(FileNo || CmdData)
CORRECT: Encrypt(CmdData only)
```
FileNo is a **CmdHeader**, not part of the encrypted payload.

#### Bug 2: IV Construction
```
WRONG:  IV_input = A55A || TI || CmdCtr || Cmd || FileNo || 00×6
CORRECT: IV_input = A55A || TI || CmdCtr || 00×8
```
The IV for ChangeFileSettings uses 8 zero bytes, not command-specific bytes.

#### Bug 3: MAC Input Missing CmdHeader
```
WRONG:  MAC_input = Cmd || CmdCtr || TI || Encrypted
CORRECT: MAC_input = Cmd || CmdCtr || TI || CmdHeader || Encrypted
```
CmdHeader (FileNo) must be included in MAC calculation.

#### Bug 4: APDU Structure
```
WRONG:  APDU_data = Encrypted || MACt
CORRECT: APDU_data = CmdHeader || Encrypted || MACt
```
FileNo must appear unencrypted at the start of APDU data.

---

## 4. Correct Implementation

### Per AN12196 Table 19: ChangeFileSettings in CommMode.Full

```python
def change_file_settings_full(self, file_no: int, cmddata: bytes) -> int:
    cmdctr_le = self.cmdctr.to_bytes(2, "little")

    # 1. Plaintext = CmdData only (FileNo is CmdHeader, sent unencrypted)
    padded = pad_iso7816_4(cmddata, 16)

    # 2. IV = E(KSesAuthENC, A55A || TI || CmdCtr || 00×8)
    iv_in = b"\xA5\x5A" + self.ti + cmdctr_le + (b"\x00" * 8)
    ivc = aes_ecb_enc(self.ks_enc, iv_in)

    # 3. Encrypted = E(KSesAuthENC, IVc, CmdData || Padding)
    enc = aes_cbc_enc(self.ks_enc, ivc, padded)

    # 4. MAC = MACt(KSesAuthMAC, Cmd || CmdCtr || TI || CmdHeader || Encrypted)
    mac_in = bytes([0x5F]) + cmdctr_le + self.ti + bytes([file_no]) + enc
    mact = mac_trunc_odd(cmac_aes(self.ks_mac, mac_in))

    # 5. APDU data = CmdHeader || Encrypted || MACt
    apdu_data = bytes([file_no]) + enc + mact
    apdu = [0x90, 0x5F, 0x00, 0x00, len(apdu_data)] + list(apdu_data) + [0x00]
    
    resp, sw1, sw2 = self._txrx(apdu)
    if sw1 == 0x91 and sw2 == 0x00:
        self.cmdctr += 1
    return sw2
```

### APDU Wire Format

```
TX: 90 5F 00 00 19 02 [16-byte encrypted] [8-byte MACt] 00
    │  │        │  │   └─ Encrypted CmdData (padded to 16 bytes)
    │  │        │  └─ FileNo (CmdHeader, unencrypted)
    │  │        └─ Lc = 1 + 16 + 8 = 25 (0x19)
    │  └─ INS = ChangeFileSettings
    └─ CLA = 0x90

RX: [8-byte response MACt] 91 00
                           └─ Success!
```

---

## 5. CmdData Format Reference

### When SDM is DISABLED (FileOption bit 6 = 0)

| Byte | Field | Description |
|------|-------|-------------|
| 0 | FileOption | Bits 0-1: CommMode (0=Plain, 1=MAC, 3=Full) |
| 1-2 | AccessRights | RW[7:4], Change[3:0], Read[7:4], Write[3:0] |

**Example:** `00E0EE` = Plain mode, RW=Free, Change=Key0, Read=Free, Write=Free

### When SDM is ENABLED (FileOption bit 6 = 1)

| Bytes | Field | Description |
|-------|-------|-------------|
| 0 | FileOption | 0x40 = SDM enabled, Plain mode |
| 1-2 | AccessRights | Standard access rights |
| 3 | SDMOptions | UID mirror, ReadCtr, etc. |
| 4-5 | SDMAccessRights | SDM key assignments |
| 6-8 | PICCDataOffset | 3-byte LE offset |
| 9-11 | SDMMACInputOffset | 3-byte LE offset |
| 12-14 | SDMMACOffset | 3-byte LE offset |

**Example:** `4000E0C1F121200000430000430000` (15 bytes)

---

## 6. Test Results

### Successful Test

```
Card: NTAG424 DNA
UID: 045a78d2151990
Key: F7F692CA64DF5C0074FB4DADE43EA5EF (Key 0)

GetFileSettings Response:
  FileType: 0x00 (StandardData)
  FileOption: 0x00 (Plain, SDM disabled)
  AccessRights: E0EE
  FileSize: 256 bytes

ChangeFileSettings:
  FileNo: 0x02
  CmdData: 00E0EE
  
TX: 905F000019025BB310B58F36879F0077E858BABBAE6A2A9068E8D81C0E0F00
RX: 452BBB55A9402A35  SW=9100

Result: ✅ SUCCESS
```

---

## 7. Key Learnings

1. **FileNo is CmdHeader, not payload** - This is the fundamental difference between our broken and working implementations.

2. **IV format varies by command** - Not all commands use the same IV structure. ChangeFileSettings uses 8 zero bytes after CmdCtr.

3. **MAC includes unencrypted headers** - Even though FileNo isn't encrypted, it's still authenticated via the MAC.

4. **GetFileSettings is essential** - Always read current settings before attempting to change them. SDM status determines CmdData length.

5. **Error codes are informative:**
   - `0x1E` = MAC wrong (crypto framing issue)
   - `0x9E` = MAC OK, params wrong (correct crypto, wrong CmdData)
   - `0x7E` = Wrong length (SDM mismatch)

---

## 8. Files Delivered

| File | Description |
|------|-------------|
| `eval.py` | Working NTAG424 DNA test tool with correct ChangeFileSettings |
| `NTAG424_ChangeFileSettings_Report.md` | This report |

---

## 9. References

- NXP AN12196: "NTAG 424 DNA and NTAG 424 DNA TagTamper features and hints" Rev 1.8
- NXP NT4H2421Gx Datasheet: "NTAG 424 DNA - Secure NFC T4T compliant IC"
- ISO/IEC 7816-4: Smart card commands
- NIST SP 800-38B: CMAC specification

---

## 10. Conclusion

The NTAG424 DNA ChangeFileSettings command is now fully operational. The fix has been validated on hardware and can be integrated into the CORA Provisioner. The key architectural insight is that NTAG424 DNA secure messaging treats CmdHeader (FileNo) as an authenticated but unencrypted field - it participates in MAC calculation but is not included in the encrypted payload.

**Status: RESOLVED ✅**

---

*Report generated by Claude (Anthropic) - January 22, 2026*
