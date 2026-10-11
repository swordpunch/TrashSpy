"""Extract first icon group from an exe and save as .ico for visual check."""
import pefile
import struct
import sys

src = sys.argv[1]
dst = sys.argv[2]
p = pefile.PE(src)

grp_entry = next(e for e in p.DIRECTORY_ENTRY_RESOURCE.entries if e.id == 14)
g = grp_entry.directory.entries[0].directory.entries[0]
data = p.get_data(g.data.struct.OffsetToData, g.data.struct.Size)
count = struct.unpack("<H", data[4:6])[0]
print("group count:", count)

icon_entry = next(e for e in p.DIRECTORY_ENTRY_RESOURCE.entries if e.id == 3)
id_map = {}
for id_entry in icon_entry.directory.entries:
    for lang_entry in id_entry.directory.entries:
        d = lang_entry.data.struct
        id_map[id_entry.id] = p.get_data(d.OffsetToData, d.Size)

out = [struct.pack("<HHH", 0, 1, count)]
offset = 6 + 16 * count
for i in range(count):
    w, h, cc, res, planes, bpp, size, rid = struct.unpack("<BBBBHHIH", data[6 + 14 * i:6 + 14 * i + 14])
    blob = id_map[rid]
    out.append(struct.pack("<BBBBHHII", w, h, cc, res, planes, bpp, len(blob), offset))
    offset += len(blob)
for i in range(count):
    _, _, _, _, _, _, _, rid = struct.unpack("<BBBBHHIH", data[6 + 14 * i:6 + 14 * i + 14])
    out.append(id_map[rid])

with open(dst, "wb") as f:
    f.write(b"".join(out))
print("saved", dst)
