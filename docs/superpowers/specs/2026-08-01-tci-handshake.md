# AetherSDR TCI Handshake — Recorded 2026-08-01

Captured with `not1mm/testing/tci_probe.py` against a live AetherSDR on
`ws://127.0.0.1:50001`. This document is the authority for not1mm's TCI command
mapping; where it disagrees with
`docs/superpowers/specs/2026-08-01-tci-support-design.md`, **this wins**.

## Answers to the five questions from the plan

### 1. Protocol and device

```
device:AetherSDR;
protocol:ExpertSDR3,1.5;
```

AetherSDR speaks **TCI 1.5**, identifying as the ExpertSDR3 dialect.

### 2. modulations_list — TWO corrections

```
modulations_list:usb,lsb,cw,cwr,am,sam,fm,nfm,digu,digl,rtty;
```

**Correction A — the command is `modulations_list`, plural.** The spec assumed
`modulation_list` (singular). Parsing the singular form would silently leave
`get_mode_list()` empty forever, which in turn breaks `Radio.__init__`'s
`cw_list`/`rtty_list` scan at `not1mm/radio.py:64-71`.

**Correction B — the mode set differs from the spec's table:**

| Spec assumed | AetherSDR actually has | Consequence |
|---|---|---|
| — | `cwr` | Missing from the table. Maps to `CWR`, which is already in `Radio.cw_list`. |
| — | `rtty` | Missing. AetherSDR has **native RTTY**, so the spec's `RTTY → digl` remap is wrong and must be removed. |
| `nfm` → `FM` | both `fm` **and** `nfm` | **Collision.** Two TCI modes would map to one not1mm mode, and the reverse map would lose `fm`. |
| `dsb`, `wfm`, `drm` | absent | Harmless — kept in the table for other TCI servers; they simply never appear. |

### 3. Argument order — two different evidence levels

The four commands below do **not** all carry the same weight of evidence.
Only one was ever observed pushed live; the other three are read from the
passive initial state dump alone, across two separate 60-second captures.

**`vfo:` — confirmed as a live push.** 10 `vfo:` frames appear in the first
capture, 2 of them the initial state dump (channel 0 and channel 1) and the
remaining 8 arriving unprompted while the operator turned the dial:

```
vfo:0,0,14193000;          -> vfo:<trx>,<channel>,<hz>
vfo:0,1,14193000;             (channel 1 = VFO B, ignored)
...
vfo:0,0,14043900;
vfo:0,0,14121800;
vfo:0,0,14121900;
...
vfo:0,0,14126000;
```

**`modulation:`, `rx_filter_band:`, `trx:` — argument order read from the
initial state dump only.** None of the three was ever observed as a live
push, across two independent 60-second capture windows:

```
modulation:0,usb;          -> modulation:<trx>,<mode>
rx_filter_band:0,0,2800;   -> rx_filter_band:<trx>,<low>,<high>  (bw = 2800)
trx:0,false;               -> trx:<trx>,<bool>
```

Each appears exactly once in the first capture (the state dump) and exactly
once again in a second, independent capture — `modulation:` 1, `rx_filter_band:`
1, `trx:` 1 — with zero further pushes of any of the three after `start;` in
either window. The argument formats above are unambiguous and not in doubt;
what is unverified is that AetherSDR pushes unsolicited updates for these
three the way it does for `vfo:`.

This is deferred, not blocking: **Task 7 Step 2 verifies mode and filter
sync, and Task 7 Step 3 verifies PTT**, both with the operator present. That
is where live-push behavior for `modulation:`, `rx_filter_band:`, and `trx:`
gets confirmed.

One data point is still useful despite the small sample: `rx_filter_band`
read `0,0,2800` in the first capture and `0,100,2800` in the second — the
low-edge field moved between sessions. That's weak evidence the field is not
static, even though no in-session push was captured. Also note it reported
`0,2800`-style asymmetric edges for USB, not the symmetric `-500,500` the
spec's example assumed; `abs(high - low)` handles both.

### 4. cw_msg — CONFIRMED WORKING 2026-08-01

The probe itself is read-only, so the capture could not exercise this. It was
instead verified end to end from the running application: with **TCI** selected
as the rig backend and **CW via CAT** selected on the CW tab, a CW macro keyed
the live AetherSDR and sent its text.

The signature implemented in `TciCAT.sendcw` is therefore correct as written:

```
cw_msg:0,,,<text>;
```

This was the least-certain line in the implementation, since it was the one
command the read-only probe could never test. It is now settled.

### 5. ready; terminates the handshake — confirmed

`ready;` arrives after the full state dump, followed immediately by `start;`.
Gating `online` on `ready;` is correct.

## Frames to ignore, and why the ignore path matters

The server pushes a large amount of traffic not1mm does not care about. The
raw capture is 339 lines total; excluding the 1-line `--- connected ---`
banner that is 338 frames, of which **279 were `rx_smeter:`** — an S-meter
update roughly every 200 ms.

Ignored commands observed: `rx_smeter`, `dds`, `vfo_limits`, `if_limits`,
`channels_count`, `receive_only`, `rx_enable`, `rit_enable`, `xit_enable`,
`rit_offset`, `xit_offset`, `split_enable`, `lock`, `sql_enable`, `sql_level`,
`agc_mode`, `rx_nb_enable`, `rx_nr_enable`, `rx_anf_enable`, `rx_apf_enable`,
`mute`, `tx_enable`, `drive`, `tune_drive`, `mic_level`, `volume`,
`active_slice`, `audio_samplerate`, `audio_stream_sample_type`,
`audio_stream_channels`, `audio_stream_samples`, `tx_stream_audio_buffering`,
`iq_samplerate`, `trx_count`, `start`.

This confirms the design decision to log unknown frames at **debug** level and
drop them. Logging them at info would flood the log at ~5 lines/second.

## Corrected mode table

This replaces the spec's table. `TCI_TO_NOT1MM_MODE`:

```python
{
    "usb": "USB",
    "lsb": "LSB",
    "cw": "CW",       # in Radio.cw_list
    "cwr": "CWR",     # in Radio.cw_list
    "am": "AM",
    "sam": "SAM",
    "fm": "FM",
    "nfm": "NFM",     # distinct from fm -- must not collide
    "digu": "DIGI-U", # not in Radio.cw_list or Radio.rtty_list -- plain mode
    "digl": "DIGI-L", # in Radio.rtty_list
    "rtty": "RTTY",   # in Radio.rtty_list -- native, do NOT remap to digl
    "dsb": "DSB",     # not on AetherSDR; kept for other TCI servers
    "wfm": "WFM",     # not on AetherSDR
    "drm": "DRM",     # not on AetherSDR
}
```

The reverse map is a plain inversion with **no special cases** — the spec's
`RTTY → digl` and `RTTY-R → digu` entries are deleted, since AetherSDR has
native `rtty`.

## Raw capture

Archived at `.superpowers/sdd/2026-08-01-tci-support/tci-handshake-raw.txt`
(git-ignored scratch). The handshake portion, verbatim:

```
vfo_limits:1000,75000000;
if_limits:-48000,48000;
trx_count:1;
channels_count:2;
device:AetherSDR;
receive_only:false;
modulations_list:usb,lsb,cw,cwr,am,sam,fm,nfm,digu,digl,rtty;
protocol:ExpertSDR3,1.5;
vfo:0,0,14193000;
vfo:0,1,14193000;
dds:0,14176580;
modulation:0,usb;
rx_enable:0,true;
rx_filter_band:0,0,2800;
rit_enable:0,false;
xit_enable:0,false;
rit_offset:0,0;
xit_offset:0,0;
split_enable:0,false;
lock:0,false;
sql_enable:0,false;
sql_level:0,20;
agc_mode:0,fast;
rx_nb_enable:0,false;
rx_nr_enable:0,true;
rx_anf_enable:0,false;
rx_apf_enable:0,false;
mute:0,false;
tx_enable:0,true;
drive:0,60;
tune_drive:0,30;
mic_level:70;
trx:0,false;
volume:-7;
active_slice:0,A;
audio_samplerate:48000;
audio_stream_sample_type:float32;
audio_stream_channels:2;
audio_stream_samples:2048;
tx_stream_audio_buffering:50;
iq_samplerate:48000;
ready;
start;
```
