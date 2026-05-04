//+------------------------------------------------------------------+
//|                                                  PTBox_e37.mq5  |
//|                            PT BOX e37 — XAUUSD intraday indicator |
//|                            Wyckoff pre-session DIRECT model       |
//|                                                                  |
//|   Asia:   18:00/90m DIRECT  + body0%  + SL=0.7×bw + TP=1.5R      |
//|   London: 00:00/60m DIRECT  + body20% + SL=0.5×bw + TP=2.0R      |
//|   NY:     07:00/60m DIRECT  + body30% + SL=0.5×bw + TP=2.5R      |
//|                                                                  |
//|   5y backtest +9084 pts · OOS validated 316% retention            |
//|                                                                  |
//|   Setup: M1 chart, XAUUSD. Indicator detects box, fires entry     |
//|   signal with BUY/SELL label + SL/TP lines + Alert.               |
//|   Manual execution di order panel MT5.                            |
//+------------------------------------------------------------------+
#property copyright "PT Box e37 · Irfan 2026"
#property version   "1.00"
#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0

//+------------------------------------------------------------------+
//| User inputs                                                      |
//+------------------------------------------------------------------+
input group "═════ Display ═════"
input bool   ShowAsia        = true;
input bool   ShowLondon      = true;
input bool   ShowNY          = true;
input bool   ShowSignals     = true;
input bool   ShowSLTPLines   = true;
input bool   PlayAlertSound  = true;
input bool   PushToMobile    = true;

input group "═════ ET Timezone Offset ═════"
input int    ET_GMTOffset    = -4;       // ET = GMT-4 (EDT summer) or -5 (EST winter)
input int    Broker_GMTOffset= 0;        // your broker's server time vs GMT (check Tools→Options→Server)

input group "═════ Asia (e37) ═════"
input int    AsiaBoxStartH   = 18;       // ET hour
input int    AsiaBoxStartM   = 0;
input int    AsiaBoxDurMin   = 90;
input int    AsiaSessionEndH = 24;       // 24 = next-day midnight extended
input double AsiaSlBoxMult   = 0.7;
input double AsiaTpMult      = 1.5;
input double AsiaMinSlPts    = 3.0;
input double AsiaBodyPct     = 0.0;
input double AsiaMaxSlPts    = 30.0;

input group "═════ London (e37) ═════"
input int    LonBoxStartH    = 0;
input int    LonBoxStartM    = 0;
input int    LonBoxDurMin    = 60;
input int    LonSessionEndH  = 8;
input double LonSlBoxMult    = 0.5;
input double LonTpMult       = 2.0;
input double LonMinSlPts     = 3.0;
input double LonBodyPct      = 0.20;
input double LonMaxSlPts     = 15.0;

input group "═════ NY (e37) ═════"
input int    NYBoxStartH     = 7;
input int    NYBoxStartM     = 0;
input int    NYBoxDurMin     = 60;
input int    NYSessionEndH   = 12;
input double NYSlBoxMult     = 0.5;
input double NYTpMult        = 2.5;
input double NYMinSlPts      = 3.0;
input double NYBodyPct       = 0.30;
input double NYMaxSlPts      = 15.0;

input group "═════ Risk ═════"
input bool   UseMaxSlFilter  = true;
input double LotSize         = 0.02;
input double CapUSD          = 200.0;

//+------------------------------------------------------------------+
//| Globals — box state                                              |
//+------------------------------------------------------------------+
double asiaBoxHi = 0, asiaBoxLo = 0;
double asiaBxHiTmp = 0, asiaBxLoTmp = 0;
bool   asiaEnteredToday = false;
datetime asiaBoxDate = 0;

double lonBoxHi = 0, lonBoxLo = 0;
double lonBxHiTmp = 0, lonBxLoTmp = 0;
bool   lonEnteredToday = false;
datetime lonBoxDate = 0;

double nyBoxHi = 0, nyBoxLo = 0;
double nyBxHiTmp = 0, nyBxLoTmp = 0;
bool   nyEnteredToday = false;
datetime nyBoxDate = 0;

datetime lastDayProcessed = 0;
int      objectCounter = 0;

//+------------------------------------------------------------------+
//| Convert broker time → ET hour/minute                             |
//+------------------------------------------------------------------+
void GetETTime(datetime t, int &hh, int &mm, datetime &dayStart)
{
   int gmtSec = (int)t - Broker_GMTOffset * 3600;
   int etSec  = gmtSec + ET_GMTOffset * 3600;
   datetime etDt = (datetime)etSec;
   MqlDateTime dt;
   TimeToStruct(etDt, dt);
   hh = dt.hour;
   mm = dt.min;
   // Day start at ET 00:00
   dt.hour = 0; dt.min = 0; dt.sec = 0;
   dayStart = StructToTime(dt);
}

int ETMinuteOfDay(datetime t)
{
   int hh, mm; datetime ds;
   GetETTime(t, hh, mm, ds);
   return hh * 60 + mm;
}

datetime ETDayStart(datetime t)
{
   int hh, mm; datetime ds;
   GetETTime(t, hh, mm, ds);
   return ds;
}

//+------------------------------------------------------------------+
//| Pattern detectors                                                |
//+------------------------------------------------------------------+
bool IsBullPin(double o, double h, double l, double c)
{
   double rng = h - l;
   if (rng <= 0) return false;
   double body = MathAbs(c - o);
   if (body / rng > 0.30) return false;
   double lowerWick = MathMin(o, c) - l;
   return (lowerWick / rng) >= 0.50;
}
bool IsBearPin(double o, double h, double l, double c)
{
   double rng = h - l;
   if (rng <= 0) return false;
   double body = MathAbs(c - o);
   if (body / rng > 0.30) return false;
   double upperWick = h - MathMax(o, c);
   return (upperWick / rng) >= 0.50;
}
bool IsBullEngulf(double po, double pc, double o, double c)
{
   return pc < po && c > o && o <= pc && c >= po;
}
bool IsBearEngulf(double po, double pc, double o, double c)
{
   return pc > po && c < o && o >= pc && c <= po;
}
bool IsInsideBar(double ph, double pl, double h, double l)
{
   return h < ph && l > pl;
}
bool AnyBull(double po, double ph, double pl, double pc, double o, double h, double l, double c)
{
   return IsBullPin(o, h, l, c) || IsBullEngulf(po, pc, o, c) || IsInsideBar(ph, pl, h, l);
}
bool AnyBear(double po, double ph, double pl, double pc, double o, double h, double l, double c)
{
   return IsBearPin(o, h, l, c) || IsBearEngulf(po, pc, o, c) || IsInsideBar(ph, pl, h, l);
}

//+------------------------------------------------------------------+
//| Object drawing helpers                                           |
//+------------------------------------------------------------------+
string NextName(string prefix)
{
   objectCounter++;
   return prefix + "_" + IntegerToString(objectCounter) + "_" + IntegerToString((int)TimeCurrent());
}

void DrawBox(string nm, datetime t1, double pr1, datetime t2, double pr2, color clr)
{
   ObjectCreate(0, nm, OBJ_RECTANGLE, 0, t1, pr1, t2, pr2);
   ObjectSetInteger(0, nm, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, nm, OBJPROP_BACK,  true);
   ObjectSetInteger(0, nm, OBJPROP_FILL,  true);
   ObjectSetInteger(0, nm, OBJPROP_STYLE, STYLE_SOLID);
   ObjectSetInteger(0, nm, OBJPROP_WIDTH, 1);
}

void DrawHLine(string nm, datetime t1, double price, datetime t2, color clr, ENUM_LINE_STYLE style, int width)
{
   ObjectCreate(0, nm, OBJ_TREND, 0, t1, price, t2, price);
   ObjectSetInteger(0, nm, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, nm, OBJPROP_STYLE, style);
   ObjectSetInteger(0, nm, OBJPROP_WIDTH, width);
   ObjectSetInteger(0, nm, OBJPROP_RAY_RIGHT, false);
}

void DrawText(string nm, datetime t, double price, string txt, color clr, int fontsize)
{
   ObjectCreate(0, nm, OBJ_TEXT, 0, t, price);
   ObjectSetString(0,  nm, OBJPROP_TEXT, txt);
   ObjectSetInteger(0, nm, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, nm, OBJPROP_FONTSIZE, fontsize);
   ObjectSetString(0,  nm, OBJPROP_FONT, "Arial Bold");
}

//+------------------------------------------------------------------+
//| Process entry signal (called when entry condition met)           |
//+------------------------------------------------------------------+
void FireEntry(string sessLabel, color sessCol, bool isLong, double entryPx,
               double slPx, double tpPx, datetime entryTime, double slDistFromEntry,
               double maxSl)
{
   // Risk filter
   if (UseMaxSlFilter && slDistFromEntry > maxSl)
   {
      string skipNm = NextName(sessLabel + "_SKIP");
      DrawText(skipNm, entryTime,
               isLong ? entryPx - 5 * Point() : entryPx + 5 * Point(),
               "SKIP " + sessLabel + " SL>" + DoubleToString(maxSl, 0),
               clrRed, 8);
      return;
   }

   string actionTxt = isLong ? "BUY" : "SELL";
   color  actionCol = isLong ? clrLime : clrRed;

   // Entry marker
   if (ShowSignals)
   {
      string entNm = NextName(sessLabel + "_ENT");
      DrawText(entNm, entryTime,
               isLong ? entryPx - 3 * Point() : entryPx + 3 * Point(),
               actionTxt + " " + sessLabel,
               actionCol, 10);
   }

   // SL/TP lines
   if (ShowSLTPLines)
   {
      datetime tEnd = entryTime + 60 * 60;  // extend 1h
      string slNm = NextName(sessLabel + "_SL");
      DrawHLine(slNm, entryTime, slPx, tEnd, clrRed, STYLE_DASH, 2);
      string slTxt = NextName(sessLabel + "_SLtxt");
      DrawText(slTxt, tEnd, slPx, "SL " + DoubleToString(slPx, _Digits), clrRed, 8);

      string tpNm = NextName(sessLabel + "_TP");
      DrawHLine(tpNm, entryTime, tpPx, tEnd, clrLime, STYLE_SOLID, 2);
      string tpTxt = NextName(sessLabel + "_TPtxt");
      DrawText(tpTxt, tEnd, tpPx, "TP " + DoubleToString(tpPx, _Digits), clrLime, 8);

      string enTxt = NextName(sessLabel + "_ENtxt");
      DrawText(enTxt, tEnd, entryPx, "@ " + DoubleToString(entryPx, _Digits), clrSilver, 8);
   }

   // Risk math
   double lossUsd = slDistFromEntry * LotSize * 100;
   double pctCap  = lossUsd / CapUSD * 100;

   // Alert
   string msg = StringFormat("%s %s %s @ %.*f | SL %.*f | TP %.*f | Risk -$%.2f (%.1f%%)",
                              isLong ? "🟢" : "🔴",
                              actionTxt, sessLabel,
                              _Digits, entryPx,
                              _Digits, slPx,
                              _Digits, tpPx,
                              lossUsd, pctCap);

   if (PlayAlertSound) Alert(msg);
   if (PushToMobile)   SendNotification(msg);
   Print(msg);
}

//+------------------------------------------------------------------+
//| OnInit                                                           |
//+------------------------------------------------------------------+
int OnInit()
{
   IndicatorSetString(INDICATOR_SHORTNAME, "PT Box e37");
   ObjectsDeleteAll(0, "PTBox");
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| OnDeinit — clean up objects                                      |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   ObjectsDeleteAll(0, "PTBox");
}

//+------------------------------------------------------------------+
//| OnCalculate — main loop                                          |
//+------------------------------------------------------------------+
int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double &open[],
                const double &high[],
                const double &low[],
                const double &close[],
                const long &tick_volume[],
                const long &volume[],
                const int &spread[])
{
   int start = (prev_calculated > 1) ? prev_calculated - 1 : 1;

   for (int i = start; i < rates_total; i++)
   {
      datetime t = time[i];
      datetime dayStart = ETDayStart(t);
      int mod = ETMinuteOfDay(t);

      // === New day reset (ET midnight crossing) ===
      if (dayStart != lastDayProcessed)
      {
         asiaBoxHi = 0; asiaBoxLo = 0; asiaBxHiTmp = 0; asiaBxLoTmp = 0;
         asiaEnteredToday = false;
         lonBoxHi = 0;  lonBoxLo = 0;  lonBxHiTmp = 0;  lonBxLoTmp = 0;
         lonEnteredToday = false;
         nyBoxHi = 0;   nyBoxLo = 0;   nyBxHiTmp = 0;   nyBxLoTmp = 0;
         nyEnteredToday = false;
         lastDayProcessed = dayStart;
      }

      // === Asia box accumulation ===
      int asiaStart = AsiaBoxStartH * 60 + AsiaBoxStartM;
      int asiaEnd   = asiaStart + AsiaBoxDurMin;
      if (mod >= asiaStart && mod < asiaEnd)
      {
         if (asiaBxHiTmp == 0) { asiaBxHiTmp = high[i]; asiaBxLoTmp = low[i]; }
         else { asiaBxHiTmp = MathMax(asiaBxHiTmp, high[i]); asiaBxLoTmp = MathMin(asiaBxLoTmp, low[i]); }
      }
      if (mod == asiaEnd && asiaBxHiTmp != 0)
      {
         asiaBoxHi = asiaBxHiTmp; asiaBoxLo = asiaBxLoTmp;
         asiaBoxDate = t;
         if (ShowAsia)
         {
            string boxNm = NextName("PTBox_Asia_BX");
            DrawBox(boxNm, t - AsiaBoxDurMin * 60, asiaBoxHi, t + 60 * 60 * 6, asiaBoxLo, clrDarkGreen);
         }
      }

      // === London box accumulation ===
      int lonStart = LonBoxStartH * 60 + LonBoxStartM;
      int lonEnd   = lonStart + LonBoxDurMin;
      if (mod >= lonStart && mod < lonEnd)
      {
         if (lonBxHiTmp == 0) { lonBxHiTmp = high[i]; lonBxLoTmp = low[i]; }
         else { lonBxHiTmp = MathMax(lonBxHiTmp, high[i]); lonBxLoTmp = MathMin(lonBxLoTmp, low[i]); }
      }
      if (mod == lonEnd && lonBxHiTmp != 0)
      {
         lonBoxHi = lonBxHiTmp; lonBoxLo = lonBxLoTmp;
         lonBoxDate = t;
         if (ShowLondon)
         {
            string boxNm = NextName("PTBox_Lon_BX");
            DrawBox(boxNm, t - LonBoxDurMin * 60, lonBoxHi, t + 60 * 60 * 8, lonBoxLo, clrDarkBlue);
         }
      }

      // === NY box accumulation ===
      int nyStart = NYBoxStartH * 60 + NYBoxStartM;
      int nyEnd   = nyStart + NYBoxDurMin;
      if (mod >= nyStart && mod < nyEnd)
      {
         if (nyBxHiTmp == 0) { nyBxHiTmp = high[i]; nyBxLoTmp = low[i]; }
         else { nyBxHiTmp = MathMax(nyBxHiTmp, high[i]); nyBxLoTmp = MathMin(nyBxLoTmp, low[i]); }
      }
      if (mod == nyEnd && nyBxHiTmp != 0)
      {
         nyBoxHi = nyBxHiTmp; nyBoxLo = nyBxLoTmp;
         nyBoxDate = t;
         if (ShowNY)
         {
            string boxNm = NextName("PTBox_NY_BX");
            DrawBox(boxNm, t - NYBoxDurMin * 60, nyBoxHi, t + 60 * 60 * 5, nyBoxLo, clrDarkOrange);
         }
      }

      // === Asia DIRECT entry ===
      int asiaSessEnd = (AsiaSessionEndH == 24 ? 24 * 60 : AsiaSessionEndH * 60);
      if (ShowAsia && asiaBoxHi != 0 && !asiaEnteredToday && i >= 1 &&
          mod >= asiaEnd && mod < asiaSessEnd)
      {
         double bw   = asiaBoxHi - asiaBoxLo;
         double thr  = AsiaBodyPct * bw;
         double sld  = MathMax(AsiaMinSlPts, AsiaSlBoxMult * bw);
         if (close[i] > asiaBoxHi && (close[i] - asiaBoxHi) >= thr &&
             AnyBull(open[i-1], high[i-1], low[i-1], close[i-1],
                     open[i],   high[i],   low[i],   close[i]))
         {
            double slPx = asiaBoxLo - sld;
            double tpPx = close[i] + AsiaTpMult * sld;
            FireEntry("Asia", clrLime, true, close[i], slPx, tpPx, t,
                      MathAbs(close[i] - slPx), AsiaMaxSlPts);
            asiaEnteredToday = true;
         }
         else if (close[i] < asiaBoxLo && (asiaBoxLo - close[i]) >= thr &&
                  AnyBear(open[i-1], high[i-1], low[i-1], close[i-1],
                          open[i],   high[i],   low[i],   close[i]))
         {
            double slPx = asiaBoxHi + sld;
            double tpPx = close[i] - AsiaTpMult * sld;
            FireEntry("Asia", clrRed, false, close[i], slPx, tpPx, t,
                      MathAbs(close[i] - slPx), AsiaMaxSlPts);
            asiaEnteredToday = true;
         }
      }

      // === London DIRECT entry ===
      int lonSessEnd = LonSessionEndH * 60;
      if (ShowLondon && lonBoxHi != 0 && !lonEnteredToday && i >= 1 &&
          mod >= lonEnd && mod < lonSessEnd)
      {
         double bw   = lonBoxHi - lonBoxLo;
         double thr  = LonBodyPct * bw;
         double sld  = MathMax(LonMinSlPts, LonSlBoxMult * bw);
         if (close[i] > lonBoxHi && (close[i] - lonBoxHi) >= thr &&
             AnyBull(open[i-1], high[i-1], low[i-1], close[i-1],
                     open[i],   high[i],   low[i],   close[i]))
         {
            double slPx = lonBoxLo - sld;
            double tpPx = close[i] + LonTpMult * sld;
            FireEntry("London", clrDeepSkyBlue, true, close[i], slPx, tpPx, t,
                      MathAbs(close[i] - slPx), LonMaxSlPts);
            lonEnteredToday = true;
         }
         else if (close[i] < lonBoxLo && (lonBoxLo - close[i]) >= thr &&
                  AnyBear(open[i-1], high[i-1], low[i-1], close[i-1],
                          open[i],   high[i],   low[i],   close[i]))
         {
            double slPx = lonBoxHi + sld;
            double tpPx = close[i] - LonTpMult * sld;
            FireEntry("London", clrRed, false, close[i], slPx, tpPx, t,
                      MathAbs(close[i] - slPx), LonMaxSlPts);
            lonEnteredToday = true;
         }
      }

      // === NY DIRECT entry ===
      int nySessEnd = NYSessionEndH * 60;
      if (ShowNY && nyBoxHi != 0 && !nyEnteredToday && i >= 1 &&
          mod >= nyEnd && mod < nySessEnd)
      {
         double bw   = nyBoxHi - nyBoxLo;
         double thr  = NYBodyPct * bw;
         double sld  = MathMax(NYMinSlPts, NYSlBoxMult * bw);
         if (close[i] > nyBoxHi && (close[i] - nyBoxHi) >= thr &&
             AnyBull(open[i-1], high[i-1], low[i-1], close[i-1],
                     open[i],   high[i],   low[i],   close[i]))
         {
            double slPx = nyBoxLo - sld;
            double tpPx = close[i] + NYTpMult * sld;
            FireEntry("NY", clrOrange, true, close[i], slPx, tpPx, t,
                      MathAbs(close[i] - slPx), NYMaxSlPts);
            nyEnteredToday = true;
         }
         else if (close[i] < nyBoxLo && (nyBoxLo - close[i]) >= thr &&
                  AnyBear(open[i-1], high[i-1], low[i-1], close[i-1],
                          open[i],   high[i],   low[i],   close[i]))
         {
            double slPx = nyBoxHi + sld;
            double tpPx = close[i] - NYTpMult * sld;
            FireEntry("NY", clrRed, false, close[i], slPx, tpPx, t,
                      MathAbs(close[i] - slPx), NYMaxSlPts);
            nyEnteredToday = true;
         }
      }
   }

   return rates_total;
}
//+------------------------------------------------------------------+
