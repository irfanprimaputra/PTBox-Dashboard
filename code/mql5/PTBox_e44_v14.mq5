//+------------------------------------------------------------------+
//|                                              PTBox_e44_v14.mq5  |
//|         PT BOX e44 PULLBACK v14 — BE TRAIL EA (auto-execute)    |
//|         Mirror of Pine v14: e44 PB state machine + BE Trail     |
//|                                                                  |
//|   Mechanic:                                                       |
//|     1. Box per session (Asia 19:00/90m, London 0:00/60m,          |
//|        NY 7:00/60m — ET timezone)                                 |
//|     2. State machine: WAIT_BREAKOUT → WAIT_PULLBACK →             |
//|        WAIT_REJECTION → ENTRY                                     |
//|     3. SL = high/low of rejection candle + buffer                 |
//|     4. TP = entry + 2×R                                           |
//|     5. BE Trail: at +1R favor, SL → entry. After BE, trail SL    |
//|        with running max(high)/min(low).                           |
//|     6. EOD force-close at session end                             |
//|                                                                  |
//|   Backtest (Pine v14 5y):                                         |
//|     WR 51.2% (vs 34.9% v13) · PnL +$4349 · worst trade -$74      |
//|                                                                  |
//|   ⚠️ AUTO-TRADE EA — opens/manages/closes trades automatically.  |
//|   Test on demo dulu sebelum live!                                 |
//+------------------------------------------------------------------+
#property copyright "PT Box e44 v14 BE Trail · Irfan 2026"
#property version   "14.00"
#property strict
#property description "Auto-execute e44 PULLBACK + BE Trail (Pine v14 mirror)"

#include <Trade\Trade.mqh>
CTrade trade;

//+------------------------------------------------------------------+
//| Inputs                                                            |
//+------------------------------------------------------------------+
input group "═════ Risk ═════"
input double LotSize          = 0.02;     // Lot per trade
input ulong  MagicNumber      = 14014401; // EA magic number (don't share with other EAs)
input int    SlippagePts      = 20;       // Slippage tolerance (points = 0.1 pip XAUUSD)

input group "═════ Timezone ═════"
input int    ET_GMTOffset     = -4;       // ET = GMT-4 (EDT) or -5 (EST winter)
input int    Broker_GMTOffset = 0;        // Broker server time vs GMT (Tools→Options→Server)

input group "═════ Session: Asia (e44 PB) ═════"
input bool   AsiaEnable       = true;
input int    AsiaBoxStartH    = 19;       // ET hour (19:00 ET)
input int    AsiaBoxStartM    = 0;
input int    AsiaBoxDurMin    = 90;
input int    AsiaSessionEndH  = 24;       // 24 = midnight (extended)

input group "═════ Session: London (e44 PB) ═════"
input bool   LonEnable        = true;
input int    LonBoxStartH     = 0;        // ET hour (0:00 ET)
input int    LonBoxStartM     = 0;
input int    LonBoxDurMin     = 60;
input int    LonSessionEndH   = 8;

input group "═════ Session: NY (e44 PB) ═════"
input bool   NYEnable         = true;
input int    NYBoxStartH      = 7;        // ET hour (7:00 ET)
input int    NYBoxStartM      = 0;
input int    NYBoxDurMin      = 60;
input int    NYSessionEndH    = 13;

input group "═════ e44 PULLBACK Params ═════"
input double PbRetestTol      = 3.0;      // Retest tolerance (pts)
input double PbSlBuffer       = 2.0;      // SL buffer below retest (pts)
input double PbTpMult         = 2.0;      // TP × actual_risk (R:R)
input int    PbMaxWaitBars    = 60;       // Max wait bars for retest

input group "═════ 🛡️ BE Trail (Phase 17 V5) ═════"
input bool   UseBeTrail       = true;     // Enable BE Trail
input double BeTriggerR       = 1.0;      // BE trigger at +X×R favor

input group "═════ Notifications ═════"
input bool   PushToMobile     = true;     // Push notification ke MT5 mobile
input bool   PlayAlertSound   = true;
input bool   PrintLog         = true;

//+------------------------------------------------------------------+
//| Globals — box state per session                                  |
//+------------------------------------------------------------------+
struct BoxState {
   double  hi;
   double  lo;
   bool    formed;
   datetime formedAt;
   int     pbState;       // 0=WAIT_BREAKOUT, 1=WAIT_PULLBACK, 2=WAIT_REJECTION
   int     pbBkDir;       // breakout direction (1=up, -1=down)
   int     pbBkBar;       // bar index when breakout fired
   double  pbExtreme;     // pullback extreme tracker
   bool    hadEntry;      // already entered today (1 attempt/day)
};

BoxState asiaBox, lonBox, nyBox;
int      lastDay = -1;
ulong    asiaTicket = 0, lonTicket = 0, nyTicket = 0;

// BE Trail per-trade state (keyed by ticket)
struct BeState {
   ulong  ticket;
   double entryPx;
   double slOrig;
   bool   triggered;
   double runExtreme;
};
BeState beStates[3];   // max 3 concurrent (one per session)

//+------------------------------------------------------------------+
//| Init / Deinit                                                    |
//+------------------------------------------------------------------+
int OnInit() {
   trade.SetExpertMagicNumber(MagicNumber);
   trade.SetDeviationInPoints(SlippagePts);
   trade.SetTypeFilling(ORDER_FILLING_IOC);
   ResetSessions();
   ArrayInitialize(beStates, 0);
   for(int i = 0; i < 3; i++) beStates[i].ticket = 0;
   Print("[PT Box v14] EA initialized | Lot=", LotSize, " | BE Trail=", UseBeTrail ? "ON" : "OFF");
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) {
   Print("[PT Box v14] EA deinit, reason=", reason);
}

//+------------------------------------------------------------------+
//| Helpers — time conversion                                        |
//+------------------------------------------------------------------+
int BrokerToETHour(datetime t) {
   MqlDateTime mt; TimeToStruct(t, mt);
   int brokerH = mt.hour;
   int gmtH = brokerH - Broker_GMTOffset;
   int etH = gmtH + ET_GMTOffset;
   while(etH < 0) etH += 24;
   while(etH >= 24) etH -= 24;
   return etH;
}

int BrokerToETMin(datetime t) {
   MqlDateTime mt; TimeToStruct(t, mt);
   return mt.min;
}

int ETMinOfDay(datetime t) {
   return BrokerToETHour(t) * 60 + BrokerToETMin(t);
}

int ETDayOfMonth(datetime t) {
   MqlDateTime mt; TimeToStruct(t, mt);
   // Approximation — for boundary precision use ET-shifted time
   int gmtH = mt.hour - Broker_GMTOffset;
   int etH = gmtH + ET_GMTOffset;
   if(etH < 0) {
      // ET previous day
      datetime prev = t - 86400;
      MqlDateTime mp; TimeToStruct(prev, mp);
      return mp.day;
   }
   if(etH >= 24) {
      datetime nxt = t + 86400;
      MqlDateTime mn; TimeToStruct(nxt, mn);
      return mn.day;
   }
   return mt.day;
}

//+------------------------------------------------------------------+
//| Session reset (new day)                                          |
//+------------------------------------------------------------------+
void ResetSessions() {
   asiaBox.hi = 0; asiaBox.lo = 0; asiaBox.formed = false;
   asiaBox.pbState = 0; asiaBox.pbBkDir = 0; asiaBox.pbBkBar = 0;
   asiaBox.pbExtreme = 0; asiaBox.hadEntry = false;

   lonBox = asiaBox;
   nyBox  = asiaBox;
}

//+------------------------------------------------------------------+
//| Build box per session — accumulate high/low during box window    |
//+------------------------------------------------------------------+
void UpdateBox(BoxState &bx, int startMin, int endMin, double ph, double pl, int curMin) {
   if(curMin >= startMin && curMin < endMin) {
      // In box window — accumulate
      if(!bx.formed && curMin == startMin) {
         bx.hi = ph; bx.lo = pl;
      } else {
         bx.hi = MathMax(bx.hi, ph);
         bx.lo = MathMin(bx.lo, pl);
      }
   } else if(curMin == endMin && !bx.formed) {
      bx.formed = true;
      bx.formedAt = TimeCurrent();
      if(PrintLog) PrintFormat("[PT Box v14] Box formed: hi=%.2f lo=%.2f bw=%.2f",
                               bx.hi, bx.lo, bx.hi - bx.lo);
   }
}

//+------------------------------------------------------------------+
//| Pattern detection — bullish/bearish reversal at retest           |
//+------------------------------------------------------------------+
bool IsBullPattern(double po, double ph, double pl, double pc,
                   double co, double ch, double cl, double cc) {
   // Engulfing bull: cc > po (current close > prev open)
   bool engulf = cc > po && co < pc;
   // Pin bull: long lower wick, close upper half
   double range = ch - cl;
   if(range <= 0) return false;
   bool pin = (cc - cl) / range > 0.6 && (cc > co);
   // Hammer / inside bar bull
   return engulf || pin;
}

bool IsBearPattern(double po, double ph, double pl, double pc,
                   double co, double ch, double cl, double cc) {
   bool engulf = cc < po && co > pc;
   double range = ch - cl;
   if(range <= 0) return false;
   bool pin = (ch - cc) / range > 0.6 && (cc < co);
   return engulf || pin;
}

//+------------------------------------------------------------------+
//| e44 PULLBACK state machine                                       |
//+------------------------------------------------------------------+
void ProcessPullback(BoxState &bx, ulong &ticketRef, string sessionTag,
                     double po, double ph, double pl, double pc,
                     double co, double ch, double cl, double cc,
                     int curBarIdx) {
   if(!bx.formed) return;
   if(bx.hadEntry) return;
   if(ticketRef != 0) return;

   double bw = bx.hi - bx.lo;
   if(bw < 1) return;

   // State 0: WAIT_BREAKOUT
   if(bx.pbState == 0) {
      if(cc > bx.hi) {
         bx.pbState = 1;
         bx.pbBkDir = 1;
         bx.pbBkBar = curBarIdx;
         bx.pbExtreme = cl;
         if(PrintLog) PrintFormat("[%s] BREAKOUT UP @ %.2f", sessionTag, cc);
      } else if(cc < bx.lo) {
         bx.pbState = 1;
         bx.pbBkDir = -1;
         bx.pbBkBar = curBarIdx;
         bx.pbExtreme = ch;
         if(PrintLog) PrintFormat("[%s] BREAKOUT DOWN @ %.2f", sessionTag, cc);
      }
      return;
   }

   // State 1: WAIT_PULLBACK — price retreats toward box edge
   if(bx.pbState == 1) {
      if(curBarIdx - bx.pbBkBar > PbMaxWaitBars) {
         bx.pbState = 0; bx.pbBkDir = 0;  // timeout, reset
         return;
      }
      if(bx.pbBkDir == 1) {
         bx.pbExtreme = MathMin(bx.pbExtreme, cl);
         // Retest: low touches near box top (within tolerance)
         if(cl <= bx.hi + PbRetestTol && cl >= bx.hi - PbRetestTol) {
            bx.pbState = 2;
         }
      } else {
         bx.pbExtreme = MathMax(bx.pbExtreme, ch);
         if(ch >= bx.lo - PbRetestTol && ch <= bx.lo + PbRetestTol) {
            bx.pbState = 2;
         }
      }
      return;
   }

   // State 2: WAIT_REJECTION — confirm reversal candle, ENTRY
   if(bx.pbState == 2) {
      if(bx.pbBkDir == 1) {
         // Long entry: price came back to box top, look for bull rejection
         if(cl >= bx.hi - PbRetestTol && IsBullPattern(po, ph, pl, pc, co, ch, cl, cc)) {
            double slPx = MathMin(cl, pl) - PbSlBuffer;
            double slDist = cc - slPx;
            if(slDist <= 0 || slDist > 30) {
               bx.pbState = 0; bx.hadEntry = true; return;  // bad SL, skip
            }
            double tpPx = cc + PbTpMult * slDist;
            OpenTrade(true, cc, slPx, tpPx, sessionTag, ticketRef);
            bx.hadEntry = true;
            bx.pbState = 0;
         }
      } else {
         if(ch <= bx.lo + PbRetestTol && IsBearPattern(po, ph, pl, pc, co, ch, cl, cc)) {
            double slPx = MathMax(ch, ph) + PbSlBuffer;
            double slDist = slPx - cc;
            if(slDist <= 0 || slDist > 30) {
               bx.pbState = 0; bx.hadEntry = true; return;
            }
            double tpPx = cc - PbTpMult * slDist;
            OpenTrade(false, cc, slPx, tpPx, sessionTag, ticketRef);
            bx.hadEntry = true;
            bx.pbState = 0;
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
//| BE Trail manager — call OnTick                                   |
//+------------------------------------------------------------------+
void ManageBeTrail() {
   if(!UseBeTrail) return;
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);

   for(int i = 0; i < 3; i++) {
      if(beStates[i].ticket == 0) continue;
      ulong ticket = beStates[i].ticket;
      if(!PositionSelectByTicket(ticket)) {
         // Position closed — clear state
         beStates[i].ticket = 0;
         continue;
      }

      long type = PositionGetInteger(POSITION_TYPE);
      double entryPx = beStates[i].entryPx;
      double slOrig  = beStates[i].slOrig;
      double slDist  = MathAbs(entryPx - slOrig);
      double curSl   = PositionGetDouble(POSITION_SL);
      double curTp   = PositionGetDouble(POSITION_TP);

      // Step 1: arm BE
      if(!beStates[i].triggered) {
         double favor = (type == POSITION_TYPE_BUY) ? (bid - entryPx) : (entryPx - ask);
         double trigger = BeTriggerR * slDist;
         if(favor >= trigger) {
            // Move SL to entry (BE)
            if(trade.PositionModify(ticket, entryPx, curTp)) {
               beStates[i].triggered = true;
               beStates[i].runExtreme = (type == POSITION_TYPE_BUY) ? bid : ask;
               string msg = StringFormat("🛡️ BE ARMED ticket=%I64u | SL → %.2f", ticket, entryPx);
               Print(msg);
               if(PushToMobile) SendNotification(msg);
            }
         }
      }
      // Step 2: trail
      else {
         if(type == POSITION_TYPE_BUY) {
            if(bid > beStates[i].runExtreme) beStates[i].runExtreme = bid;
            double newSl = beStates[i].runExtreme - slDist;
            if(newSl > curSl) {
               if(trade.PositionModify(ticket, newSl, curTp)) {
                  if(PrintLog) PrintFormat("🎯 TRAIL ticket=%I64u SL → %.2f", ticket, newSl);
               }
            }
         } else {
            if(ask < beStates[i].runExtreme) beStates[i].runExtreme = ask;
            double newSl = beStates[i].runExtreme + slDist;
            if(newSl < curSl) {
               if(trade.PositionModify(ticket, newSl, curTp)) {
                  if(PrintLog) PrintFormat("🎯 TRAIL ticket=%I64u SL → %.2f", ticket, newSl);
               }
            }
         }
      }
   }
}

//+------------------------------------------------------------------+
//| EOD force-close per session                                      |
//+------------------------------------------------------------------+
void ForceCloseSession(ulong &ticketRef, string sessionTag) {
   if(ticketRef == 0) return;
   if(PositionSelectByTicket(ticketRef)) {
      if(trade.PositionClose(ticketRef)) {
         string msg = StringFormat("🔚 EOD close %s ticket=%I64u", sessionTag, ticketRef);
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
   // BE Trail runs every tick (responsive)
   ManageBeTrail();

   // Bar-close logic only
   datetime curBar = iTime(_Symbol, PERIOD_M1, 0);
   if(curBar == lastBar) return;
   lastBar = curBar;

   datetime now = TimeCurrent();
   int curDay = ETDayOfMonth(now);
   int curMin = ETMinOfDay(now);

   // New day reset
   if(lastDay != -1 && curDay != lastDay) {
      ResetSessions();
   }
   lastDay = curDay;

   // Get prev + cur bar OHLC (bar 1 = closed prev, bar 0 = current forming)
   double po = iOpen(_Symbol, PERIOD_M1, 2);
   double ph = iHigh(_Symbol, PERIOD_M1, 2);
   double pl = iLow(_Symbol, PERIOD_M1, 2);
   double pc = iClose(_Symbol, PERIOD_M1, 2);
   double co = iOpen(_Symbol, PERIOD_M1, 1);
   double ch = iHigh(_Symbol, PERIOD_M1, 1);
   double cl = iLow(_Symbol, PERIOD_M1, 1);
   double cc = iClose(_Symbol, PERIOD_M1, 1);

   int curBarIdx = (int)(now / 60);

   // === ASIA ===
   if(AsiaEnable) {
      int asiaStart = AsiaBoxStartH * 60 + AsiaBoxStartM;
      int asiaEnd   = asiaStart + AsiaBoxDurMin;
      int asiaForce = (AsiaSessionEndH == 24 ? 1439 : AsiaSessionEndH * 60 - 1);
      UpdateBox(asiaBox, asiaStart, asiaEnd, ph, pl, curMin);
      if(curMin >= asiaEnd && curMin < asiaForce) {
         ProcessPullback(asiaBox, asiaTicket, "ASIA", po, ph, pl, pc, co, ch, cl, cc, curBarIdx);
      }
      if(curMin == asiaForce) ForceCloseSession(asiaTicket, "ASIA");
   }

   // === LONDON ===
   if(LonEnable) {
      int lonStart = LonBoxStartH * 60 + LonBoxStartM;
      int lonEnd   = lonStart + LonBoxDurMin;
      int lonForce = LonSessionEndH * 60 - 1;
      UpdateBox(lonBox, lonStart, lonEnd, ph, pl, curMin);
      if(curMin >= lonEnd && curMin < lonForce) {
         ProcessPullback(lonBox, lonTicket, "LON", po, ph, pl, pc, co, ch, cl, cc, curBarIdx);
      }
      if(curMin == lonForce) ForceCloseSession(lonTicket, "LON");
   }

   // === NY ===
   if(NYEnable) {
      int nyStart = NYBoxStartH * 60 + NYBoxStartM;
      int nyEnd   = nyStart + NYBoxDurMin;
      int nyForce = NYSessionEndH * 60 - 1;
      UpdateBox(nyBox, nyStart, nyEnd, ph, pl, curMin);
      if(curMin >= nyEnd && curMin < nyForce) {
         ProcessPullback(nyBox, nyTicket, "NY", po, ph, pl, pc, co, ch, cl, cc, curBarIdx);
      }
      if(curMin == nyForce) ForceCloseSession(nyTicket, "NY");
   }

   // Cleanup closed tickets from registry
   if(asiaTicket != 0 && !PositionSelectByTicket(asiaTicket)) asiaTicket = 0;
   if(lonTicket  != 0 && !PositionSelectByTicket(lonTicket))  lonTicket  = 0;
   if(nyTicket   != 0 && !PositionSelectByTicket(nyTicket))   nyTicket   = 0;
}

//+------------------------------------------------------------------+
