#!/usr/bin/env python3
"""
tools/run_tracker.py  —  Live save file tracker for Blue Prince

Watches MtHollyBlueprint.es3 and updates two JSON files on every save write:
  - events.json   : bool/int fields from the save
  - drafts.json   : per-room global draft counts from RoomRecords

Usage:
    python3 run_tracker.py                      # auto-detect save dir
"""

import sys
import os
import re
import time
import json
import argparse
import datetime


# ── Encryption (identical to decrypt_save.py) ─────────────────────────────────

KEY_STRING = (
    'D#vnrl%TI_9q0euFPIx+wKRuNx%Aja2-AtuH1jtMSk2k%H1jXjUPor08QaeQE=p5l='
    'LAIWaSYms-68SYVS0PPoWxgM1B8?8tirM+UGr=cp!5a3=B5tBsKYEUfqxN!H9DvRVkL'
    'W?6cMeZWxgov%OOXmfl9zRiqWPsXq95lEc4yax7hqf5m_i5ssn-OGgLA8LJu2ETibBi7'
    'DwLc-zQ4M9jRGIdV_izS_J_=3FA=rAo0HUiEr-HWYVnuK$OQUyaVMchXxf%EBo3A7Z-PXYm'
    '$6PPG%fJfWzV7M$L5he#y5cb?kVR67IfGzG$UzBcLhNMDhQFwQSEX59ZG7hP32q?6Pgir'
    'mvGTd-45+7ZKyG$FrDHoNw7ceUhrxYdzYSHd0yRz0T_RR_R5$GZda%DDfCUPHIaVlIhMq4FE'
    'Ozo?GL7wyXr9XD7SD_QGpjZh&NDwycjnBeOy2mmFazlOV5eR7jsiwYDde9jCOH&cOxeTody'
    '=iUEt|l7JCQ8IyX|0g3H&NO6DMveVqC9|OPkOZpO3DpM|||3LJ7PX40rZJXmLILu0UXU'
    '9hpM5'
)

SAVE_FILENAME = 'MtHollyBlueprint.es3'

DEFAULT_SAVE_DIRS = [
    os.path.expandvars(r'%USERPROFILE%\AppData\LocalLow\Dogubomb\BLUE PRINCE\storage'),
    os.path.expanduser('~/Library/Application Support/com.Dogubomb.BluePrince/storage'),
    os.path.expanduser('~/.config/unity3d/Dogubomb/BLUE PRINCE/storage'),
]

DEFAULT_OUT_DIR = r'C:\Program Files (x86)\Steam\steamapps\common\Blue Prince'



# ── Pure Python AES-128-CBC (no external libraries needed) ───────────────────
# Uses hashlib.pbkdf2_hmac (stdlib) for key derivation and a lookup-table
# optimised pure Python AES implementation for decryption (~0.5s per save).

_AES_SBOX = [
    0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
    0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
    0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
    0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
    0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
    0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
    0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
    0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
    0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
    0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
    0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
    0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
    0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
    0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
    0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
    0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16,
]
_AES_INV_SBOX = [0] * 256
for _i, _v in enumerate(_AES_SBOX): _AES_INV_SBOX[_v] = _i
_RCON = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1b, 0x36]

def _xtime(a): return (((a << 1) ^ 0x1b) & 0xff) if (a & 0x80) else ((a << 1) & 0xff)
_XTIME = [_xtime(a) for a in range(256)]

def _gmul(a, n):
    x2 = _XTIME[a]; x4 = _XTIME[x2]; x8 = _XTIME[x4]
    return {1:a, 2:x2, 3:a^x2, 8:x8, 9:a^x8, 11:a^x2^x8, 13:a^x4^x8, 14:x2^x4^x8}[n]

_M9  = [_gmul(a,  9) for a in range(256)]
_M11 = [_gmul(a, 11) for a in range(256)]
_M13 = [_gmul(a, 13) for a in range(256)]
_M14 = [_gmul(a, 14) for a in range(256)]


def _aes_expand_key(key: bytes) -> list:
    w = [list(key[i:i+4]) for i in range(0, 16, 4)]
    for i in range(4, 44):
        t = w[i-1][:]
        if i % 4 == 0:
            t = [_AES_SBOX[t[1]] ^ _RCON[i//4-1],
                 _AES_SBOX[t[2]], _AES_SBOX[t[3]], _AES_SBOX[t[0]]]
        w.append([w[i-4][j] ^ t[j] for j in range(4)])
    flat = []
    for word in w: flat.extend(word)
    return flat


def _aes_decrypt_block(block: bytes, rk: list) -> bytearray:
    s = bytearray(block)
    s = bytearray(s[i] ^ rk[160 + i] for i in range(16))
    for rnd in range(9, 0, -1):
        s0,s4,s8,s12 = s[0],s[4],s[8],s[12]
        s1,s5,s9,s13 = s[1],s[5],s[9],s[13]
        s2,s6,s10,s14 = s[2],s[6],s[10],s[14]
        s3,s7,s11,s15 = s[3],s[7],s[11],s[15]
        s = bytearray([s0,s13,s10,s7, s4,s1,s14,s11, s8,s5,s2,s15, s12,s9,s6,s3])
        s = bytearray(_AES_INV_SBOX[b] for b in s)
        base = rnd * 16
        s = bytearray(s[i] ^ rk[base + i] for i in range(16))
        ns = bytearray(16)
        for c in range(4):
            a0,a1,a2,a3 = s[c*4], s[c*4+1], s[c*4+2], s[c*4+3]
            ns[c*4  ] = _M14[a0] ^ _M11[a1] ^ _M13[a2] ^ _M9[a3]
            ns[c*4+1] = _M9[a0]  ^ _M14[a1] ^ _M11[a2] ^ _M13[a3]
            ns[c*4+2] = _M13[a0] ^ _M9[a1]  ^ _M14[a2] ^ _M11[a3]
            ns[c*4+3] = _M11[a0] ^ _M13[a1] ^ _M9[a2]  ^ _M14[a3]
        s = ns
    s0,s4,s8,s12 = s[0],s[4],s[8],s[12]
    s1,s5,s9,s13 = s[1],s[5],s[9],s[13]
    s2,s6,s10,s14 = s[2],s[6],s[10],s[14]
    s3,s7,s11,s15 = s[3],s[7],s[11],s[15]
    s = bytearray([s0,s13,s10,s7, s4,s1,s14,s11, s8,s5,s2,s15, s12,s9,s6,s3])
    s = bytearray(_AES_INV_SBOX[b] for b in s)
    return bytearray(s[i] ^ rk[i] for i in range(16))


def _aes_encrypt_block(block: bytes, rk: list) -> bytes:
    s = bytearray(block)
    s = bytearray(s[i] ^ rk[i] for i in range(16))
    for rnd in range(1, 11):
        s = bytearray(_AES_SBOX[b] for b in s)
        s0,s4,s8,s12 = s[0],s[4],s[8],s[12]
        s1,s5,s9,s13 = s[1],s[5],s[9],s[13]
        s2,s6,s10,s14 = s[2],s[6],s[10],s[14]
        s3,s7,s11,s15 = s[3],s[7],s[11],s[15]
        s = bytearray([s0,s5,s10,s15, s4,s9,s14,s3, s8,s13,s2,s7, s12,s1,s6,s11])
        if rnd < 10:
            ns = bytearray(16)
            for c in range(4):
                a0,a1,a2,a3 = s[c*4],s[c*4+1],s[c*4+2],s[c*4+3]
                x2a0=_XTIME[a0]; x2a1=_XTIME[a1]; x2a2=_XTIME[a2]; x2a3=_XTIME[a3]
                ns[c*4  ] = x2a0^(x2a1^a1)^a2^a3
                ns[c*4+1] = a0^x2a1^(x2a2^a2)^a3
                ns[c*4+2] = a0^a1^x2a2^(x2a3^a3)
                ns[c*4+3] = (x2a0^a0)^a1^a2^x2a3
            s = ns
        base = rnd * 16
        s = bytearray(s[i] ^ rk[base + i] for i in range(16))
    return bytes(s)


def _derive_key(salt: bytes) -> bytes:
    import hashlib
    return hashlib.pbkdf2_hmac('sha1', KEY_STRING.encode('utf-8'), salt, 100, dklen=16)


def decrypt_es3(path: str) -> str:
    with open(path, 'rb') as f:
        raw = f.read()
    salt = raw[:16]; ciphertext = raw[16:]
    key  = _derive_key(salt)
    rk   = _aes_expand_key(key)
    out  = bytearray(); prev = bytearray(salt)
    for i in range(0, len(ciphertext), 16):
        block = ciphertext[i:i+16]
        dec   = _aes_decrypt_block(block, rk)
        out.extend(dec[j] ^ prev[j] for j in range(16))
        prev  = bytearray(block)
    pad_len = out[-1]
    return bytes(out[:-pad_len]).decode('utf-8')


def encrypt_es3(plaintext: str, out_path: str):
    salt = os.urandom(16)
    key  = _derive_key(salt)
    rk   = _aes_expand_key(key)
    data    = plaintext.encode('utf-8')
    pad_len = 16 - (len(data) % 16)
    padded  = data + bytes([pad_len] * pad_len)
    out  = b''; prev = bytearray(salt)
    for i in range(0, len(padded), 16):
        chunk = padded[i:i+16]
        xored = bytes(chunk[j] ^ prev[j] for j in range(16))
        enc_b = _aes_encrypt_block(xored, rk)
        out  += enc_b; prev = bytearray(enc_b)
    with open(out_path, 'wb') as f:
        f.write(salt + out)
    print(f"Encrypted save written to: {out_path}")

# ── Room name → roomId mapping ────────────────────────────────────────────────
#
# Maps the exact room name strings from RoomRecords Keys in the save file
# to the roomId integers used in the drafts JSON.
#
# TO EDIT: change the number on the right of any room name.
# Rooms not listed here will be skipped in the drafts JSON output.
#
ROOM_NAME_TO_ID = {
    "THE FOUNDATION":           1,
    "ENTRANCE HALL":            2,
    "SPARE ROOM":               3,
    "ROTUNDA":                  4,
    "PARLOR":                   5,
    "BILLIARD ROOM":            6,
    "GALLERY":                  7,
    "ROOM 8":                   8,
    "CLOSET":                   9,
    "WALK-IN CLOSET":           10,
    "ATTIC":                    11,
    "STOREROOM":                12,
    "NOOK":                     13,
    "GARAGE":                   14,
    "MUSIC ROOM":               15,
    "LOCKER ROOM":              16,
    "DEN":                      17,
    "WINE CELLAR":              18,
    "TROPHY ROOM":              19,
    "BALLROOM":                 20,
    "PANTRY":                   21,
    "RUMPUS ROOM":              22,
    "VAULT":                    23,
    "OFFICE":                   24,
    "DRAWING ROOM":             25,
    "STUDY":                    26,
    "LIBRARY":                  27,
    "CHAMBER OF MIRRORS":       28,
    "THE POOL":                 29,
    "DRAFTING STUDIO":          30,
    "UTILITY CLOSET":           31,
    "BOILER ROOM":              32,
    "PUMP ROOM":                33,
    "SECURITY":                 34,
    "WORKSHOP":                 35,
    "LABORATORY":               36,
    "SAUNA":                    37,
    "COAT CHECK":               38,
    "MAIL ROOM":                39,
    "FREEZER":                  40,
    "DINING ROOM":              41,
    "OBSERVATORY":              42,
    "CONFERENCE ROOM":          43,
    "AQUARIUM":                 44,
    "ANTECHAMBER":              45,
    "ROOM 46":                  46,
    "BEDROOM":                  47,
    "BOUDOIR":                  48,
    "GUEST BEDROOM":            49,
    "NURSERY":                  50,
    "SERVANT'S QUARTERS":       51,
    "BUNK ROOM":                52,
    "HER LADYSHIP'S CHAMBER":   53,
    "MASTER BEDROOM":           54,
    "HALLWAY":                  55,
    "WEST WING HALL":           56,
    "EAST WING HALL":           57,
    "CORRIDOR":                 58,
    "PASSAGEWAY":               59,
    "SECRET PASSAGE":           60,
    "FOYER":                    61,
    "GREAT HALL":               62,
    "TERRACE":                  63,
    "PATIO":                    64,
    "COURTYARD":                65,
    "CLOISTER":                 66,
    "VERANDA":                  67,
    "GREENHOUSE":               68,
    "MORNING ROOM":             69,
    "SECRET GARDEN":            70,
    "COMMISSARY":               71,
    "KITCHEN":                  72,
    "LOCKSMITH":                73,
    "SHOWROOM":                 74,
    "LAUNDRY ROOM":             75,
    "BOOKSHOP":                 76,
    "THE ARMORY":               77,
    "GIFT SHOP":                78,
    "LAVATORY":                 79,
    "CHAPEL":                   80,
    "MAID'S CHAMBER":           81,
    "ARCHIVES":                 82,
    "GYMNASIUM":                83,
    "DARKROOM":                 84,
    "WEIGHT ROOM":              85,
    "FURNACE":                  86,
    "DOVECOTE":                 87,
    "THE KENNEL":               88,
    "CLOCK TOWER":              89,
    "CLASSROOM":                90,
    "SOLARIUM":                 91,
    "DORMITORY":                92,
    "VESTIBULE":                93,
    "CASINO":                   94,
    "PLANETARIUM":              95,
    "MECHANARIUM":              96,
    "TREASURE TROVE":           97,
    "THRONE ROOM":              98,
    "TUNNEL":                   99,
    "CONSERVATORY":             100,
    "LOST & FOUND":             101,
    "CLOSED EXHIBIT":           102,
    "TOOLSHED":                 103,
    "BOMB SHELTER":             104,
    "SCHOOLHOUSE":              105,
    "SHRINE":                   106,
    "ROOT CELLAR":              107,
    "HOVEL":                    108,
    "TRADING POST":             109,
    "TOMB":                     110,
    "Slot Zero":                111,
}


# ── Fields to track in events JSON ───────────────────────────────────────────
#
# EVENTS_BOOLS : save file key → written as a bool entry in events JSON
# EVENTS_INTS  : save file key → written as an int entry in events JSON

EVENTS_BOOLS = [
    "Planetarium Added",
    "Conservatory Added",
    "Tunnel Added",
    "Mechanarium Added",
    "Closed Exhibit Added",
    "Lost&Found Added",
    "Throne Room Added",
    "Treasure Trove Added",
    "Dovecote Added",
    "The Kennel Added",
    "Clock Tower Added",
    "Classroom Added",
    "Dormitory Added",
    "Solarium Added",
    "Casino Added",
    "Vestibule Added",
    "Room 46 Reached",
    "Trophy Explorers",
]

EVENTS_INTS = [
    "Chess Power",
]




FIELD_RE = re.compile(
    r'"([^"]+)":\{\s*"__type" : "([^"]+)"(.*?)\s*\}',
    re.DOTALL
)

SLOT_RE = re.compile(
    r'"(BluePrint\d*)" :.*?"objs" : \{(.*?)\},\s*"arrays"',
    re.DOTALL
)

ARRAY_BLOCK_RE = re.compile(
    r'"([^"]+)":\[(.*?)\]',
    re.DOTALL
)

ARRAY_VALUE_RE = re.compile(
    r'"__type" : "([^"]+)"(.*?)\s*\}',
    re.DOTALL
)


def parse_slot_fields(plaintext: str) -> dict:
    result = {}
    for m in SLOT_RE.finditer(plaintext):
        slot_key    = m.group(1)
        slot_fields = {}
        for fm in FIELD_RE.finditer(m.group(2)):
            slot_fields[fm.group(1)] = (fm.group(2), fm.group(3).strip())
        result[slot_key] = slot_fields
    return result


def parse_room_records(plaintext: str, slot_key: str) -> dict:
    slot_pattern = re.compile(
        re.escape(f'"{slot_key}"') + r'.*?"arrays"\s*:\s*\{(.*?)\},\s*"obj"',
        re.DOTALL
    )
    m = slot_pattern.search(plaintext)
    if not m:
        return {}

    arrays = {}
    for am in ARRAY_BLOCK_RE.finditer(m.group(1)):
        name   = am.group(1)
        values = []
        for vm in ARRAY_VALUE_RE.finditer(am.group(2)):
            typ = vm.group(1)
            val = vm.group(2).strip().strip('"')
            values.append((typ, val))
        arrays[name] = values

    keys_arr   = arrays.get('RoomRecords Keys',   [])
    values_arr = arrays.get('RoomRecords Values', [])

    result = {}
    for (_, room_name), (_, count_str) in zip(keys_arr, values_arr):
        try:
            result[room_name] = int(count_str)
        except ValueError:
            result[room_name] = 0

    return result


def pick_slot_manually() -> str:
    print("\nWhich save slot are you tracking?")
    print("  1 = BluePrint")
    print("  2 = BluePrint2")
    print("  3 = BluePrint3")
    print("  4 = BluePrint4")
    while True:
        ans = input("Slot [1-4]: ").strip()
        if ans == '1': return 'BluePrint'
        if ans == '2': return 'BluePrint2'
        if ans == '3': return 'BluePrint3'
        if ans == '4': return 'BluePrint4'
        print("Please enter 1, 2, 3, or 4.")


# ── JSON builder ─────────────────────────────────────────────────────────────

def build_events_json(fields: dict) -> dict:
    bools = []
    for key in EVENTS_BOOLS:
        if key in fields:
            val = fields[key][1] == 'true'
        else:
            val = False
        bools.append({"key": key, "value": val})

    ints = []
    for key in EVENTS_INTS:
        try:
            val = int(fields[key][1]) if key in fields else 0
        except ValueError:
            val = 0
        ints.append({"key": key, "value": val})

    return {"bools": bools, "ints": ints}


def build_drafts_json(room_records: dict) -> list:

    entries = {}
    for room_name, room_id in ROOM_NAME_TO_ID.items():
        entries[room_id] = {
            "roomId":       room_id,
            "globalDrafts": room_records.get(room_name, 0),
            "todayDrafts":  0,
        }
    return [entries[rid] for rid in sorted(entries.keys())]


# ── File I/O ──────────────────────────────────────────────────────────────────

def write_json(path: str, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def find_save_dir() -> str:
    for path in DEFAULT_SAVE_DIRS:
        if os.path.isdir(path):
            return path
    return None


# ── Main tracker ──────────────────────────────────────────────────────────────

def run_tracker(save_path: str, out_dir: str):
    events_path = os.path.join(out_dir, 'events.json')
    drafts_path = os.path.join(out_dir, 'drafts.json')

    active_slot = pick_slot_manually()
    slot_num    = active_slot.replace('BluePrint', '') or '1'

    print(f"\nSlot:         {active_slot}")
    print(f"Watching:     {save_path}")
    print(f"Events JSON:  {events_path}")
    print(f"Drafts JSON:  {drafts_path}")
    print("Press Ctrl+C to stop.\n")
    print("─" * 60)

    def process_save():
        try:
            plaintext    = decrypt_es3(save_path)
            slot_fields  = parse_slot_fields(plaintext)
            fields       = slot_fields.get(active_slot, {})
            room_records = parse_room_records(plaintext, active_slot)

            events = build_events_json(fields)
            drafts = build_drafts_json(room_records)

            write_json(events_path, events)
            write_json(drafts_path, drafts)

            ts      = datetime.datetime.now().strftime('%H:%M:%S')
            day     = fields.get('DAY', ('', '?'))[1]

            # ── DEBUG: print all rooms with non-zero draft counts ─────────────
            drafted = [(name, count) for name, count in room_records.items() if count > 0]
            if drafted:
                print(f"\n{ts}  [Slot {slot_num}]  Day {day}  — drafted rooms:")
                for name, count in sorted(drafted, key=lambda x: -x[1]):
                    room_id = ROOM_NAME_TO_ID.get(name, '???')
                    print(f"  roomId {str(room_id):>4}  |  {count:>2}x  |  {name}")
            else:
                print(f"{ts}  [Slot {slot_num}]  Day {day}  |  no rooms drafted yet")

            # ── Also flag any room names not in ROOM_NAME_TO_ID ───────────────
            unmapped = [name for name in room_records if name not in ROOM_NAME_TO_ID]
            if unmapped:
                print(f"  WARNING: {len(unmapped)} unmapped room name(s):")
                for name in unmapped:
                    print(f"    '{name}'")

            print(f"  JSONs updated.\n")

        except Exception as e:
            ts = datetime.datetime.now().strftime('%H:%M:%S')
            print(f"{ts}  WARNING: {e}")

    # Initial read on startup
    process_save()

    save_dir = os.path.dirname(save_path)

    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler

        class Handler(FileSystemEventHandler):
            def on_modified(self, event):
                if SAVE_FILENAME in os.path.basename(event.src_path):
                    time.sleep(0.3)  # wait for game to finish writing
                    process_save()

        observer = Observer()
        observer.schedule(Handler(), path=save_dir, recursive=False)
        observer.start()
        print("(using watchdog — instant notifications)\n")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

    except ImportError:
        print("(watchdog not installed — polling every second)")
        print("Install for instant notifications:  pip install watchdog\n")

        last_mtime = os.path.getmtime(save_path)
        try:
            while True:
                time.sleep(1)
                try:
                    mtime = os.path.getmtime(save_path)
                    if mtime != last_mtime:
                        last_mtime = mtime
                        time.sleep(0.3)
                        process_save()
                except FileNotFoundError:
                    pass
        except KeyboardInterrupt:
            pass

    print("\nTracker stopped.")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Live save tracker — updates events/drafts JSON on every save write',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Auto-detect save directory:
    python3 run_tracker.py

  Custom directories:
    python3 run_tracker.py --save-dir "C:/path/to/storage" --out-dir "C:/path/to/output"
        """
    )
    parser.add_argument('--save-dir',
        help='Path to Blue Prince storage folder. Auto-detected if omitted.')
    parser.add_argument('--out-dir',
        default=DEFAULT_OUT_DIR,
        help=f'Folder to write JSON files into. Default: {DEFAULT_OUT_DIR}')
    args = parser.parse_args()

    # Resolve save directory
    save_dir = args.save_dir or find_save_dir()
    if not save_dir:
        print("ERROR: Could not auto-detect save directory.")
        print("Use --save-dir to specify it manually.")
        sys.exit(1)

    save_path = os.path.join(save_dir, SAVE_FILENAME)
    if not os.path.isfile(save_path):
        print(f"ERROR: Save file not found: {save_path}")
        sys.exit(1)

    # Resolve output directory
    out_dir = args.out_dir
    if not os.path.isdir(out_dir):
        print(f"Output directory not found: {out_dir}")
        ans = input("Create it? [Y/n]: ").strip().lower()
        if ans in ('', 'y', 'yes'):
            os.makedirs(out_dir, exist_ok=True)
        else:
            sys.exit(1)

    run_tracker(save_path, out_dir)


if __name__ == '__main__':
    main()
