# Reel recipes (from Nicole's notes, Oct 17 and 20)

What a photographer actually posts. The Assistant offers these as a pick-one; it never invents a format.

| Recipe | What it is | Script |
|---|---|---|
| Behind the scenes into the photos | A talking or behind-the-scenes clip opens (about 3 s, hook on it), then the finished photos land one every two beats. The default when a clip exists. | `--recipe hook-photos` |
| Photo montage | Photos only, one every two beats. The default for a folder of photos. | `--recipe montage` |
| Behind the scenes cut to music | The behind-the-scenes clips chopped into beat-length pieces, spread across each clip. | `--recipe bts` |
| Behind the scenes then photos | Clip pieces on the beat for the first stretch, then the photos. | `--recipe bts-photos` |
| Montage with a client's review over it | Photo montage with the review as the persistent hook text (`--hook-persist`). The review's words only, with the client's OK. | `--recipe montage --hook "..." --hook-persist` |
| The matching moment | The behind-the-scenes second that became a finished photo, cut into the photo. Not built yet. | later |

Pacing: `--beats-per-photo 2` is the calm default (1.2 s per photo at 100 bpm). `1` is fast, `4` is slow. Keep the whole reel under 20 seconds unless they ask.

Text: one short line, cream, centered in the upper third, in their headline font, holding for the opening (Nicole's reel rule). Never on a face: the script keeps text out of the top 250 and bottom 300 pixels, and the grader reports where the text band sits. If the Brand File says otherwise, the Brand File wins.

Trial reels: the same cut with a different hook line each, from the hooks they didn't pick. `--variants hooks.txt`. They go out as trial reels, never to the feed.
