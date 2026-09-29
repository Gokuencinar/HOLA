from pathlib import Path
import struct
import sys

CPU_TYPE_ARM64 = 0x0100000C
CPU_SUBTYPE_ARM64_ALL = 0x00000000
CPU_SUBTYPE_ARM64E_NEW = 0x80000002

def read_arches(path):
    data = Path(path).read_bytes()
    if len(data) < 12:
        raise SystemExit(f"{path}: file too small")

    be_magic = struct.unpack(">I", data[:4])[0]
    arches = []

    if be_magic == 0xCAFEBABE:
        count = struct.unpack(">I", data[4:8])[0]
        off = 8
        for _ in range(count):
            cputype, subtype, fileoff, size, align = struct.unpack(">IIIII", data[off:off+20])
            arches.append((cputype, subtype))
            off += 20
    elif be_magic == 0xCAFEBABF:
        count = struct.unpack(">I", data[4:8])[0]
        off = 8
        for _ in range(count):
            cputype, subtype, fileoff, size, align, reserved = struct.unpack(">IIQQII", data[off:off+32])
            arches.append((cputype, subtype))
            off += 32
    else:
        le_magic = struct.unpack("<I", data[:4])[0]
        if le_magic != 0xFEEDFACF:
            raise SystemExit(f"{path}: unsupported Mach-O magic {be_magic:#x}/{le_magic:#x}")
        cputype, subtype = struct.unpack("<II", data[4:12])
        arches.append((cputype, subtype))

    return arches

if len(sys.argv) < 2:
    raise SystemExit("usage: validate_bwrh_arm64e.py <Mach-O> [<Mach-O> ...]")

for item in sys.argv[1:]:
    arches = read_arches(item)
    print(f"{item}: " + ", ".join(f"cpu={c:#x} subtype={s:#x}" for c, s in arches))

    if (CPU_TYPE_ARM64, CPU_SUBTYPE_ARM64_ALL) not in arches:
        raise SystemExit(f"{item}: missing arm64 slice")
    if (CPU_TYPE_ARM64, CPU_SUBTYPE_ARM64E_NEW) not in arches:
        raise SystemExit(f"{item}: missing modern arm64e slice (expected subtype 0x80000002)")

    legacy = [(c, s) for c, s in arches if c == CPU_TYPE_ARM64 and (s & 0xFF) == 2 and not (s & 0x80000000)]
    if legacy:
        raise SystemExit(f"{item}: legacy arm64e ABI detected: {legacy}")

print("Modern arm64e validation passed.")
