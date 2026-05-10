# 📜 PT Box — Iterations Log (best-of registry)

> Single chronological registry of every variant tested. Append-only.
> Adoption rule: variant becomes new baseline ONLY if it improves total 5y PnL
> AND passes OOS check (test quarters ≥ 70% positive, retention reasonable).

**Current LIVE baselines:** **e41 BREAKOUT** (5y +3983 / WR 61% / wide SL) + **e44 PULLBACK** (5y +4301 / WR 35% / tight SL — psychology-friendly parallel)
**Toggleable** in Pine v13 via input "Entry Mode" (BREAKOUT default)
**Last updated:** 2026-05-07

---

## 🏆 Hall of Fame (current baseline + supersession chain)

| Order | Variant | Date | 5y Total | Δ Prev | OOS Verdict | Notes |
|---|---|---|---|---|---|---|
| 1 | e37 (v11+) | 2026-05-05 | +1755 | — | PASS 9/10 Q+ | Engine bugfix baseline (post v10→v11 loss accounting fix) |
| 2 | e38 (ATR filter) | 2026-05-05 | +2611 | **+856** | PASS 9/10 Q+ ret 496% | ATR(30d, 30th pctile) — skip calmest 30% of days |
| 3 | e39 (TP boost) | 2026-05-05 | +3121 | **+510** | PASS 9/10 Q+ ret 498% | e38 + TP×1.3 when ATR rank ≥72nd |
| 4 | e40 (NY delay 25m) | 2026-05-05 | +3317 | +196 | PASS 9/10 Q+ ret 526% | e39 + NY entry delayed 25min after box close (skip 8:30-8:55 ET noise) |
| 5 | **e41 (time/SL adj)** | 2026-05-05 | **+3983** | **+666** | PASS 9/10 Q+ ret 560% | e40 + Asia start 19:00 + London SL 0.9×bw + NY end 13 |
| 5b | e42 (entry delay 3 bars) | 2026-05-05 | +4028 | +45 (marginal) | PASS 9/10 Q+ ret 552% | RESEARCH-validated, NOT deployed (saturation) |
| 6 | **e44 (PULLBACK mode — parallel)** | 2026-05-05 | **+4301** | +318 vs e41 | **PASS 10/10 Q+** ret 341% | Tight SL strategy: avg 4.2pt / worst -$74 / WR 35% / **5.8× safer per trade** — Pine toggle deployed |
| 6b | e45 (Pullback + SMC sweep) | 2026-05-06 | +4743 (V4 FVG only) | +442 vs e44 (FAKE) | REJECTED | 6 SMC ideas tested on e44: FVG/strict-pin/prior-box/prior-SR/fib/body-quality. Only V4 FVG total +442 BUT closed PnL collapsed -1233 (EOD M-T-M inflated edge). Same trap as min_SL. NOT deployed. |
| 7 | Phase 16 S1-S10 session-behaviour filter sweep | 2026-05-07 | best -103 vs e41 | ALL 10 FAIL on PnL | REJECTED — saturation Layer 4 | 10 filters tested on e41 baseline: Asia→London/NY level confluence (S1/S2), pre-box OR (S3), pre-box 2h direction (S4), NY chop skip (S5), lowest-25% ATR hour (S6), NY 8-11 ET window (S7), Asia compression amplifier (S8), Asia false-break counter (S9), skip Asia after loss day (S10). Only S6 raises WR+1.3pt and PF+0.09 materially but PnL -22% (-30% trade count). Per-trade expectancy +12% but absolute PnL drops. Filter layer saturation confirmed. e41 baseline UNCHANGED. |
| 8 | Phase 17 BE Trail Sweep | 2026-05-08 | V5 +48 PnL +16.2 WR | NOT auto-deployed | RESEARCH (pending user decision) | 6 BE-trail variants on e44 PB: V1 BE@1R, V2 BE@0.5R, V3 BE+1pt@1R, V4 BE@1.5R, V5 TRAIL+1R then trail (⭐ winner), V6 BE@box-edge. V5 = +48 PnL / +16.2pt WR (34.9→51.2%) / worst trade unchanged. V6 = +307 PnL but WR collapse -21pt. V2 catastrophic -902. Trade count V5 +1360 because BE exit free up max=5 slots. Pine port effort 2-3 jam if user gas. e44 baseline UNCHANGED. |
| 9 | Phase 18 EOD Impact Analysis | 2026-05-08 | structural insight | DOCUMENTATION | STRUCTURAL EDGE confirmed | 3 scenarios: A=current (EOD force-close ON, +4301), B=drop EOD trades analytical (+1966, -2334), C=extend session 23:59 ET no force-close (+3485, -816). EOD kontribusi 54% e44 PnL. Asia closed-only NEGATIF -19 → full Asia edge dari EOD M-T-M. Force-close BUKAN bug, STRUCTURAL EDGE. Live trader wajib manual close di session-end. Dashboard claim e41/e44 baseline include EOD M-T-M. Natural resolution number = $1,394/yr vs claimed $1,720/yr (-19%). Pine `forceSessionEndClose` lines 663-688 essential. |
| 10 | Phase 19 Loss Forensic Analysis | 2026-05-08 | 5 hypothesis skip rules | RESEARCH (validation pending) | DATA-DRIVEN INSIGHT | Forensic 3,807 losing trades 5y e44 PB. Top finding: Trade Duration = predictor #1 (Flash <5min=82.2% loss, Quick 5-15min=73.5%, Grind >60min=43.6% LOSS = 56% WIN). Tight SL PARADOX (3-5pt=59.6% loss vs Wide 8-12pt=45.4% loss — counter-intuitive). Hour 8 ET = WORST 62.7% loss (NY pre-8:30 macro trap). COUNTER pre-box trend = 59.7% loss vs ALIGNED 56%. Februari = 62.9% loss month (Q1 Fed/CPI). Loss avg -3.73pt, P95 worst -7.98pt, max -36.9pt. 72.5% days ada ≥3 losses (multi-loss day NORMAL). 5 hypothesis skip rules surfaced (hold ≥60min, skip 8ET, skip counter-trend, avoid narrow box 5-10pt, Feb cautious) PENDING validation — Phase 16 caveat (filter sweep mostly fails). Pine UNCHANGED. |
| 11 | Phase 20 Candle Pattern Visual Forensic | 2026-05-08 | 4 hypothesis (B strongest -25.8pt skew) | RESEARCH | VISUAL DECODED | Deep M1 candle anatomy + multi-TF trend per trade. Top split: max counter 5-bar > 3pt = 81% LOSS RATE (n=738) HUGE skew. Bar+1 favor positive = WR 48% vs negative 36% (12pt diff). LOSS pattern = weak entry candle (random body%) + instant counter bar+1 + max counter avg 1.79pt. WIN pattern = strong body entry candle (60% top winners >70% body) + immediate favor bar+1 + max counter avg 0.97pt. D1 same-day align tipis material (+0.92pt skew). HTF M15/H1 align essentially tied. Worst-30 100% SL with weak body + counter context. 4 hypothesis surfaced — Phase 21 validation FAILED. Pine UNCHANGED. |
| 12 | Phase 21 Early-Exit Sweep | 2026-05-08 | best B4 -541 PnL | ALL 6 FAIL — REJECTED | 4× IRON LAW CONFIRMED | Validation Phase 20 hypothesis B (cut early on counter movement). 6 variants: B1 cut bar+5 counter>3pt (-939), B2 bar+3>3pt (-763), B3 bar+5>2pt (-1235), B4 bar+5>4pt (-541), B5 bar+1>1pt (-1491), B6 combo (-1594). ALL drop PnL. Reason: filter cut WIN trades juga (counter recovery to TP). B1 decompose: save 425 from full SL (+2125pts) but lose 167 winners (-1670pts), early-exit aggregate -1633pts. Net -939. **4× IRON LAW**: e23 DoW skip + Phase 16 S1-S10 + e45 SMC + Phase 21 early-exit ALL fail same pattern. Descriptive statistical skew ≠ exploitable forward filter. Trigger context: user pain $50 London 3-attempt 2026-05-08 = bad cluster (3.5× normal drag, 3-day sample too small), NOT system defect. Recommend: stop trade hari ini, equity protection -15% drawdown halt, lot reduction streak loss, mode switch e44↔e41 variety. Pine UNCHANGED. |
| 13 | Phase 22 NFP/CPI/FOMC Day Impact | 2026-05-08 | NFP +7.68 pts/day (1.78× normal) | ACTIONABLE INSIGHT | DOCUMENTATION | Macro release day analysis 5y. NFP = paling profitable day-type (+7.68 pts/day vs normal +4.31). NY NFP WR 48.2% vs normal 41.3%. NY hour 10-11 ET = 60% WR sweet spot. Hour 9 ET avoid (37.5% WR transition noise). Worst-ever NFP single trade -$37 at 0.02 lot. Skip-NFP filter LOSES -78pts/yr. Last 6 NFP days 5/6 strongly profitable (avg +41.3 pts/day). CPI ~13th = +5.50 pts/day (1.28×). FOMC = +2.24 pts/day (0.52× — worst). Trigger: tonight 8 May 2026 = NFP. Recommend trade NFP, NY hour 10-11 priority. Pine UNCHANGED. |
| 14 | Live Journal 2026-05-08 Whipsaw Day | 2026-05-08 | -$49.25 actual loss user real broker | LIVE GROUND TRUTH | CASE STUDY | Real broker trade record user pain. 3 consecutive trades London/NY-pre, all SL: T1 06:00 BUY 4726→4717 -$17.23, T2 07:13 BUY 4725→4717 -$15.21, T3 08:20 SELL 4707→4715 -$16.81. Pattern = WHIPSAW (BUY-BUY-SELL traps). Loss/trade -8.2pt vs 5y avg -3.73pt = 2.2× wider. P95-P99 worst-day distribution. Same tier as Phase 19 worst-30 signature (Feb 2026 cluster). Bukan unprecedented (worst NFP day ever -20.9pt 2024-10-04). User context: validation day 2, sample 16 trades = TOO SMALL judge. Mental: NOT system defect, NOT bug — chop regime day. Documented to vault Live-Journal/ + dashboard new page Live Journal (page 6). Pine UNCHANGED. |
| 15 | Phase 23 EURUSD Multi-Asset Port (5y apple-to-apple) | 2026-05-09 | +2,317 pips 5y / +434 pips/yr | EDGE TRANSFER WEAK | MULTI-ASSET VALIDATION | EURUSD 5y M1 backtest port e44 PB SAME period as gold (2021-01-04 → 2026-05-08). Apply same rules: e38 ATR + e39 TP boost + e40 NY delay + e41 session params. Result: edge POSITIVE tapi LEMAH vs gold. PF ~1.05 vs gold 1.30. WR 36.5% vs gold 42.1%. Per-session: NY +2150 pips dominant (PF 1.19), London +70 NEAR-ZERO (PF 1.01, degrading post-2020), Asia +96 marginal (PF 1.03). Capital efficiency: gold $200=$1720/yr (860%) vs EURUSD $1K=$434/yr (43%). Gold 2× per-yr at standard lot. For user $200 capital: gold remains primary. EURUSD viable kalau capital scale ke $1K+ NY-only (skip Asia + London — marginal di 5y window). Dashboard cleanup: rename pages (resolve 4_ duplicate prefix), add Multi-Asset page (7), update home with multi-asset hero + recent phases timeline + 7-rule constraints. Pine UNCHANGED. |
| 16 | Phase 24 Asia BO + Tight SL Sweep (Hybrid Concept) | 2026-05-09 | V2 winner +664 (vs e44 +572), worst -$10 (vs e44 -$74) | RESEARCH (per-session optimization) | HYBRID FIRST PROOF | User concept: Asia e41 BREAKOUT entry + tight SL fixed cap (e44-style). 8 SL variants tested on Asia 5y. Variants: V0 (e41 0.7×bw), V1-V5 (fixed 4-8pt), V6-V8 (proportional 0.3-0.5×bw). WINNER V2 fixed 5pt SL: +664 PnL (+16% vs e44 PB Asia +572) + WR 47.4% (+3.3pt) + worst trade -$10 (7.4× safer than e44 -$74). Mental gain HUGE: Asia worst-trade drama drop 86%. Proportional SL exposed to wide-box outliers (-$88 to -$147 worst). Fixed-pt = mental cap. V1 too tight (whipsaw drop), V3-V5 over-cushion. V2 sweet spot. Hybrid SCENARIO 9 = V2 Asia + e44 London + e44 NY = +4393 vs e44 ALL +4301 (+92 modest). Pending: London + NY same-style sweep, Pine v14 per-session entry-mode patch. Pine UNCHANGED. |
| 17 | Phase 25 M5 Multi-TF Backtest | 2026-05-09 | M5 +3677 vs M1 +4301 | NOT adopt | RESEARCH | M1 → M5 resample test e44 PB. M5 result mixed: WR +2.3pt better (44.4% vs 42.1%) BUT total PnL -624 lower AND worst trade -$203 vs -$74 (2.7× WORSE). Per-session: Asia M5 WR 48.9% best, NY M5 worst trade -$203 scary. Asumsi M5 less noise = better WR confirmed. Asumsi M5 better total PnL = FALSE (M5 fewer EOD trades). Asumsi M5 safer = FALSE (wider bars = wider SL). Score 6.4/10 vs M1 8.0/10. NOT deploy standalone (lower PnL). NOT deploy paralel (mental load 2× + worst-trade drama). M5 useful kalau capital scale $5K+ untuk paralel lot 0.01. Pine UNCHANGED. |
| 18 | Phase 26 Max Attempt × Spread Optimization | 2026-05-09 | max=5 OPTIMAL all tiers | DOCUMENTATION | KEY INSIGHT | Max attempt sweep (1-5) × Exness tier (Pro/Raw/Zero) net income calc. COUNTER-INTUITIVE finding: max=5 STILL OPTIMAL across ALL tiers. Cutting attempts = WORSE net (-$99 to -$583). Why: Phase 17 finding later attempts higher WR (46.1% at 5 vs 39.9% at 1), system filters to higher-quality, EOD edge needs volume, spread saving < gross PnL loss. Real solution = SWITCH BROKER TIER not reduce attempts. Pro $887/yr → Raw $1310/yr (+$423) → Zero $1516/yr (+$629) (initial estimate, see Phase 27 verified). Pine LIVE: max=5 already optimal, UNCHANGED. |
| 19 | Phase 27 Exness Spread Reality Check | 2026-05-09 | Pro real spread $0.10-0.20 (not $0.30) | DOCUMENTATION | REALISM UPDATE | User asked verify spread (market closed weekend). Web search Exness 2026 May. Real numbers: Standard 20-35 pips, Pro 1.1-1.6 pips ($0.022-0.32 range), Raw 0+$3.50/lot/side ($0.14/trade), Zero near-0+$2.50-5/side ($0.10-0.20/trade). My initial $0.30 Pro estimate LIKELY HIGH. Pro real spread $0.10-0.20/trade likely. Tier switch advantage TIPIS ($0-200/yr) instead of $629 claim Phase 26. Revised Pro net income range $1,150-1,545/yr (575-770% return) vs initial $887. User WAJIB verify live spread di Exness app for definitive cost. Pine UNCHANGED. |
| 20 | Phase 28 Entry-to-SL Bar Progression | 2026-05-09 | SLOW_GRIND #1 loss (47.5%), V_SHAPE_FAIL 19.2% | RESEARCH | LOSS PATTERN DECODE | Bar-by-bar trace ALL 6,567 trades from entry to exit. Classify 7 patterns. SLOW_GRIND = #1 loss killer (47.5%, median 41 bars drift). V_SHAPE_FAIL = 19.2% (hit +1R favor first → reverse to SL = BE Trail target). 60.3% of SL hits take >20 bars (slow not flash). Validates Phase 17 V5 BE Trail concept (650 V_SHAPE save potential). Pine UNCHANGED. |
| 21 | Phase 29 SLOW_GRIND Filter Sweep | 2026-05-09 | best T7 +$10/yr (statistically zero) | ALL FAIL — 5× IRON LAW | REJECTED | 7 time-cap exit variants tested. Variants: T1 (b30 c2 f1) -70, T2 (b20 c1.5 f1) -78, T3 (b40 c2) -323, T4 (b30 f0.5) -2, T5 (b25 c2 f1.5) -43, T6 (b15 c1.5 f1) -153, T7 (b45 c2.5 f1) +10. ALL near-neutral or negative. **5× iron law**: e23 + Phase 16 + e45 + Phase 21 + Phase 29 ALL fail same pattern. Filter cuts winners equally as losses. Pine UNCHANGED. |
| 22 | Phase 30 Loss Clustering Research | 2026-05-09 | loss streaks RANDOM | DOCUMENTATION | STRUCTURAL INSIGHT | Statistical loss STRUCTURE research. Loss streaks RANDOM no autocorrelation (after 5 consec next WR same as baseline 42%). "Stop after N losses" = MYTH. Min 25 ET worst loss density 64.7%. Round numbers HELP not hurt (54% loss vs 58% farther). Day-after-loss mild drag -2pts/day. Same-day post-loss next session BETTER (mean reversion). Mental rules surfaced, no deployable filter. Pine UNCHANGED. |
| 23 | Phase 31 Mentor 5min Box Test | 2026-05-09 | Mentor approach -75% PnL | REJECTED | MENTOR TEST | User mentor approach (5min box + SL hard cap 3pt + TP fixed 6pt). 6 box durations tested (5/15/30/45/60/90). ALL FAIL — best 60min +1106 vs baseline +4301 (-75% PnL). SL cap skip 50% setups. Tight SL = whipsaw, WR 42→28%. Worst trade -$3 mental cap but income hancur. 60min sweet spot already optimal. Mentor manual discretion ≠ algorithmic backtest reality. Pine UNCHANGED. |
| 24 | Phase 32 WIN vs LOSS Pattern Compare | 2026-05-09 | pre-entry WEAK (Cohen d <0.15) | RESEARCH | PRODUCT-ITERATION APPROACH | Extract 19 features per trade, compare WIN vs LOSS distribution. ALL pre-entry features Cohen d <0.15 (WEAK predictors). Counter-intuitions: SL ≥5pt = +5.6pt WR, dist <3pt to $50 round = +4.3pt WR, D1 aligned +4.2pt, attempt #≥2 +3.7pt. POST-ENTRY signals STRONG (Cohen d 0.27-0.37) but Phase 21 confirmed cuts winners equally. Filter saturated via feature overlap. Pine UNCHANGED. |
| 25 | Phase 33 Candle Pattern Classifier | 2026-05-09 | spread best/worst pattern 5.7pt | RESEARCH | CANDLE ANATOMY | Classify entry bar 12+ patterns. Distribution: PIN ALIGNED 27.5% WR 41.7%, DOJI 24.9% WR 43.4%, ENGULF 21.6% WR 40.1%, MARUBOZU 11.8% WR 43.8% TOP, INSIDE_BAR 2.4% WR 38.1% WORST. Spread 5.7pt = filter alone tidak material. PIN BAR overrated, DOJI underrated, MARUBOZU best, INSIDE_BAR worst. Pine UNCHANGED. |
| 26 | Phase 34 Mentor LuxAlgo Sessions | 2026-05-09 | PT Box current win all sessions | REJECTED | MENTOR TEST | User mentor LuxAlgo TradingView sessions test (Asia 17-24, London 3-7, NY 8-12 ET). Apple-to-apple TOTAL PnL: PT Box CURRENT WIN ALL 3 sessions. Asia +382 vs +572, London +278 vs +1307, NY +1182 vs +2422. Total mentor +1842 vs PT Box +4301 = -$2459. Mentor's tighter windows = less EOD M-T-M edge captured (Phase 18: 54% PnL from EOD). Different paradigm: mentor manual discretion vs PT Box algorithmic full-session capture. Pine UNCHANGED. |
| 27 | Phase 35 24h No-Session PT Box | 2026-05-09 | V6 +$1,072/yr extra IF Zero account | CONDITIONAL WIN | INSIGHT | Test PT Box rules WITHOUT session constraint. 6 variants. GROSS PnL: 3 of 6 WIN vs current (V4 +$2943, V5 +$274, V6 +$3602 best). NET after Pro spread ($0.60/trade): ALL LOSE (V6 +$1812 net vs current +$4658 = LOSE -$2846). Switch Zero account ($0.11/trade): V6 24h becomes BIG WIN (+$13240 vs current +$7879 = +$5361/5y = +$1072/yr extra). Conditional deploy IF + only IF Zero account adopted. **KEY INSIGHT**: PT Box session constraint = HIDDEN SPREAD MANAGEMENT. Pro→Zero+24h = $2648/yr (+185% income vs current $932). Pine UNCHANGED. |
| 28 | Phase 36 Cap SL ≤5pt + Bigger TP | 2026-05-10 | Cap5 RR 1:4 = best capped (-$1,285) | REJECTED | TRADE-OFF TEST | User concept: cap SL ≤5pt safety + naikin TP ratio recover income. 7 RR variants tested (1:2 to 1:10). ALL capped LOSE vs baseline +4523. Best capped RR 1:4 = +3238 (-$1285). WR drop dramatic (39.8% → 32.9% di RR 1:10). Sweet spot RR 1:4 partial mitigate, ga full recover. Mental: capped GUARANTEED worst -$10 but income -$514/yr + WR mental shock. Per Phase 32: wider SL setups = higher quality structural trades. Cap removes high-quality. STAY baseline no-cap RR 1:2. Pine UNCHANGED. |
| 29 | Phase 37 Post-Entry Trajectory | 2026-05-10 | 12 categories classified | RESEARCH | TRAJECTORY DECODE | Trace post-entry first 5 bars (M1 = tick proxy) untuk 6,574 trades. Classify 12 categories. Findings: NO_MOVE 48.4% HUGE (half trades sit di entry zone first 5 bars, 37% WR slow chop), A_CLEAN_RUN_to_TP 10.4% (best +$9.44 avg), B_PROFIT_RETRACE 9.7% (WR 49.5% recover), C1_PROFIT_FLIP_to_SL 6.6% (62.6% of flips kena SL), C2_PROFIT_FLIP_to_TP 2.6% (+$14.77 best!), D1_INSTANT_COUNTER_to_SL 6.6% (73.8% of instant counter kena SL), D2_INSTANT_COUNTER_to_TP 1.3% (+$9.81 recovery). Bar+1 favor positive = +12pt WR boost. Bar+1 counter ≥1pt = 73.8% SL signal. Filter NOT exploitable forward (Phase 21 cut-on-counter already failed). Mental real-time awareness > algorithmic filter. Pine UNCHANGED. |
| 30 | Phase 38 Regime Split (Trump-2 Era) | 2026-05-10 | Full 12-cat matrix per year (sums 100%) | INSIGHT | REGIME SHIFT | Yearly split Phase 37 trajectory (2021-2026). MAJOR regime shift Biden→Trump-2. NO_MOVE collapse 60.4%→19.4% (-41pp 🔻 chop dead). FLIP→SL surge 3.1%→15.1% (+12pp 🔺 whipsaw 5×). CLEAN→TP boost 8.1%→15.8% (+7.7pp 🔺 trend 2×). INSTANT→SL up 4.3%→11.9% (+7.6pp). Income jump $605/yr (2021) → $2850/yr (2025) → $2481 in 3.3mo 2026 = ~$10K/yr run-rate. **Trump-2 mental matrix per 10 trades**: 1.6 CLEAN→TP win + 1.5 FLIP→SL pain + 1.4 PROFIT_RETRACE + 1.2 INSTANT→SL + 0.9 CLEAN→SL + 1.9 NO_MOVE + 0.6 FLIP→TP recovery (rare +$34!) + others. Geopolitical overlay: tantrum tweet → INSTANT+CLEAN binary; war escalation → CLEAN→TP gold safe-haven; mental skip headlines escalate, NOT systematic filter (5× iron law). User 2026-05-08 -$49 cluster = NORMAL Trump-era P75-P85, BUKAN system defect. Pine UNCHANGED. |
| 31 | Pine v14 BE TRAIL DEPLOYED | 2026-05-10 | WR 34.9%→51.2% (+16.2pt) | LIVE PRODUCTION | DEPLOY | First BE Trail ever to Pine production. Phase 17 V5 winner stacked on e44 PB. Mechanic: trade reach +1×R favor → SL pindah ke entry (BE). After BE armed → SL trail running max(high)/min(low) by sl_distance. Exit reason logged 3 jenis: BE (sl~=entry, $0 loss), TRAIL (sl past entry, locked profit), SL (never armed). Backtest 5y: WR 34.9%→51.2% (+16.2pt 🚀), PnL +$4301→+$4349 (+$48), worst trade SAMA -$74. New inputs: useBeTrail (default true), beTriggerR (default 1.0), beShowTrailLine (default true). Trade struct +3 fields (slOrig/beTriggered/runExtreme). All 10 Trade.new calls updated. Visual: SL line bergerak real-time saat trail; exit marker baru 🛡️BE (aqua) / 🎯TRAIL (aqua). Mental impact MASSIVE — profit ga balik ke loss lagi. User context (gaji Dash 9jt/bulan, modal kecil): BE Trail = safest upgrade ZERO extra risk. Trump-2 era boost estimated ~$2K/yr via FLIP→SL saves (Phase 38 finding: PROFIT_FLIP_to_SL surge 3.1%→15.1%). Phase 7 dashboard header sync v13→v14. Vault doc + memory + canonical updated. User wait 2-4 minggu live validation sebelum stack V2 Asia / Compound / lot bump. |
| 32 | MT5 EA v14.1 — Pine parity | 2026-05-10 | 95% Pine v14 parity, 528 lines | LIVE PRODUCTION | DEPLOY | Standalone MT5 EA mirroring Pine v14 BE Trail logic. v14.0 fix: ArrayInitialize struct compile error, UpdateBox race condition, ETDayOfMonth boundary. v14.1 parity: maxAttempt 1→5 (was missing 80% setups), ATR filter (e38 skip <30th pctile), TP boost (e39 1.3× when ATR ≥72), NY delay 25min (e40), pattern detection expanded (engulf+pin+hammer+inside vs engulf+pin), per-day ATR cache. Reflection setup: 3 modes (Standalone recommended, Manual mirror free, PineConnector $5-19/mo). User pakai Standalone — Pine + MT5 jalan parallel same logic, $0 cost, no latency. Live Deploy dashboard sync (header + status badge + MT5 EA tag). Setup vault doc dengan troubleshooting + risk disclaimer (test demo 3 sesi sebelum live attach). |
| 33 | Phase 39 Compound Sizing REJECTED | 2026-05-10 | 8 variants ALL fail Phase A gate | RESEARCH | REJECTED | Opsi B engine sim (3 win → tier 0.03, loss reset) + 7 variants. ALL fail PnL Δ ≥ +30% gate. BEST = Opsi B global streak +2.2% ($37/yr extra). Tier-up rare karena P(3 consecutive wins WR 42%) = 0.42³ = 7.4% per cluster. Memo iterasi 2026-05-07 estimate +50% SALAH (assumed every 3rd triggers immediate, ignored streak rarity). 6× IRON LAW confirmed (e23/P16/e45/P21/P29/P39). DO NOT touch Pine for compound. Real income paths: bump lot 0.02→0.03 (+$860/yr, worst -$111), Pro→Zero account switch (+$370-700/yr), V2 Asia Tight SL (+$92/yr + 86% safer worst), BE Trail v14 deployed (+$48/yr + WR 35→51%). Pine UNCHANGED. |
| 34 | Pine v15 V2 Asia Tight SL DEPLOYED | 2026-05-10 | Asia worst -$74→-$10 (86% safer) | LIVE PRODUCTION | DEPLOY | Phase 24 V2 Asia Tight SL stacked on Pine v14. Asia entry mode toggle: asiaUseTightSlBO (default ON). Mechanic: Asia direct breakout (close > boxHi) + fixed 5pt SL + TP 10pt (1:2 RR). London + NY tetap PB unchanged. BE Trail v14 still applies. Backtest 5y: Asia +664 vs +572 PB (+$92), worst trade -$10 vs -$74 (7.4× safer), WR ~37% similar. Mental impact modal $115: Asia worst was -$74=64% balance, sekarang -$10=9% balance. Drama drop 86%. Per-session entry mode wrapped via toggle gate. Indicator title v15. Stats panel slimmed (14→9 rows) + BE/Trail row added. |
| 35 | Phase 40 Stop Rules Backtest | 2026-05-10 | 11 stop variants tested vs baseline | RESEARCH | INSIGHT | Test stop discipline rules against 5y backtest. Baseline +$1,720/yr. Weekly -$100 BEST (-2% only, lose $35/yr). Daily -$50 OK (-7%). Daily -$30 too tight (-23%). Max 3 consec loss DISASTER (-39%). Max 5 consec loss bad (-9.5% AND worst day GETS WORSE -$156 vs -$130). FLIP SKIP REJECTED -31% (gua suggest tadi WRONG, worst day actually -$209 worse). 7× IRON LAW confirmed. Final plan modal $115 lot 0.01: daily stop -$25, weekly stop -$50, no consec rule, no flip skip. Cost ~10% income drag, benefit modal preservation. Vault note Phase 40 + live plan modal kecil saved. Schedule WIB Asia 07:30-11:00 pagi, London 12:00-19:00 siang, NY 19:25-24:00 malam. ETA $115→$1000 = 6-8 bulan. Pine UNCHANGED. |
| 36 | Phase 42 Wider TP Sweep REJECTED | 2026-05-10 | 7 TP mult 1:2 to 1:8 vs current | RESEARCH | REJECTED | User asked "what if TP dilebarin?" Test wider TP with BE Trail v14 active. ALL wider variants LOSE: TP 1:3 -$426/yr, TP 1:5 -$599/yr, TP 1:8 -$616/yr. TP hit rate collapse 15.6%→4.4%→1.2%→0.3%→0%. Reason: Gold M1 jarang gerak >3R sebelum reverse. Wider TP = trade hampir never hit TP, jadi trail exit dominan. Trail captures LESS than 1:2 TP would have given (max reward lost). Confirms Phase 36 pattern (cap SL + bigger TP also failed). TP 1:2 OPTIMAL config confirmed. Kill list updated (8 dead variants total): Wider TP, Cap SL ≤5pt, Tighter SL <3pt, Compound sizing, Filter sweeps (3×), Max consec/flip skip stop. Pine UNCHANGED. |

---

## 📊 Full Registry — every variant tested

Sorted by 5y total PnL. ⭐ = adopted as baseline. ✓ = improvement vs e37 baseline. ✗ = regression.

| Variant | Description | 5y Total | 5y Closed | Trades | WR | Status |
|---|---|---|---|---|---|---|
| **e41** | e40 + Asia 19:00 + London SL 0.9 + NY end 13 | **+3983** | +4145 | 1589 | 60.9% | ⭐ CURRENT |
| e41_min_sl_7 | min SL 7pt — APPEARED HUGE +546 but ARTIFACT | +3863 | +1642 | 803 | 49.8% | ⚠️ rejected (closed PnL -1846, EOD inflated) |
| e41_asia_start_19_only | Asia start 19:00 alone | +3794 | +3919 | 1700 | 62.0% | ✓ component |
| e41_min_sl_5 | min SL 5pt — same artifact pattern | +3706 | +2892 | 1191 | 55.6% | ⚠️ rejected |
| e41_london_sl_0.9_only | London SL 0.9 alone | +3449 | +3594 | 1689 | 59.6% | ✓ component |
| e40 | e39 + NY entry delay 25 min | +3317 | +3488 | 1740 | 60.9% | superseded by e41 |
| e40_ny_delay_30 | e39 + NY entry delay 30 min | +3277 | +3560 | 1733 | 61.3% | runner-up |
| e40_ny_delay_35 | e39 + NY entry delay 35 min | +3222 | +3518 | 1726 | 61.4% | ✓ |
| e39 | e38 + TP×1.3 on ATR ≥ 72nd pctile | +3121 | +3307 | 1766 | 60.1% | superseded by e40 |
| e39_b_tp65x1.30 | e38 + TP×1.3 on ATR ≥ 65th | +3112 | +3265 | 1742 | 59.3% | runner-up |
| e39_b_tp70x1.30 | e38 + TP×1.3 on ATR ≥ 70th | +3113 | +3280 | 1755 | 59.7% | runner-up |
| e39_b_tp75x1.30 | e38 + TP×1.3 on ATR ≥ 75th | +3072 | +3326 | 1775 | 60.3% | ✓ |
| e39_b_tp80x1.30 | e38 + TP×1.3 on ATR ≥ 80th | +3063 | +3385 | 1788 | 60.9% | ✓ |
| e39_b_tp70x1.20 | e38 + TP×1.2 on ATR ≥ 70th | +3038 | +3461 | 1788 | 60.9% | ✓ |
| **e38** | e37 + ATR(30d, 30th pctile) filter | **+2611** | +3540 | 1868 | 63.1% | superseded by e39 |
| atr_filter_30d_50th | ATR(30d, median) — pre-tune | +2394 | +3104 | 1409 | 63.9% | ✓ but suboptimal |
| atr_filter_20d_30th | ATR(20d, 30th) — pre-tune | +2542 | +3457 | 1834 | 63.2% | ✓ |
| e39_c_cooldown | e38 + cooldown after 2 losses | +2611 | +3540 | 1868 | 63.1% | NEUTRAL (rare trigger) |
| e39_d_trend_stacked | e38 + D1 SMA20 directional bias | +2404 | +2849 | 1341 | 66.2% | ✗ over-filtered |
| e37_trend_only | D1 SMA20 trend filter alone | +1718 | +3149 | 2391 | 60.1% | ≈ baseline |
| eod_cap_180min | Force exit after 180 min | +1600 | +3424 | 2040 | 61.6% | ✗ kills runners |
| **e37** | v11+ engine canonical (no filter) | **+1755** | +3223 | 2433 | 60.2% | base reference |
| volume_filter | tickvol > rolling 20d threshold | +1450 | +2675 | 1418 | 62.3% | ✗ noise > signal |
| e39_e_box_bias | Intra-box HH-HL/LL-LH structure | +1363 | +2110 | 1442 | 62.1% | ✗ over-filtered |
| eod_cap_120min | Force exit after 120 min | +1265 | +3197 | 1570 | 63.0% | ✗ |
| eod_cap_90min | Force exit after 90 min | +1024 | +3030 | 1202 | 65.5% | ✗ |
| box_quality_filter | Skip days with width > 2× rolling | +1052 | +1998 | 2291 | 59.3% | ✗ NY hardest hit |
| e39_a_per_session_atr | Per-session ATR(20d, 30th) | +1469 | +2818 | 1588 | 62.5% | ✗ daily ATR > per-session |
| eod_cap_60min | Force exit after 60 min | +989 | +3077 | 764 | 72.8% | ✗ worst (high WR but low N) |
| atr_low_control | ATR < median (control test) | -619 | +193 | 1085 | 55.4% | ✓ confirms ATR signal direction |

---

## 🎯 Lessons learned (what worked vs what didn't)

### What worked ✅
1. **Daily ATR regime filter** (e38) — single biggest gain (+856). Skip calm days.
2. **Asymmetric TP per ATR** (e39) — wider TP on high-vol days reduces EOD drag dramatically.
3. **Engine bugfix** (v10→v11) — loss accounting fix corrected +9084 inflated → +3223 true.
4. **Stability cluster around 65-75th × 1.30 TP** — optimum is robust, not curve-fit.

### Tier-5 ENTRY TRIGGER SATURATION (added 2026-05-05)
15 entry-trigger refinements tested on e41 baseline (+3983):

**Adopted/marginal:**
- Wait 3 M1 bars after first break: Δ +45 (research-validated, NOT live-deployed)
- Wait 1 bar: Δ +10
- Hold 2 closes beyond box: Δ +1 (neutral)

**FAILED:**
- Pullback entry (require retest): **-1116** (system designed for first break)
- Second break (break → retrace → break again): **-2067** (worst — by-the-time-double-break, move is over)
- Wait 5+ bars after first break: -187 to -997 (too much delay misses move)
- Engulfing only (drop pin + inside): -1102 (drops too many valid trades)
- Pin only: -452
- Strong body ≥70%: -740 (conflicts with pin detection ≤30%)
- Close in top/bottom 20%: -782
- Close > box + 0.2 to 0.5×bw push: -299 to -977 (require stronger break = miss good ones)
- 3-bar HH-HL momentum into break: -476 (counter-momentum entries actually profitable)

**Lesson — entry trigger SATURATION:** PT box system already enters at near-optimal moment (immediate breakout + body-% + any-of-3-patterns). Refining entry timing/quality further hits diminishing returns or hurts. The edge is in **REGIME + RISK + TIMING + SL**, not entry sophistication.

**Future direction:** Position sizing, walk-forward param refresh, multi-symbol portfolio, cost-aware filters.

### e45 PULLBACK + SMC sweep — REJECTED despite total improvement (added 2026-05-06)
6 SMC enhancements stacked on e44 pullback:
- **V4 FVG retest**: total +4743 (Δ +442 vs e44) — looked best BUT closed PnL collapsed -1233 (EOD M-T-M inflated +1790)
- **V1b close-extreme**: total +4133 (Δ -61) ≈ neutral
- **V5 fib retest** (38.2%/50%/61.8%/78.6%): -186 to -578
- **V6 breakout body filter** (≥40-70%): -236 to -574
- **V1a strict pin only**: -693
- **V3 prior session S/R confluence**: -1167
- **V2 prior session box S/D confluence**: -1269

**Verdict:** All 6 ideas REJECTED. V4 FVG looked great by total PnL but **closed-edge collapsed** — same trap as min_SL Tier-4. Live execution can't reliably capture EOD M-T-M drift with manual orders. Final stack stays e41 BREAKOUT + e44 PULLBACK toggle.

**Lesson — closed PnL is the truth.** Total PnL with EOD inflation = brittle. Backtest must check closed-only edge separately.

### Phase 16 — S1-S10 Session-Behaviour Filter Sweep — ALL 10 FAIL (added 2026-05-07)
10 filters tested on e41 baseline (5y closed PnL, harness `scripts/run_S_filter_sweep.py`):

| Filter | Δ PnL | Δ WR | Δ PF | Note |
|--------|------:|-----:|-----:|------|
| S1 Asia H/L → London/NY ±5pt confluence | -1854 | -0.7 | +0.02 | over-filter |
| S2 London H/L → NY ±5pt confluence | -623 | -0.4 | +0.03 | meh |
| S3 Box breaks pre-box 15min OR | -1000 | -0.7 | -0.05 | bad |
| S4 Pre-box 2h direction align | -759 | 0.0 | +0.03 | meh |
| S5 Skip NY if Asia+London chop | -103 | +0.2 | +0.01 | near-neutral |
| **S6 Skip lowest-25% ATR hour bucket** | -894 | **+1.3** | **+0.09** | only WR/PF improver, per-trade exp +12% |
| S7 NY entry 8-11 ET overlap only | -125 | -0.1 | -0.02 | neutral |
| S8 Asia tight (<12pt) → London/NY | -2417 | -1.7 | -0.11 | wrong theory |
| S9 Asia false-break counter direction | -765 | -0.5 | +0.01 | meh |
| S10 Skip Asia after loss day | -348 | -0.3 | -0.03 | meh |

**Verdict:** No PnL improvement. S6 is sole material WR/PF improver but trade count -30% means absolute PnL drops -22%. **Filter-on-top layer saturation confirmed.** e41 baseline UNCHANGED. Not deployed. Vault: [[Phase-16-S1-S10-Filter-Sweep]].

**Insight:** PT box edge is in REGIME (e38) + RISK (e39 TP boost) + TIMING (e40 NY delay, e41 Asia/London/NY tuning) + SL CALIBRATION (e41 London 0.9). Layer 4 (filter on-top) does not add edge. Saturation across all 4 layers now confirmed.

### Phase 17 — BE Trail Sweep on e44 PB (added 2026-05-08)
6 breakeven-trail variants tested on e44 PULLBACK 5y baseline (engine-internal reference: closed-only +1,966 / 5,203 trades / WR 34.9%):

| Variant | Δ PnL | Δ WR | Worst | Note |
|---------|------:|-----:|------:|------|
| V1 BE @ +1R | -256 | -7.6 | same | over-filter |
| V2 BE @ +0.5R | -902 | -16.6 | -1.0 | early trigger trap |
| V3 BE+1pt @ +1R | -90 | +15.9 | same | neutral PnL + WR up |
| V4 BE @ +1.5R | -231 | -2.7 | same | meh |
| **V5 TRAIL @ +1R then trail** | **+48** | **+16.2** | same | ⭐ balanced WIN |
| V6 BE @ opposite-box-edge | +307 | -21.0 | +6.1 | absolute PnL win, WR collapse |

**Verdict:** V5 winner — +48 PnL marginal + WR 34.9→51.2% (+16.2pt) + worst trade unchanged. Per-session V5: Asia FLIP positif (-19→+68), London +54, NY -93. **NOT auto-deployed** — pending user decision (Pine port 2-3 jam effort). Vault: [[Phase-17-BE-Trail-Sweep]].

**Caveat:** Trade count V5 = 6,563 vs baseline 5,203 (+1,360). BE exit free up max=5 slots → re-entry. Live trader manual mungkin TIDAK ambil semua re-entry — real V5 PnL likely slightly < +48 sim, but WR boost real.

### Phase 18 — EOD Force-Close Impact Analysis (added 2026-05-08)
**STRUCTURAL FINDING.** 3-scenario test on e44 PB 5y:

| Scenario | Trades | PnL | Δ vs A | WR |
|----------|------:|-----:|-------:|---:|
| **A. CURRENT** (EOD force-close ON) | 6,574 | **+4,301** | 0 | 42.1% |
| **B. DROP-EOD** (analytical filter) | 5,203 | +1,966 | -2,334 | 34.9% |
| **C. EXTEND** (session ke 23:59, no force-close) | 7,201 | +3,485 | -816 | 36.2% |

**Per-Session Closed vs EOD share:**
| Session | Closed | EOD | EOD share |
|---------|------:|-----:|----------:|
| Asia | **-19** | +591 | **100%** (Asia full edge from EOD!) |
| London | +679 | +628 | 48% |
| NY | +1,306 | +1,116 | 46% |
| Total | +1,966 | +2,334 | **54%** |

**3 Critical Insights:**
1. EOD force-close kontribusi 54% e44 PnL (+2,334 dari +4,301)
2. Asia closed-only NEGATIF -19 — semua Asia edge dari EOD M-T-M
3. Extend to midnight ≠ recovery (still -19% vs baseline) — force-close STRATEGIC captures favorable mid-trade prices

**Live Trading Implication:**
- Manual close di session-end (Pine alert) → Full +4,301 captured ✓
- Hold sampai SL/TP only → -19% drag ⚠️
- Mixed (close profit, hold loss) → WORST (loss aversion trap)

**Verdict:** EOD force-close = STRUCTURAL EDGE source, BUKAN bug. Pine `forceSessionEndClose` lines 663-688 essential. Real $/yr at 0.02 lot:
- With EOD force-close: $1,720/yr
- Natural SL/TP only: $1,394/yr (-19%)

Vault: [[Phase-18-EOD-Impact-Analysis]].

### Phase 19 — Loss Forensic Analysis (added 2026-05-08)
Forensic on **3,807 losing trades** dari 5y e44 PB (baseline WR 42.1%, loss avg -3.73pt, P95 worst -7.98pt).

**Top 5 Patterns Found:**

1. **Trade Duration = Predictor #1**:
   - Flash <5min: 82.2% loss (-895 PnL)
   - Quick 5-15min: 73.5% loss (-536 PnL)
   - Grind >60min: 43.6% loss (+4,586 PnL = mostly winners)
   - **Insight:** Patience pays. Trade survive >60min = 56% WIN.

2. **Tight SL Paradox** (counter-intuitive):
   - Tight 3-5pt: 59.6% loss
   - Wide 8-12pt: **45.4% loss** (best!)
   - **Insight:** Tight retest entry whipsaws more. Wider SL setups = lebih konsisten.

3. **Hour 8 ET = WORST** (62.7% loss, 800 trades):
   - NY pre-8:30 macro release window trap (NFP/CPI/Retail Sales)
   - Hour 7 ET (NY box formation) = BEST 45.5% loss

4. **Pre-box 2h Direction Alignment**:
   - ALIGNED: 56.0% loss
   - RANGE: 56.4% loss
   - COUNTER: 59.7% loss
   - **Insight:** Skip counter-trend = save 4pt loss rate.

5. **Februari = Worst Month** (62.9% loss):
   - Q1 Fed/CPI cycle volatility
   - November best 52.9% loss

**Worst 30 Trades Common Signature:**
- 100% SL hit
- Risk 17-37pt (outlier wide)
- 80%+ RANGE_PRE / COUNTER context
- 90%+ at ATR rank >70 (high vol)
- Februari 2026 dominant (10/30)

**Loss Distribution Reality:**
- 95% losses < 8pt = mental cap aman, system designed correct
- Daily loss clustering: 72.5% days have ≥3 losses (multi-loss day NORMAL)

**5 Hypothesis Skip Rules (PENDING VALIDATION):**
1. Hold trade ≥60min — mental rule, no code change
2. Skip Hour 8 ET entries (NY pre-macro)
3. Skip counter-pre-box-trend trades
4. Avoid narrow box 5-10pt (paradox)
5. Februari extra cautious / lower lot sizing

**Caveat:** Phase 16 confirmed filter-on-top sweep ALL FAIL. These hypothesis perlu backtest validation sebelum auto-deploy. e44 baseline UNCHANGED.

Vault: [[Phase-19-Loss-Forensic-Analysis]].

### Tier-4 SMC tested — ALL FAILED (added 2026-05-05)
- **Order Block** directional align: -119 pts (no edge)
- **Fair Value Gap** align: -2 pts (neutral, no signal)
- **Break of Structure** align: -476 pts (cuts good trades)
- **BOS presence-only** (skip days with no BOS): -1843 pts (massive over-filter, 474 trades only)

**Insight:** PT box edge is in REGIME (e38) + RISK ADJUSTMENT (e39 TP boost) + TIMING (e40 NY delay, e41 Asia 19:00) + SL CALIBRATION (e41 London 0.9). Smart-Money structural concepts add nothing — system trades the breakout itself, not the structural narrative.

### Tier-4 min-SL trap — REJECTED despite "improvement"
- min_sl=5: total +3706 (Δ +389 vs e40) — looked great BUT closed PnL drops -596, EOD inflates +985
- min_sl=7: total +3863 (Δ +546) — closed PnL -1846, EOD +2392 ← entire "improvement" is EOD M-T-M inflation
- WR drops 60% → 49.8% with wider SL. Trade count halves.
- **Lesson:** total PnL + EOD without proper M-T-M attribution can mislead. Always check closed PnL alongside.

### What didn't work ❌
1. **EOD time-cap exits** (60-180 min) — caps kill winning runners. Better fix: wider TP via e39.
2. **Volume filter** (tickvol confirmation) — MT5 tickvol too noisy for signal.
3. **Box-quality filter** (skip wide boxes) — NY suffers most, boxes naturally wide there.
4. **Daily trend D1 SMA20 directional** — counter-trend breakouts profitable in this system.
5. **Per-session ATR** — daily ATR captures macro regime better than session-specific.
6. **Intra-box HH-HL bias** — only ~58% boxes have clean structure, over-filtering kills good trades.
7. **DoW filter** (skip Thursday) — disconfirmed earlier (e23 series, see vault).
8. **Cooldown after 2 losses** — trigger too rare to matter (e38 already filters bad regime).
9. **ICT Power-of-Three (PO3) sweep** (require pre-box liquidity sweep) — over-filters: only 489 trades / -1779 pts. Sweep concept too restrictive for system that already trades breakouts.
10. **Pre-session direction filter (RANGE only / skip directional)** — over-filter: -1178 pts. Pre-2h direction not predictive enough.
11. **Inter-session chain (Asia[t-1] → London/NY direction bias)** — counter-direction trades have positive expectancy: -674 pts.
12. **Top-40% volatility hours filter** — over-filter: -493 pts. ATR daily already captures regime.
13. **Spread cost realism** — at 0.1pt spread cost, -260 pts/5y; at 0.5pt, -1300 pts. **Real concern for live trading**, not a strategy filter but cost reality. Need to check actual broker spread.

### What worked but marginal (not adopted standalone)
- **Continuous TP × ATR rank linear** — Δ +29 vs e39. Marginal, complexity not justified vs discrete e39 boost.
- **Drop inside-bar (Naked Forex strict)** — Δ +1 vs e39. Neutral, but reduces trade count cleaner.
- **TP shrink TP×0.75 when ATR ≤ 30th** — Δ +7 vs e39. Marginal, not worth complexity.

### Vault wisdom incorporated
- e23 disconfirmed: descriptive stats ≠ forward-applied filter (sample collapse + optimizer drift)
- All filters use ROLLING window with NO look-ahead (lessons from earlier traps)
- Constraint per user: PT box duration time stays FIXED (90/60/60 min); only filters added on top

---

## 🔬 Test methodology

For every candidate:
1. Run on full 5y data (2021-2026, 1368 trading days)
2. Compare closed PnL + total PnL (incl. EOD M-T-M) vs current baseline
3. If improves, run OOS train/test split (≤2023 vs >2023)
4. Validate: test quarters ≥ 70% positive, retention reasonable
5. Add to registry whether adopted or rejected
6. **NEVER OVERWRITE WINNING BASELINE WITH WORSE VARIANT**

---

## 📂 Source files

- `data/iterations_registry.json` — machine-readable registry (10+ variants)
- `data/phase8_e38_v12_iteration.json` — e38 sweep results (5 candidates)
- `data/phase8_e38_atr_filter.json` — e38 5y + OOS
- `data/phase9_e39_tier2.json` — e39 tier-2 sweep
- `data/phase9_e39_winner.json` — e39 winner config + OOS
- `scripts/run_e38_v12_iteration.py` — e38 framework
- `scripts/run_e39_tier2_stacked.py` — e39 tier-2 framework
