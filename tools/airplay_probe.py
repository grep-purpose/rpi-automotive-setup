import xbmc

labels = [
    "Player.Title",
    "Player.Art(thumb)",
    "Player.Art(fanart)",
    "Player.Art(icon)",
    "Player.Art(album.thumb)",
    "MusicPlayer.Title",
    "MusicPlayer.Artist",
    "MusicPlayer.Album",
    "MusicPlayer.Cover",
    "MusicPlayer.Property(Album_Description)",
    "Player.FilenameAndPath",
    "Player.Time",
    "Player.Duration",
    "Player.Progress",
]

out = []

for label in labels:
    try:
        value = xbmc.getInfoLabel(label)
    except Exception as e:
        value = f"ERROR: {e}"

    out.append(
        f"{label} = {value!r}"
    )

text = "\n".join(out)

with open(
    "/tmp/rnse_airplay_probe.txt",
    "w",
    encoding="utf-8"
) as f:
    f.write(text + "\n")

xbmc.log(
    "RNSE AIRPLAY PROBE\n" + text,
    xbmc.LOGINFO
)
