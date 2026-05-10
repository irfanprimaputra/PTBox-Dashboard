//+------------------------------------------------------------------+
//|                                    PTBox_e44_v14_indicator.mq5  |
//|         PT BOX e44 PULLBACK v14 — INDICATOR (visual only)       |
//|         Mirror of Pine v14: e44 PB state machine + BE Trail     |
//|                                                                  |
//|   VISUAL ONLY. NO AUTO-TRADE. Manual execution di order panel.   |
//|   - Detect e44 PB setup per sesi (Asia/London/NY)                |
//|   - Draw box + breakout direction                                |
//|   - Show BUY/SELL entry signal label                             |
//|   - Draw SL/TP lines                                             |
//|   - Show 🛡️ BE marker saat virtual trade reach +1R favor       |
//|   - Show 🎯 TRAIL marker saat trail update SL                    |
//|   - Push notif HP via SendNotification()                         |
//|                                                                  |
//|   Backtest reference (Pine v14 5y):                               |
//|     WR 51.2% · PnL +$4349 · worst trade -$74                     |
//+------------------------------------------------------------------+
#property copyright "PT Box e44 v14 Indicator · Irfan 2026"
#property version   "14.10"
#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0
#property strict

//+------------------------------------------------------------------+
//| Inputs                                                            |
//+------------------------------------------------------------------+
input group "═════ Display ═════"
input bool   ShowBoxes        = true;
input bool   ShowSignals      = true;
input bool   ShowSLTPLines    = true;
input bool   ShowBeMarkers    = true;
input color  AsiaColor        = clrLime;
input color  LonColor         = clrDeepSkyBlue;
input color  NYColor          = clrOrange;

input group "═════ Notifications ═════"
input bool   PushToMobile     = true;
input bool   PlayAlertSound   = true;
input bool   ShowAlertPopup   = false;

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
input int    NYEntryDelayMin  = 25;

input group "═════ e44 PULLBACK Params ═════"
input double PbRetestTol      = 3.0;
input double PbSlBuffer       = 2.0;
input double PbTpMult         = 2.0;
input int    PbMaxWaitBars    = 60;

input group "═════ 🛡️ BE Trail (Phase 17 V5) ═════"
input bool   UseBeTrail       = true;
input double BeTriggerR       = 1.0;

input group "═════ Risk Info ═════"
input double LotSize          = 0.02;
input double CapUSD           = 200;

//+------------------------------------------------------------------+
//| Globals — virtual trade state (for visualization)                |
//+------------------------------------------------------------------+
struct BoxState {
   double  hi;
   double  lo;
   bool    formed;
   datetime formedAt;
   int     pbState;
   int     pbBkDir;
   datetime pbBkTime;
   double  pbExtreme;
   int     attempts;
};

struct VirtualTrade {
   bool   active;
   int    dir;            // 1=long, -1=short
   double entry;
   double sl;
   double slOrig;
   double tp;
   datetime openTime;
   bool   beTriggered;
   double runExtreme;
   string sessionTag;
};

BoxState     asiaBox, lonBox, nyBox;
VirtualTrade asiaVT, lonVT, nyVT;
int          lastDay = -1;
string       OBJ_PREFIX = "PTBox_v14_";

//+------------------------------------------------------------------+
//| Init / Deinit                                                    |
//+------------------------------------------------------------------+
int OnInit() {
   ResetSessions();
   PrintFormat("[PT Box v14 Indicator] init | BE Trail=%s | Lot=%.2f",
               UseBeTrail ? "ON" : "OFF", LotSize);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) {
   ObjectsDeleteAll(0, OBJ_PREFIX);
   PrintFormat("[PT Box v14 Indicator] deinit reason=%d", reason);
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
   bx.pbState = 0; bx.pbBkDir = 0; bx.pbBkTime = 0;
   bx.pbExtreme = 0; bx.attempts = 0;
}

void ResetVT(VirtualTrade &vt) {
   vt.active = false; vt.dir = 0; vt.entry = 0; vt.sl = 0; vt.slOrig = 0; vt.tp = 0;
   vt.openTime = 0; vt.beTriggered = false; vt.runExtreme = 0; vt.sessionTag = "";
}

void ResetSessions() {
   ResetBox(asiaBox); ResetBox(lonBox); ResetBox(nyBox);
   ResetVT(asiaVT); ResetVT(lonVT); ResetVT(nyVT);
}

//+------------------------------------------------------------------+
//| Pattern detection                                                |
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
//| Box update                                                       |
//+------------------------------------------------------------------+
void UpdateBox(BoxState &bx, int startMin, int endMin, double ph, double pl, int curMin, color col, string sessionTag) {
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
      // Draw box
      if(ShowBoxes) DrawBox(bx, col, sessionTag);
      Print("[", sessionTag, "] BOX FORMED hi=", DoubleToString(bx.hi, 2), " lo=", DoubleToString(bx.lo, 2),
            " bw=", DoubleToString(bx.hi - bx.lo, 2));
   }
}

void DrawBox(BoxState &bx, color col, string tag) {
   string boxName = OBJ_PREFIX + tag + "_box_" + IntegerToString(ETDayOfMonth(TimeCurrent()));
   datetime endT = TimeCurrent() + 14400;  // 4hr forward visual extension
   ObjectCreate(0, boxName, OBJ_RECTANGLE, 0, bx.formedAt - 5400, bx.hi, endT, bx.lo);
   ObjectSetInteger(0, boxName, OBJPROP_COLOR, col);
   ObjectSetInteger(0, boxName, OBJPROP_FILL, true);
   ObjectSetInteger(0, boxName, OBJPROP_BACK, true);
   ObjectSetInteger(0, boxName, OBJPROP_STYLE, STYLE_DOT);
   color fillCol = ColorAlpha(col, 30);
   ObjectSetInteger(0, boxName, OBJPROP_BGCOLOR, fillCol);
}

color ColorAlpha(color c, int alpha) {
   return (color)(c | (alpha << 24));
}

//+------------------------------------------------------------------+
//| e44 PB state machine + virtual trade tracking                    |
//+------------------------------------------------------------------+
void ProcessPullback(BoxState &bx, VirtualTrade &vt, string sessionTag, int maxAtt, color col,
                     double po, double ph, double pl, double pc,
                     double co, double ch, double cl, double cc, datetime curBarTime) {
   if(!bx.formed) return;
   if(bx.attempts >= maxAtt) return;
   if(vt.active) return;

   double bw = bx.hi - bx.lo;
   if(bw < 1) return;

   if(bx.pbState == 0) {
      if(cc > bx.hi) {
         bx.pbState = 1; bx.pbBkDir = 1; bx.pbBkTime = curBarTime; bx.pbExtreme = cl;
         Print("[", sessionTag, "] BREAKOUT UP @ ", DoubleToString(cc, 2));
      } else if(cc < bx.lo) {
         bx.pbState = 1; bx.pbBkDir = -1; bx.pbBkTime = curBarTime; bx.pbExtreme = ch;
         Print("[", sessionTag, "] BREAKOUT DOWN @ ", DoubleToString(cc, 2));
      }
      return;
   }

   if(bx.pbState == 1) {
      int barsSinceBreak = (int)((curBarTime - bx.pbBkTime) / 60);
      if(barsSinceBreak > PbMaxWaitBars) {
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
      if(bx.pbBkDir == 1) {
         if(cl >= bx.hi - PbRetestTol && IsBullPattern(po, ph, pl, pc, co, ch, cl, cc)) {
            double slPx = MathMin(cl, pl) - PbSlBuffer;
            double slDist = cc - slPx;
            if(slDist <= 0 || slDist > 30) {
               bx.attempts++; bx.pbState = 0; return;
            }
            double tpPx = cc + PbTpMult * slDist;
            FireSignal(vt, true, cc, slPx, tpPx, sessionTag, col, slDist, curBarTime);
            bx.attempts++; bx.pbState = 0;
         }
      } else {
         if(ch <= bx.lo + PbRetestTol && IsBearPattern(po, ph, pl, pc, co, ch, cl, cc)) {
            double slPx = MathMax(ch, ph) + PbSlBuffer;
            double slDist = slPx - cc;
            if(slDist <= 0 || slDist > 30) {
               bx.attempts++; bx.pbState = 0; return;
            }
            double tpPx = cc - PbTpMult * slDist;
            FireSignal(vt, false, cc, slPx, tpPx, sessionTag, col, slDist, curBarTime);
            bx.attempts++; bx.pbState = 0;
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Fire entry signal (visual + alert + virtual trade register)      |
//+------------------------------------------------------------------+
void FireSignal(VirtualTrade &vt, bool isLong, double entry, double sl, double tp,
                string sessionTag, color col, double slDist, datetime t) {
   vt.active = true; vt.dir = isLong ? 1 : -1; vt.entry = entry; vt.sl = sl;
   vt.slOrig = sl; vt.tp = tp; vt.openTime = t; vt.beTriggered = false;
   vt.runExtreme = entry; vt.sessionTag = sessionTag;

   double lossUsd = slDist * LotSize * 100;
   double pctCap = lossUsd / CapUSD * 100;

   string msg = StringFormat("🌊 PT Box v14 %s | %s @ %.2f | SL %.2f | TP %.2f | Risk %.1fpt = -$%.2f (%.1f%% cap)",
                             sessionTag, isLong ? "BUY" : "SELL", entry, sl, tp, slDist, lossUsd, pctCap);
   Print(msg);
   if(PushToMobile) SendNotification(msg);
   if(PlayAlertSound) PlaySound("alert.wav");
   if(ShowAlertPopup) Alert(msg);

   // Visual entry marker
   if(ShowSignals) DrawEntryLabel(t, entry, isLong, sessionTag, col);
   if(ShowSLTPLines) DrawSLTP(vt, col);
}

void DrawEntryLabel(datetime t, double price, bool isLong, string tag, color col) {
   string name = OBJ_PREFIX + tag + "_entry_" + TimeToString(t, TIME_DATE | TIME_SECONDS);
   ObjectCreate(0, name, OBJ_ARROW, 0, t, price);
   ObjectSetInteger(0, name, OBJPROP_ARROWCODE, isLong ? 233 : 234);
   ObjectSetInteger(0, name, OBJPROP_COLOR, col);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, 3);

   string lblName = name + "_lbl";
   ObjectCreate(0, lblName, OBJ_TEXT, 0, t, isLong ? price - 5 : price + 5);
   ObjectSetString(0, lblName, OBJPROP_TEXT, (isLong ? "🌊 BUY " : "🌊 SELL ") + tag);
   ObjectSetInteger(0, lblName, OBJPROP_COLOR, clrWhite);
   ObjectSetInteger(0, lblName, OBJPROP_FONTSIZE, 9);
}

void DrawSLTP(VirtualTrade &vt, color col) {
   string base = OBJ_PREFIX + vt.sessionTag + "_" + TimeToString(vt.openTime, TIME_DATE | TIME_SECONDS);
   datetime endT = vt.openTime + 14400;

   string slName = base + "_sl";
   ObjectCreate(0, slName, OBJ_TREND, 0, vt.openTime, vt.sl, endT, vt.sl);
   ObjectSetInteger(0, slName, OBJPROP_COLOR, clrRed);
   ObjectSetInteger(0, slName, OBJPROP_STYLE, STYLE_DASH);
   ObjectSetInteger(0, slName, OBJPROP_WIDTH, 1);

   string tpName = base + "_tp";
   ObjectCreate(0, tpName, OBJ_TREND, 0, vt.openTime, vt.tp, endT, vt.tp);
   ObjectSetInteger(0, tpName, OBJPROP_COLOR, clrLime);
   ObjectSetInteger(0, tpName, OBJPROP_STYLE, STYLE_DASH);
   ObjectSetInteger(0, tpName, OBJPROP_WIDTH, 1);

   string entName = base + "_entry_line";
   ObjectCreate(0, entName, OBJ_TREND, 0, vt.openTime, vt.entry, endT, vt.entry);
   ObjectSetInteger(0, entName, OBJPROP_COLOR, col);
   ObjectSetInteger(0, entName, OBJPROP_STYLE, STYLE_DOT);
}

void UpdateSLLine(VirtualTrade &vt, double newSL, string markerText) {
   string base = OBJ_PREFIX + vt.sessionTag + "_" + TimeToString(vt.openTime, TIME_DATE | TIME_SECONDS);
   string slName = base + "_sl";
   datetime now = TimeCurrent();
   datetime endT = now + 14400;
   ObjectMove(0, slName, 0, vt.openTime, newSL);
   ObjectMove(0, slName, 1, endT, newSL);
   if(ShowBeMarkers) {
      string markerName = base + "_be_" + TimeToString(now, TIME_DATE | TIME_SECONDS);
      ObjectCreate(0, markerName, OBJ_ARROW, 0, now, newSL);
      ObjectSetInteger(0, markerName, OBJPROP_ARROWCODE, 251);
      ObjectSetInteger(0, markerName, OBJPROP_COLOR, clrAqua);
      string lblName = markerName + "_lbl";
      ObjectCreate(0, lblName, OBJ_TEXT, 0, now, vt.dir == 1 ? newSL - 3 : newSL + 3);
      ObjectSetString(0, lblName, OBJPROP_TEXT, markerText);
      ObjectSetInteger(0, lblName, OBJPROP_COLOR, clrAqua);
      ObjectSetInteger(0, lblName, OBJPROP_FONTSIZE, 8);
   }
}

//+------------------------------------------------------------------+
//| BE Trail manager + exit detection (virtual)                      |
//+------------------------------------------------------------------+
void ManageVirtualTrade(VirtualTrade &vt) {
   if(!vt.active) return;
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double cur = vt.dir == 1 ? bid : ask;

   // Exit check (virtual)
   bool exited = false;
   string exitReason = "";
   double exitPx = 0;
   if(vt.dir == 1) {
      if(bid <= vt.sl) { exited = true; exitPx = vt.sl;
         exitReason = vt.beTriggered && MathAbs(vt.sl - vt.entry) <= 0.5 ? "BE" : (vt.beTriggered ? "TRAIL" : "SL");
      }
      else if(bid >= vt.tp) { exited = true; exitPx = vt.tp; exitReason = "TP"; }
   } else {
      if(ask >= vt.sl) { exited = true; exitPx = vt.sl;
         exitReason = vt.beTriggered && MathAbs(vt.sl - vt.entry) <= 0.5 ? "BE" : (vt.beTriggered ? "TRAIL" : "SL");
      }
      else if(ask <= vt.tp) { exited = true; exitPx = vt.tp; exitReason = "TP"; }
   }

   if(exited) {
      double pnl = (vt.dir == 1 ? exitPx - vt.entry : vt.entry - exitPx);
      string emoji = exitReason == "TP" ? "✅" : (exitReason == "BE" ? "🛡️" : (exitReason == "TRAIL" ? "🎯" : "❌"));
      string msg = StringFormat("%s %s VIRTUAL EXIT %s @ %.2f | PnL %.2fpt = $%.2f @ 0.02 lot",
                                emoji, vt.sessionTag, exitReason, exitPx, pnl, pnl * LotSize * 100);
      Print(msg);
      if(PushToMobile) SendNotification(msg);
      if(PlayAlertSound) PlaySound("alert.wav");
      DrawExitMarker(vt, exitPx, exitReason);
      ResetVT(vt);
      return;
   }

   // BE Trail logic
   if(!UseBeTrail) return;
   double slDist = MathAbs(vt.entry - vt.slOrig);

   if(!vt.beTriggered) {
      double favor = vt.dir == 1 ? (cur - vt.entry) : (vt.entry - cur);
      double trigger = BeTriggerR * slDist;
      if(favor >= trigger) {
         vt.sl = vt.entry;
         vt.beTriggered = true;
         vt.runExtreme = cur;
         UpdateSLLine(vt, vt.sl, "🛡️ BE");
         string msg = StringFormat("🛡️ BE ARMED %s | SL → entry %.2f", vt.sessionTag, vt.entry);
         Print(msg);
         if(PushToMobile) SendNotification(msg);
      }
   } else {
      if(vt.dir == 1) {
         if(cur > vt.runExtreme) vt.runExtreme = cur;
         double newSl = vt.runExtreme - slDist;
         if(newSl > vt.sl) {
            vt.sl = newSl;
            UpdateSLLine(vt, vt.sl, "🎯");
         }
      } else {
         if(cur < vt.runExtreme) vt.runExtreme = cur;
         double newSl = vt.runExtreme + slDist;
         if(newSl < vt.sl) {
            vt.sl = newSl;
            UpdateSLLine(vt, vt.sl, "🎯");
         }
      }
   }
}

void DrawExitMarker(VirtualTrade &vt, double exitPx, string reason) {
   datetime now = TimeCurrent();
   string name = OBJ_PREFIX + vt.sessionTag + "_exit_" + TimeToString(vt.openTime, TIME_DATE | TIME_SECONDS);
   ObjectCreate(0, name, OBJ_TEXT, 0, now, exitPx);
   string symbol = reason == "TP" ? "✅" : (reason == "BE" ? "🛡️" : (reason == "TRAIL" ? "🎯" : "❌"));
   ObjectSetString(0, name, OBJPROP_TEXT, symbol + " " + reason + " " + vt.sessionTag);
   color col = (reason == "TP" || reason == "TRAIL") ? clrLime : (reason == "BE" ? clrAqua : clrRed);
   ObjectSetInteger(0, name, OBJPROP_COLOR, col);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 10);
}

//+------------------------------------------------------------------+
//| OnTick                                                           |
//+------------------------------------------------------------------+
datetime lastBar = 0;

int OnCalculate(const int rates_total, const int prev_calculated,
                const datetime &time[], const double &open[],
                const double &high[], const double &low[], const double &close[],
                const long &tick_volume[], const long &volume[],
                const int &spread[]) {
   // Manage virtual trades every tick
   ManageVirtualTrade(asiaVT);
   ManageVirtualTrade(lonVT);
   ManageVirtualTrade(nyVT);

   // Bar-close logic only
   if(rates_total < 3) return rates_total;
   datetime curBar = time[rates_total - 1];
   if(curBar == lastBar) return rates_total;
   lastBar = curBar;

   datetime now = TimeCurrent();
   int curDay = ETDayOfMonth(now);
   int curMin = ETMinOfDay(now);

   if(lastDay != -1 && curDay != lastDay) ResetSessions();
   lastDay = curDay;

   int idx = rates_total - 2;  // last closed bar
   if(idx < 1) return rates_total;
   double po = open[idx-1], ph = high[idx-1], pl = low[idx-1], pc = close[idx-1];
   double co = open[idx],   ch = high[idx],   cl = low[idx],   cc = close[idx];

   if(AsiaEnable) {
      int s = AsiaBoxStartH * 60 + AsiaBoxStartM;
      int e = s + AsiaBoxDurMin;
      int f = (AsiaSessionEndH == 24 ? 1439 : AsiaSessionEndH * 60 - 1);
      UpdateBox(asiaBox, s, e, ph, pl, curMin, AsiaColor, "ASIA");
      if(curMin >= e && curMin < f) {
         ProcessPullback(asiaBox, asiaVT, "ASIA", AsiaMaxAttempt, AsiaColor,
                         po, ph, pl, pc, co, ch, cl, cc, time[idx]);
      }
   }

   if(LonEnable) {
      int s = LonBoxStartH * 60 + LonBoxStartM;
      int e = s + LonBoxDurMin;
      int f = LonSessionEndH * 60 - 1;
      UpdateBox(lonBox, s, e, ph, pl, curMin, LonColor, "LON");
      if(curMin >= e && curMin < f) {
         ProcessPullback(lonBox, lonVT, "LON", LonMaxAttempt, LonColor,
                         po, ph, pl, pc, co, ch, cl, cc, time[idx]);
      }
   }

   if(NYEnable) {
      int s = NYBoxStartH * 60 + NYBoxStartM;
      int e = s + NYBoxDurMin;
      int f = NYSessionEndH * 60 - 1;
      UpdateBox(nyBox, s, e, ph, pl, curMin, NYColor, "NY");
      if(curMin >= e + NYEntryDelayMin && curMin < f) {
         ProcessPullback(nyBox, nyVT, "NY", NYMaxAttempt, NYColor,
                         po, ph, pl, pc, co, ch, cl, cc, time[idx]);
      }
   }

   return rates_total;
}

//+------------------------------------------------------------------+
