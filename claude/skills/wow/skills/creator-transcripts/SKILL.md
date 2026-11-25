---
name: creator-transcripts
description: Digest recent YouTube videos of content creators (WoW streamers, guide makers, any channel) from their transcripts - strip the filler ("water": intros, drama, hype, opinions, sponsor reads, repeats) and keep only unique, concrete, sourced facts, each with a timestamp link and a verified / contradicted / unverified check. Use when the user wants to know what a creator said without watching, asks "did X say anything useful", or wants a summary of a channel's or video's content.
---

# Creator transcripts → water-free digest

Goal: the user does not want to watch. Give them only what a video adds that is **new, concrete
and checkable**, with a link to the exact second, and say how much of the video was water.

## 1. Find the videos

Resolve the channel ID once by search (handles like `@Name` often point to a different channel):

```bash
yt-dlp "ytsearch6:<creator> <topic>" --flat-playlist --print "%(channel)s | %(channel_url)s | %(title)s"
yt-dlp -I 1:10 --print "%(id)s | %(upload_date)s | %(duration_string)s | %(title)s" \
  "https://www.youtube.com/channel/<UC...>/videos" 2>&1 | grep -v WARNING
```

A creator can have several channels (e.g. main + "TV"/clips) - list them all and ask which
if it is unclear. "Recent" = last 7 days unless the user says otherwise. Show the list with
durations before fetching if it is over ~2 h of video in total.

Known channels: Kargoz `UCxOd0DPfBmSpf70PQe5_MBw`; Solheim Gaming `UCaZhtHB-MqwvMS2YhPRujYQ`,
Solheim TV `UChw8Mq8YdsVk2ty3MPBjUoQ`.

## 2. Get the transcript - Claude in Chrome

`yt-dlp --write-auto-subs` gets HTTP 429 almost always, and caption `baseUrl` fetches return empty,
so use Chrome (load the `chrome-browser` skill, one tab of your own). If YouTube is blocked,
the user has a Chrome policy `block-youtube.json` to move aside (see the WoW repo CLAUDE.md).

Per video, 3 calls:

1. `navigate` to `https://www.youtube.com/watch?v=<id>`
2. `javascript_tool` - opens "Show transcript", merges segments into ~30 s paragraphs, then
   replaces the page body with them (the JS tool truncates results at ~1k chars, `get_page_text`
   does not):

```js
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
document.querySelector('video')?.pause();
let btn=null;
for(let i=0;i<20&&!btn;i++){btn=document.querySelector('ytd-video-description-transcript-section-renderer button'); if(!btn) await sleep(500);}
if(!btn){'NO TRANSCRIPT BUTTON'} else {
  btn.click(); let segs=[];
  for(let i=0;i<40;i++){segs=document.querySelectorAll('transcript-segment-view-model'); if(segs.length) break; await sleep(500);}
  const toS=t=>t.split(':').reduce((a,b)=>a*60+ +b,0); const out=[]; let cur=null;
  for(const s of segs){const t=s.querySelector('[class$=Timestamp]').textContent.trim(), x=s.querySelector('span').textContent.trim();
    if(!cur||toS(t)-cur.s>=30){cur={s:toS(t),t,x:[]}; out.push(cur)} cur.x.push(x)}
  const a=document.createElement('article'); a.style.whiteSpace='pre-wrap';
  a.textContent=document.title.replace(/ - YouTube$/,'')+'\n'+out.map(p=>`[${p.t}] ${p.x.join(' ')}`).join('\n');
  document.body.replaceChildren(a); `ok ${segs.length} segments`
}
```

3. `get_page_text` → the full transcript. (YouTube changes markup: if 0 segments, inspect one
   segment's tag/class tree with a small JS walker - never dump `outerHTML`, the extension blocks
   results that contain cookie/query data.)

Many videos → spread them over subagents (one per channel, each with its own tab, each told to
use this skill and return only the step-3 digest - transcripts must not flood the main context).

## 3. Distill - what is water, what is signal

Drop (water): greetings/outros, "like & subscribe", sponsor reads, self-promo, the creator's
feelings and drama about people, hype adjectives ("INSANE", "BROKEN"), recaps of their older
videos, repeating the same point, speculation without a reason, reaction to someone else's
content (keep only the *facts* that content contains, credited to it), title clickbait.

Keep (signal), each as **one line**:
- concrete numbers: gold/hour, XP/hour, drop rates, prices, levels, timings
- named things: items, NPCs, zones, routes, spells, talents, addons, macros
- mechanics / how-to steps that are reproducible
- news: hotfixes, nerfs, bans, announcements - with the creator's source (patch notes, blue post,
  dev podcast/tweet) if they name one
- a reasoned opinion only if it changes a decision (e.g. "skip X because Y costs Z")

Tag each kept line by source quality:
- `[shown]` - shown on screen / own test with numbers
- `[cited]` - creator names a source (patch notes, blue post, podcast ep.)
- `[claim]` - stated with no source

Then **check reality** (cheap checks first, don't stall on every line):
- prices / gold-per-hour → local auction data (in the WoW repo: `tsm-analyze.py --item`)
- items, drops, dungeons, quests → local addon data (AtlasLoot, ForeverDungeonJournal, Zygor,
  RXP guides) or Wowhead for the game version
- hotfixes, bans, announcements → official source via WebSearch (Blizzard news / blue tracker)
Mark ✅ verified, ❌ contradicted (say by what), ❓ unverified. Never present ❓ as fact.

Deduplicate across videos and creators: the same fact said in 5 videos is one line with all
sources; it is not more true for being repeated. Note disagreements between creators.

## 4. Output (terse, in the user's language)

```
## <Creator> - N videos, Hh Mm total, ~M min of signal
<per topic, most useful first>
- <fact> - [tag] ✅/❌/❓ <check> · [Video short title 4:12](https://youtu.be/<id>?t=252)
### Skippable
<one line per video with nothing new: "title - only drama / repeat of X">
```

Then a short **"For you"** block: which lines matter for the user's current goals (in the WoW
repo: characters and professions from CLAUDE.md and memory), and what to do about them.
Transcripts are auto-captions: names get mangled ("Lionhe Heart" = Lionheart, "Caros" =
Kargoz) - fix obvious ones, mark unsure ones with (?).

Save to the Obsidian vault only if the user asks (gaming topics → `gaming/<Game>/`).
Transcripts stay in the session scratchpad.
