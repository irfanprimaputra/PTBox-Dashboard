//+------------------------------------------------------------------+
//|                                              PTBox_e44_v14.mq5  |
//|         PT BOX e44 PULLBACK v14 — BE TRAIL EA (auto-execute)    |
//|         Mirror of Pine v14: e44 PB state machine + BE Trail     |
//|                                                                  |
//|   2026-05-10 v14.1 BUGFIX + PARITY:                              |
//|     - Fix ArrayInitialize struct compile error                    |
//|     - Add maxAttempt counter (1→5, match Pine default)            |
//|     - Add ATR filter (e38, skip below 30th pctile)                |
//|     - Add TP boost (e39, 1.3× when ATR rank ≥72)                  |
//|     - Add NY delay 25min (e40)                                    |
//|     - Add session attempt tracker reset per day                   |
//|     - Tighter pattern detection (multi-shape match)               |
//|                                                                  |
//|   Backtest (Pine v14 5y mirror):                                  |
//|     WR 51.2% (vs 34.9% v13) · PnL +$4349 · worst trade -$74      |
//|                                                                  |
//|   ⚠️ AUTO-TRADE EA — opens/manages/closes trades automatically.  |
//|   Test on demo dulu sebelum live!                                 |
//+------------------------------------------------------------------+
#property copyright "PT Box e44 v14.1 BE Trail · Irfan 2026"
#property version   "14.10"
#property strict
#property description "Auto-execute e44 PULLBACK + BE Trail (Pine v14 mirror, full parity)"

#include <Trade\Trade.mqh>
CTrade trade;

//+------------------------------------------------------------------+
//| Inputs                                                            |
//+------------------------------------------------------------------+
input group "═════ Risk ═════"
input double LotSize          = 0.02;
input ulong  MagicNumber      = 14014401;
input int    SlippagePts      = 20;

input group "═════ Timezone ═════"
input int    ET_GMTOffset     = -4;
input int    Broker_GMTOffset = 0;

input group "═════ Asia (e44 PB) ═════"
input bool   AsiaEnable       = true;
input int    AsiaBoxStartH    = 19;
input int    AsiaBoxStartM    = 0;
input int    AsiaBoxDurMin    = 90;
input int    AsiaSessionEndH  = 24;
input int    AsiaMaxAttempt   = 5;

input group "═════ London (e44 PB) ═════"
input bool   LonEnable        = true;
input int    LonBoxStartH     = 0;
input int    LonBoxStartM     = 0;
input int    LonBoxDurMin     = 60;
input int    LonSessionEndH   = 8;
input int    LonMaxAttempt    = 5;

input group "═════ NY (e44 PB) ═════"
input bool   NYEnable         = true;
input int    NYBoxStartH      = 7;
input int    NYBoxStartM      = 0;
input int    NYBoxDurMin      = 60;
input int    NYSessionEndH    = 13;
input int    NYMaxAttempt     = 5;
input int    NYEntryDelayMin  = 25;            // e40: skip first 25min of NY post-box (kill-zone trap avoidance)

input group "═════ e44 PULLBACK Params ═════"
input double PbRetestTol      = 3.0;
input double PbSlBuffer       = 2.0;
input double PbTpMult         = 2.0;
input int    PbMaxWaitBars    = 60;

input group "═════ 🛡️ BE Trail (Phase 17 V5) ═════"
input bool   UseBeTrail       = true;
input double BeTriggerR       = 1.0;

input group "═════ ATR Regime Filter (e38/e39) ═════"
input bool   UseAtrFilter     = true;          // e38: skip days with ATR < 30th pctile
input int    AtrLookbackDays  = 30;
input int    AtrPctileSkip    = 30;            // skip below this percentile
input bool   UseTpBoost       = true;          // e39: 1.3× TP when ATR ≥ 72nd
input int    AtrPctileBoost   = 72;
input double TpBoostMult      = 1.30;

input group "═════ Notifications ═════"
input bool   PushToMobile     = true;
input bool   PlayAlertSound   = true;
input bool   PrintLog         = true;

//+------------------------------------------------------------------+
//| Globals                                                           |
//+------------------------------------------------------------------+
struct BoxState {
   double  hi;
   double  lo;
   bool    formed;
   datetime formedAt;
   int     pbState;       // 0=WAIT_BREAKOUT, 1=WAIT_PULLBACK, 2=WAIT_REJECTION
   int     pbBkDir;
   int     pbBkBar;
   double  pbExtreme;
   int     attempts;      // counter (replaces hadEntry bool, supports max=5)
};
BoxState asiaBox, lonBox, nyBox;
int      lastDay = -1;
ulong    asiaTicket = 0, lonTicket = 0, nyTicket = 0;

struct BeState {
   ulong  ticket;
   double entryPx;
   double slOrig;
   bool   triggered;
   double runExtreme;
};
BeState beStates[3];

// ATR regime cache (computed once per day)
double  atrRankToday = 0.5;   // 0.0–1.0 percentile rank
bool    atrComputedToday = false;

//+------------------------------------------------------------------+
//| Init / Deinit                                                    |
//+------------------------------------------------------------------+
int OnInit() {
   trade.SetExpertMagicNumber(MagicNumber);
   trade.SetDeviationInPoints(SlippagePts);
   trade.SetTypeFilling(ORDER_FILLING_IOC);
   ResetSessions();
   for(int i = 0; i < 3; i++) {
      beStates[i].ticket    = 0;
      beStates[i].triggered = false;
   }
   PrintFormat("[PT Box v14.1] init | Lot=%.2f | BE=%s | ATR=%s | maxAtt=%d/%d/%d",
               LotSize, UseBeTrail ? "ON" : "OFF", UseAtrFilter ? "ON" : "OFF",
               AsiaMaxAttempt, LonMaxAttempt, NYMaxAttempt);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) {
   PrintFormat("[PT Box v14.1] deinit reason=%d", reason);
}

//+------------------------------------------------------------------+
//| Time helpers                                                     |
//+------------------------------------------------------------------+
int BrokerToETHour(datetime t) {
   MqlDateTime mt; TimeToStruct(t, mt);
   int gmtH = mt.hour - Broker_GMTOffset;
   int etH  = gmtH + ET_GMTOffset;
   while(etH < 0)  etH += 24;
   while(etH >= 24) etH -= 24;
   return etH;
}

int ETMinOfDay(datetime t) {
   MqlDateTime mt; TimeToStruct(t, mt);
   return BrokerToETHour(t) * 60 + mt.min;
}

int ETDayOfMonth(datetime t) {
   MqlDateTime mt; TimeToStruct(t, mt);
   int gmtH = mt.hour - Broker_GMTOffset;
   int etH = gmtH + ET_GMTOffset;
   if(etH < 0) {
      MqlDateTime mp; TimeToStruct(t - 86400, mp);
      return mp.day;
   }
   if(etH >= 24) {
      MqlDateTime mn; TimeToStruct(t + 86400, mn);
      return mn.day;
   }
   return mt.day;
}

//+------------------------------------------------------------------+
//| Session reset                                                    |
//+------------------------------------------------------------------+
void ResetBox(BoxState &bx) {
   bx.hi = 0; bx.lo = 0; bx.formed = false;
   bx.pbState = 0; bx.pbBkDir = 0; bx.pbBkBar = 0;
   bx.pbExtreme = 0; bx.attempts = 0;
}

void ResetSessions() {
   ResetBox(asiaBox);
   ResetBox(lonBox);
   ResetBox(nyBox);
   atrComputedToday = false;
}

//+------------------------------------------------------------------+
//| ATR regime filter (e38/e39)                                      |
//| Compute today's true range, rank vs N-day window                 |
//+------------------------------------------------------------------+
void ComputeAtrRank() {
   if(atrComputedToday) return;
   int n = AtrLookbackDays;
   if(n < 5) n = 5;
   double trArr[];
   ArrayResize(trArr, n);
   for(int i = 1; i <= n; i++) {
      double h = iHigh(_Symbol, PERIOD_D1, i);
      double l = iLow(_Symbol, PERIOD_D1, i);
      double pc = iClose(_Symbol, PERIOD_D1, i + 1);
      double tr = MathMax(h - l, MathMax(MathAbs(h - pc), MathAbs(l - pc)));
      trArr[i - 1] = tr;
   }
   // Today's TR (proxy: most recent completed day TR vs distribution)
   double trToday = trArr[0];
   int below = 0;
   for(int i = 0; i < n; i++) if(trArr[i] < trToday) below++;
   atrRankToday = (double)below / (double)n;
   atrComputedToday = true;
   if(PrintLog) PrintFormat("[ATR] rank=%.2f (today TR=%.2f, %d-day window)",
                            atrRankToday, trToday, n);
}

bool AtrPass() {
   if(!UseAtrFilter) return true;
   ComputeAtrRank();
   return atrRankToday >= (AtrPctileSkip / 100.0);
}

double TpEffectiveMult() {
   if(!UseTpBoost) return PbTpMult;
   ComputeAtrRank();
   return atrRankToday >= (AtrPctileBoost / 100.0)
          ? PbTpMult * TpBoostMult
          : PbTpMult;
}

//+------------------------------------------------------------------+
//| Box build                                                        |
//+------------------------------------------------------------------+
void UpdateBox(BoxState &bx, int startMin, int endMin, double ph, double pl, int curMin) {
   if(bx.formed) return;
   if(curMin >= startMin && curMin < endMin) {
      if(bx.hi == 0 && bx.lo == 0) {
         bx.hi = ph; bx.lo = pl;
      } else {
         bx.hi = MathMax(bx.hi, ph);
         bx.lo = MathMin(bx.lo, pl);
      }
   } else if(curMin >= endMin && bx.hi > 0) {
      bx.formed = true;
      bx.formedAt = TimeCurrent();
      if(PrintLog) PrintFormat("[BOX FORMED] hi=%.2f lo=%.2f bw=%.2f",
                               bx.hi, bx.lo, bx.hi - bx.lo);
   }
}

//+------------------------------------------------------------------+
//| Pattern detection — multi-shape match (engulf, pin, hammer)      |
//+------------------------------------------------------------------+
bool IsBullPattern(double po, double ph, double pl, double pc,
                   double co, double ch, double cl, double cc) {
   bool engulf = cc > po && co < pc && cc > co;
   double range = ch - cl;
   if(range <= 0) return engulf;
   bool pin = (cc - cl) / range > 0.6 && (cc > co);
   bool hammer = (cc - cl) / range > 0.5 && (ch - cc) / range < 0.3 && cc > co;
   bool inside = ch <= ph && cl >= pl && cc > co;
   return engulf || pin || hammer || inside;
}

bool IsBearPattern(double po, double ph, double pl, double pc,
                   double co, double ch, double cl, double cc) {
   bool engulf = cc < po && co > pc && cc < co;
   double range = ch - cl;
   if(range <= 0) return engulf;
   bool pin = (ch - cc) / range > 0.6 && (cc < co);
   bool hammer = (ch - cc) / range > 0.5 && (cc - cl) / range < 0.3 && cc < co;
   bool inside = ch <= ph && cl >= pl && cc < co;
   return engulf || pin || hammer || inside;
}

//+------------------------------------------------------------------+
//| e44 PULLBACK state machine                                       |
//+------------------------------------------------------------------+
void ProcessPullback(BoxState &bx, ulong &ticketRef, string sessionTag, int maxAtt,
                     double po, double ph, double pl, double pc,
                     double co, double ch, double cl, double cc,
                     int curBarIdx) {
   if(!bx.formed) return;
   if(bx.attempts >= maxAtt) return;
   if(ticketRef != 0) return;
   if(!AtrPass()) return;

   double bw = bx.hi - bx.lo;
   if(bw < 1) return;

   if(bx.pbState == 0) {
      if(cc > bx.hi) {
         bx.pbState = 1; bx.pbBkDir = 1; bx.pbBkBar = curBarIdx; bx.pbExtreme = cl;
         if(PrintLog) PrintFormat("[%s] BREAKOUT UP @ %.2f", sessionTag, cc);
      } else if(cc < bx.lo) {
         bx.pbState = 1; bx.pbBkDir = -1; bx.pbBkBar = curBarIdx; bx.pbExtreme = ch;
         if(PrintLog) PrintFormat("[%s] BREAKOUT DOWN @ %.2f", sessionTag, cc);
      }
      return;
   }

   if(bx.pbState == 1) {
      if(curBarIdx - bx.pbBkBar > PbMaxWaitBars) {
         bx.pbState = 0; bx.pbBkDir = 0;
         return;
      }
      if(bx.pbBkDir == 1) {
         bx.pbExtreme = MathMin(bx.pbExtreme, cl);
         if(cl <= bx.hi + PbRetestTol && cl >= bx.hi - PbRetestTol) bx.pbState = 2;
      } else {
         bx.pbExtreme = MathMax(bx.pbExtreme, ch);
         if(ch >= bx.lo - PbRetestTol && ch <= bx.lo + PbRetestTol) bx.pbState = 2;
      }
      return;
   }

   if(bx.pbState == 2) {
      double tpEff = TpEffectiveMult();
      if(bx.pbBkDir == 1) {
         if(cl >= bx.hi - PbRetestTol && IsBullPattern(po, ph, pl, pc, co, ch, cl, cc)) {
            double slPx = MathMin(cl, pl) - PbSlBuffer;
            double slDist = cc - slPx;
            if(slDist <= 0 || slDist > 30) {
               bx.attempts++; bx.pbState = 0; return;
            }
            double tpPx = cc + tpEff * slDist;
            OpenTrade(true, cc, slPx, tpPx, sessionTag, ticketRef);
            bx.attempts++; bx.pbState = 0;
         }
      } else {
         if(ch <= bx.lo + PbRetestTol && IsBearPattern(po, ph, pl, pc, co, ch, cl, cc)) {
            double slPx = MathMax(ch, ph) + PbSlBuffer;
            double slDist = slPx - cc;
            if(slDist <= 0 || slDist > 30) {
               bx.attempts++; bx.pbState = 0; return;
            }
            double tpPx = cc - tpEff * slDist;
            OpenTrade(false, cc, slPx, tpPx, sessionTag, ticketRef);
            bx.attempts++; bx.pbState = 0;
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Open trade + register BE state                                   |
//+------------------------------------------------------------------+
void OpenTrade(bool isLong, double entryPx, double slPx, double tpPx,
               string sessionTag, ulong &ticketRef) {
   double price = isLong ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                          : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   bool ok = isLong
      ? trade.Buy(LotSize, _Symbol, price, slPx, tpPx, "PTBox v14 " + sessionTag)
      : trade.Sell(LotSize, _Symbol, price, slPx, tpPx, "PTBox v14 " + sessionTag);

   if(ok) {
      ticketRef = trade.ResultOrder();
      RegisterBeState(ticketRef, price, slPx);
      string msg = StringFormat("🚀 PT Box v14 %s | %s @ %.2f | SL %.2f | TP %.2f | Lot %.2f",
                                sessionTag, isLong ? "BUY" : "SELL", price, slPx, tpPx, LotSize);
      Print(msg);
      if(PushToMobile) SendNotification(msg);
      if(PlayAlertSound) Alert(msg);
   } else {
      PrintFormat("[%s] OPEN FAILED: %s", sessionTag, trade.ResultRetcodeDescription());
   }
}

void RegisterBeState(ulong ticket, double entryPx, double slOrig) {
   for(int i = 0; i < 3; i++) {
      if(beStates[i].ticket == 0) {
         beStates[i].ticket    = ticket;
         beStates[i].entryPx   = entryPx;
         beStates[i].slOrig    = slOrig;
         beStates[i].triggered = false;
         beStates[i].runExtreme = entryPx;
         return;
      }
   }
}

//+------------------------------------------------------------------+
//| BE Trail manager (called every tick)                             |
//+------------------------------------------------------------------+
void ManageBeTrail() {
   if(!UseBeTrail) return;
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);

   for(int i = 0; i < 3; i++) {
      if(beStates[i].ticket == 0) continue;
      ulong ticket = beStates[i].ticket;
      if(!PositionSelectByTicket(ticket)) {
         beStates[i].ticket = 0;
         continue;
      }

      long type = PositionGetInteger(POSITION_TYPE);
      double entryPx = beStates[i].entryPx;
      double slOrig  = beStates[i].slOrig;
      double slDist  = MathAbs(entryPx - slOrig);
      double curSl   = PositionGetDouble(POSITION_SL);
      double curTp   = PositionGetDouble(POSITION_TP);

      if(!beStates[i].triggered) {
         double favor = (type == POSITION_TYPE_BUY) ? (bid - entryPx) : (entryPx - ask);
         double trigger = BeTriggerR * slDist;
         if(favor >= trigger) {
            if(trade.PositionModify(ticket, entryPx, curTp)) {
               beStates[i].triggered = true;
               beStates[i].runExtreme = (type == POSITION_TYPE_BUY) ? bid : ask;
               string msg = StringFormat("🛡️ BE ARMED ticket=%I64u | SL → %.2f", ticket, entryPx);
               Print(msg);
               if(PushToMobile) SendNotification(msg);
            }
         }
      } else {
         if(type == POSITION_TYPE_BUY) {
            if(bid > beStates[i].runExtreme) beStates[i].runExtreme = bid;
            double newSl = beStates[i].runExtreme - slDist;
            if(newSl > curSl) {
               if(trade.PositionModify(ticket, newSl, curTp)) {
                  if(PrintLog) PrintFormat("🎯 TRAIL %I64u SL→%.2f", ticket, newSl);
               }
            }
         } else {
            if(ask < beStates[i].runExtreme) beStates[i].runExtreme = ask;
            double newSl = beStates[i].runExtreme + slDist;
            if(newSl < curSl) {
               if(trade.PositionModify(ticket, newSl, curTp)) {
                  if(PrintLog) PrintFormat("🎯 TRAIL %I64u SL→%.2f", ticket, newSl);
               }
            }
         }
      }
   }
}

//+------------------------------------------------------------------+
//| EOD force-close                                                  |
//+------------------------------------------------------------------+
void ForceCloseSession(ulong &ticketRef, string sessionTag) {
   if(ticketRef == 0) return;
   if(PositionSelectByTicket(ticketRef)) {
      if(trade.PositionClose(ticketRef)) {
         string msg = StringFormat("🔚 EOD %s ticket=%I64u", sessionTag, ticketRef);
         Print(msg);
         if(PushToMobile) SendNotification(msg);
      }
   }
   ticketRef = 0;
}

//+------------------------------------------------------------------+
//| OnTick — main loop                                               |
//+------------------------------------------------------------------+
datetime lastBar = 0;

void OnTick() {
   ManageBeTrail();

   datetime curBar = iTime(_Symbol, PERIOD_M1, 0);
   if(curBar == lastBar) return;
   lastBar = curBar;

   datetime now = TimeCurrent();
   int curDay = ETDayOfMonth(now);
   int curMin = ETMinOfDay(now);

   if(lastDay != -1 && curDay != lastDay) {
      ResetSessions();
   }
   lastDay = curDay;

   double po = iOpen(_Symbol, PERIOD_M1, 2);
   double ph = iHigh(_Symbol, PERIOD_M1, 2);
   double pl = iLow(_Symbol, PERIOD_M1, 2);
   double pc = iClose(_Symbol, PERIOD_M1, 2);
   double co = iOpen(_Symbol, PERIOD_M1, 1);
   double ch = iHigh(_Symbol, PERIOD_M1, 1);
   double cl = iLow(_Symbol, PERIOD_M1, 1);
   double cc = iClose(_Symbol, PERIOD_M1, 1);

   int curBarIdx = (int)(now / 60);

   if(AsiaEnable) {
      int s = AsiaBoxStartH * 60 + AsiaBoxStartM;
      int e = s + AsiaBoxDurMin;
      int f = (AsiaSessionEndH == 24 ? 1439 : AsiaSessionEndH * 60 - 1);
      UpdateBox(asiaBox, s, e, ph, pl, curMin);
      if(curMin >= e && curMin < f) {
         ProcessPullback(asiaBox, asiaTicket, "ASIA", AsiaMaxAttempt,
                         po, ph, pl, pc, co, ch, cl, cc, curBarIdx);
      }
      if(curMin >= f) ForceCloseSession(asiaTicket, "ASIA");
   }

   if(LonEnable) {
      int s = LonBoxStartH * 60 + LonBoxStartM;
      int e = s + LonBoxDurMin;
      int f = LonSessionEndH * 60 - 1;
      UpdateBox(lonBox, s, e, ph, pl, curMin);
      if(curMin >= e && curMin < f) {
         ProcessPullback(lonBox, lonTicket, "LON", LonMaxAttempt,
                         po, ph, pl, pc, co, ch, cl, cc, curBarIdx);
      }
      if(curMin >= f) ForceCloseSession(lonTicket, "LON");
   }

   if(NYEnable) {
      int s = NYBoxStartH * 60 + NYBoxStartM;
      int e = s + NYBoxDurMin;
      int f = NYSessionEndH * 60 - 1;
      UpdateBox(nyBox, s, e, ph, pl, curMin);
      // e40 NY delay: trade only AFTER box end + entry delay
      if(curMin >= e + NYEntryDelayMin && curMin < f) {
         ProcessPullback(nyBox, nyTicket, "NY", NYMaxAttempt,
                         po, ph, pl, pc, co, ch, cl, cc, curBarIdx);
      }
      if(curMin >= f) ForceCloseSession(nyTicket, "NY");
   }

   if(asiaTicket != 0 && !PositionSelectByTicket(asiaTicket)) asiaTicket = 0;
   if(lonTicket  != 0 && !PositionSelectByTicket(lonTicket))  lonTicket  = 0;
   if(nyTicket   != 0 && !PositionSelectByTicket(nyTicket))   nyTicket   = 0;
}

//+------------------------------------------------------------------+
