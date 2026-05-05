//+------------------------------------------------------------------+
//|  PT Box — NY Session Indicator                               |
//|  Visual: Box, BUY/SELL labels, SL/TP lines, Stats table         |
//|  Logic: Breakout + Pullback ke box edge                         |
//|  Timezone: NY Time (UTC-4) via America/New_York                 |
//+------------------------------------------------------------------+
#property copyright   "PT Box System — Irfan"
#property version     "1.00"
#property indicator_chart_window
#property indicator_plots 0

//--- Input Parameters
input group "=== BOX SETTINGS ==="
input int    BoxHour     = 9;     // Box Hour (NY Time / UTC-4)
input int    BoxMinute   = 3;    // Box Minute
input int    BoxDuration = 5;     // Box Duration (minutes)

input group "=== RISK SETTINGS ==="
input double SL_Buffer  = 3.0;   // SL Buffer (points)
input double TP1_Points = 9.0;   // TP1 (points)
input double TP2_Points = 18.0;  // TP2 (points)
input int    MaxAttempts = 3;     // Max Attempts per day

input group "=== DISPLAY SETTINGS ==="
input bool   ShowBox    = true;   // Show PT Box
input bool   ShowSignals= true;   // Show BUY/SELL Labels
input bool   ShowLines  = true;   // Show SL/TP Lines
input color  BoxColor   = clrMediumOrchid;  // Box Color
input color  BuyColor   = clrTeal;          // BUY Label Color
input color  SellColor  = clrTeal;          // SELL Label Color
input color  SL_Color   = clrRed;           // SL Line Color
input color  TP1_Color  = clrLime;          // TP1 Line Color
input color  TP2_Color  = clrGreen;         // TP2 Line Color
input int    BoxTransp  = 85;     // Box Transparency (0-100)

//--- Global State
double   bx_hi = 0, bx_lo = 0;
bool     bx_forming = false, bx_ready = false;
double   day_hi = 0, day_lo = 0;
int      attempt = 0, bk_dir = 0;
bool     in_trade = false;
double   entry_px = 0, sl_px = 0, tp1_px = 0, tp2_px = 0;
bool     day_done = false;
datetime bk_bar_time = 0, sl_bar_time = 0;
datetime last_box_time = 0;

//--- Stats
int    total_win = 0, total_loss = 0, total_chop = 0;
int    total_tp1 = 0, total_tp2 = 0;
double total_pnl = 0.0;

//--- Object name helpers
string pfx = "PTBox_NY_";

//+------------------------------------------------------------------+
int OnInit()
{
   Print("PT Box London Indicator v1.00 | ",
         BoxHour,":",BoxMinute<10?"0":"",BoxMinute,
         " dur=",BoxDuration,"m | SL=",SL_Buffer,
         " TP1=",TP1_Points," TP2=",TP2_Points);
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   // Clean up all objects
   ObjectsDeleteAll(0, pfx);
}

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
   // Process only on new bar
   if(rates_total <= 1) return(0);

   // On first run or refresh, recalculate all history
   int start = (prev_calculated <= 1) ? 0 : prev_calculated - 1;

   // Reset state on full recalc
   if(prev_calculated <= 1)
   {
      bx_hi=0; bx_lo=0; bx_forming=false; bx_ready=false;
      day_hi=0; day_lo=0; attempt=0; bk_dir=0;
      in_trade=false; entry_px=0; sl_px=0; tp1_px=0; tp2_px=0;
      day_done=false; bk_bar_time=0; sl_bar_time=0; last_box_time=0;
      total_win=0; total_loss=0; total_chop=0;
      total_tp1=0; total_tp2=0; total_pnl=0;
      ObjectsDeleteAll(0, pfx);
   }

   // Process bars
   for(int i = start; i < rates_total - 1; i++)
   {
      datetime ct = time[i];
      double   ch = high[i], cl = low[i], cc = close[i];

      // Get NY time components
      MqlDateTime dt;
      TimeToStruct(ct, dt);

      // Convert server time to NY time (UTC-4)
      // Server is UTC+0, NY = UTC-4, so subtract 4 hours
      datetime ny_time = ct - 4 * 3600;
      MqlDateTime ny_dt;
      TimeToStruct(ny_time, ny_dt);

      int ny_h   = ny_dt.hour;
      int ny_m   = ny_dt.min;
      int ny_dow = ny_dt.day_of_week;

      bool is_weekday = (ny_dow >= 1 && ny_dow <= 5);
      bool is_box_start  = is_weekday && ny_h == BoxHour && ny_m == BoxMinute;
      bool is_box_candle = is_weekday && ny_h == BoxHour && ny_m >= BoxMinute && ny_m < (BoxMinute + BoxDuration);
      bool is_box_end    = is_weekday && ny_h == BoxHour && ny_m == (BoxMinute + BoxDuration);

      // --- NEW DAY (box start) ---
      if(is_box_start && ct != last_box_time)
      {
         last_box_time = ct;

         // Reset day state
         bx_hi = ch; bx_lo = cl;
         bx_forming = true; bx_ready = false;
         day_hi = 0; day_lo = 0;
         attempt = 0; bk_dir = 0;
         in_trade = false;
         entry_px = sl_px = tp1_px = tp2_px = 0;
         day_done = false;
         bk_bar_time = 0; sl_bar_time = 0;

         // Remove old SL/TP lines from previous day
         RemoveDayLines();
      }

      // --- BUILD BOX ---
      if(bx_forming && is_box_candle && ct != last_box_time)
      {
         if(ch > bx_hi) bx_hi = ch;
         if(cl < bx_lo) bx_lo = cl;
      }

      // --- BOX COMPLETE ---
      if(is_box_end && bx_forming)
      {
         bx_forming = false;
         bx_ready   = true;
         day_hi     = bx_hi;
         day_lo     = bx_lo;

         // Draw box on chart
         if(ShowBox)
         {
            string box_name = pfx + "Box_" + TimeToString(ct, TIME_DATE|TIME_MINUTES);
            int    bar_start = i - BoxDuration;
            if(bar_start < 0) bar_start = 0;

            // Box extends 80 bars to the right
            datetime t_left  = time[bar_start];
            datetime t_right = ct + 80 * PeriodSeconds();

            color box_fill = ColorAlpha(BoxColor, (uchar)(255 - BoxTransp * 255 / 100));

            ObjectCreate(0, box_name, OBJ_RECTANGLE, 0, t_left, bx_hi, t_right, bx_lo);
            ObjectSetInteger(0, box_name, OBJPROP_COLOR,     BoxColor);
            ObjectSetInteger(0, box_name, OBJPROP_STYLE,     STYLE_SOLID);
            ObjectSetInteger(0, box_name, OBJPROP_WIDTH,     1);
            ObjectSetInteger(0, box_name, OBJPROP_FILL,      true);
            ObjectSetInteger(0, box_name, OBJPROP_BACK,      true);
            ObjectSetInteger(0, box_name, OBJPROP_SELECTABLE,false);

            Print("Box formed | Hi:",DoubleToString(bx_hi,2),
                  " Lo:",DoubleToString(bx_lo,2),
                  " Range:",DoubleToString(bx_hi-bx_lo,2)," pts");
         }
      }

      // --- ONLY TRADE AFTER BOX IS READY ---
      if(!bx_ready || bx_forming || day_hi == 0 || day_lo == 0) continue;

      // --- TRADE MANAGEMENT (check existing trade first) ---
      if(in_trade && sl_px != 0 && tp1_px != 0)
      {
         bool hit_sl  = (bk_dir == 1) ? (cl <= sl_px)  : (ch >= sl_px);
         bool hit_tp1 = (bk_dir == 1) ? (ch >= tp1_px) : (cl <= tp1_px);
         bool hit_tp2 = (bk_dir == 1) ? (ch >= tp2_px) : (cl <= tp2_px);

         if(hit_tp2)
         {
            total_win++; total_tp2++;
            total_pnl += TP2_Points;
            in_trade = false; day_done = true;

            if(ShowSignals)
               DrawLabel(pfx+"TP2_"+TimeToString(ct), ct,
                         tp2_px, "TP2 ✓",
                         clrGreen, ANCHOR_UPPER, LABEL_DOWN);

            // Remove active lines
            RemoveDayLines();
            Print("TP2 ✓ | +",TP2_Points," pts | Total:",DoubleToString(total_pnl,1));
            continue;
         }
         else if(hit_tp1)
         {
            total_win++; total_tp1++;
            total_pnl += TP1_Points;
            in_trade = false; day_done = true;

            if(ShowSignals)
               DrawLabel(pfx+"TP1_"+TimeToString(ct), ct,
                         tp1_px, "TP1 ✓",
                         clrLime, ANCHOR_UPPER, LABEL_DOWN);

            RemoveDayLines();
            Print("TP1 ✓ | +",TP1_Points," pts | Total:",DoubleToString(total_pnl,1));
            continue;
         }
         else if(hit_sl)
         {
            double actual_loss = MathAbs(entry_px - sl_px);
            total_loss++;
            total_pnl -= actual_loss;
            in_trade  = false;
            bk_dir    = 0;
            bk_bar_time = 0;
            sl_bar_time = ct;

            RemoveDayLines();

            if(attempt >= MaxAttempts)
            {
               total_chop++;
               day_done = true;
               if(ShowSignals)
                  DrawLabel(pfx+"CHOP_"+TimeToString(ct), ct,
                            sl_px, "CHOP ✗",
                            clrOrange, ANCHOR_LOWER, LABEL_UP);
               Print("CHOP ✗ | -",DoubleToString(actual_loss,2)," pts");
            }
            else
            {
               if(ShowSignals)
                  DrawLabel(pfx+"SL_"+TimeToString(ct), ct,
                            sl_px,
                            "SL ✗ "+IntegerToString(attempt)+"/"+IntegerToString(MaxAttempts),
                            clrRed, ANCHOR_LOWER, LABEL_UP);
               Print("SL ✗ | Attempt ",attempt,"/",MaxAttempts,
                     " | -",DoubleToString(actual_loss,2)," pts");
            }
            continue;
         }
      }

      // --- SKIP IF DONE / IN TRADE / MAX ATTEMPTS ---
      if(day_done || in_trade || attempt >= MaxAttempts) continue;

      // SL cooldown: must be past sl_bar
      bool is_past_sl = (sl_bar_time == 0) || (ct > sl_bar_time);
      if(!is_past_sl) continue;

      // --- BREAKOUT DETECTION ---
      if(bk_dir != 1 && cc > day_hi)
      {
         bk_dir = 1;
         bk_bar_time = ct;
         Print("BREAKOUT UP | ",TimeToString(ct)," | Close:",DoubleToString(cc,2),
               " > BoxHi:",DoubleToString(day_hi,2));
      }
      else if(bk_dir != -1 && cc < day_lo)
      {
         bk_dir = -1;
         bk_bar_time = ct;
         Print("BREAKOUT DOWN | ",TimeToString(ct)," | Close:",DoubleToString(cc,2),
               " < BoxLo:",DoubleToString(day_lo,2));
      }

      // --- PULLBACK DETECTION ---
      if(bk_dir == 0 || bk_bar_time == 0) continue;
      if(ct <= bk_bar_time) continue;

      bool pullback_up   = (bk_dir == 1) && (cc > day_hi) && (cl <= day_hi);
      bool pullback_down = (bk_dir == -1) && (cc < day_lo) && (ch >= day_lo);

      if(!pullback_up && !pullback_down) continue;

      // --- ENTRY ---
      attempt++;
      in_trade  = true;
      entry_px  = cc;

      if(bk_dir == 1)
      {
         sl_px  = cl  - SL_Buffer;
         tp1_px = cc  + TP1_Points;
         tp2_px = cc  + TP2_Points;
      }
      else
      {
         sl_px  = ch  + SL_Buffer;
         tp1_px = cc  - TP1_Points;
         tp2_px = cc  - TP2_Points;
      }

      // Draw BUY/SELL label
      if(ShowSignals)
      {
         string dir_str = (bk_dir == 1) ? "BUY " : "SELL ";
         string lbl_name = pfx + "Entry_" + TimeToString(ct);
         double lbl_price = (bk_dir == 1) ?
                            cl  - (day_hi - day_lo) * 0.5 :
                            ch  + (day_hi - day_lo) * 0.5;
         color  lbl_col  = (bk_dir == 1) ? BuyColor : SellColor;
         ENUM_ARROW_ANCHOR anch = (bk_dir == 1) ? ANCHOR_TOP : ANCHOR_BOTTOM;
         ENUM_OBJECT style = (bk_dir == 1) ? OBJ_ARROW_UP : OBJ_ARROW_DOWN;

         // Use text label instead
         ObjectCreate(0, lbl_name, OBJ_TEXT, 0, ct, lbl_price);
         ObjectSetString(0, lbl_name, OBJPROP_TEXT,
                         dir_str + IntegerToString(attempt) + "x");
         ObjectSetInteger(0, lbl_name, OBJPROP_COLOR,    lbl_col);
         ObjectSetInteger(0, lbl_name, OBJPROP_FONTSIZE, 9);
         ObjectSetString(0, lbl_name,  OBJPROP_FONT,    "Arial Bold");
         ObjectSetInteger(0, lbl_name, OBJPROP_SELECTABLE, false);
      }

      // Draw SL / TP1 / TP2 horizontal lines
      if(ShowLines)
      {
         datetime t_now   = ct;
         datetime t_end   = ct + 200 * PeriodSeconds();

         DrawHLine(pfx+"SL_Line",   sl_px,  SL_Color,  "SL",  STYLE_DOT);
         DrawHLine(pfx+"TP1_Line",  tp1_px, TP1_Color, "TP1", STYLE_DASH);
         DrawHLine(pfx+"TP2_Line",  tp2_px, TP2_Color, "TP2", STYLE_DASH);
      }

      Print(bk_dir==1?"BUY ":"SELL ", attempt, "x | Entry:",
            DoubleToString(entry_px,2),
            " | SL:",DoubleToString(sl_px,2),
            " | TP1:",DoubleToString(tp1_px,2),
            " | TP2:",DoubleToString(tp2_px,2));
   }

   // --- DRAW STATS TABLE (last bar) ---
   DrawStatsTable();

   // --- DRAW LIVE SL/TP LINES ON CURRENT BAR ---
   if(in_trade && ShowLines)
   {
      // Update line positions if needed (already drawn at entry)
      // They persist until trade closes
   }

   return(rates_total);
}

//+------------------------------------------------------------------+
// Helper: Draw horizontal line
//+------------------------------------------------------------------+
void DrawHLine(string name, double price, color clr, string label, ENUM_LINE_STYLE style)
{
   if(ObjectFind(0, name) >= 0)
      ObjectDelete(0, name);

   ObjectCreate(0, name, OBJ_HLINE, 0, 0, price);
   ObjectSetInteger(0, name, OBJPROP_COLOR,     clr);
   ObjectSetInteger(0, name, OBJPROP_STYLE,     style);
   ObjectSetInteger(0, name, OBJPROP_WIDTH,     1);
   ObjectSetString(0,  name, OBJPROP_TOOLTIP,   label+": "+DoubleToString(price,2));
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE,false);
   ObjectSetInteger(0, name, OBJPROP_BACK,      false);
}

//+------------------------------------------------------------------+
// Helper: Draw text label
//+------------------------------------------------------------------+
void DrawLabel(string name, datetime t, double price, string text,
               color clr, ENUM_ARROW_ANCHOR anchor, ENUM_OBJECT style)
{
   if(ObjectFind(0, name) >= 0) ObjectDelete(0, name);
   ObjectCreate(0, name, OBJ_TEXT, 0, t, price);
   ObjectSetString(0,  name, OBJPROP_TEXT,      text);
   ObjectSetInteger(0, name, OBJPROP_COLOR,     clr);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE,  8);
   ObjectSetString(0,  name, OBJPROP_FONT,     "Arial Bold");
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE,false);
}

//+------------------------------------------------------------------+
// Helper: Remove active SL/TP lines
//+------------------------------------------------------------------+
void RemoveDayLines()
{
   string lines[] = {pfx+"SL_Line", pfx+"TP1_Line", pfx+"TP2_Line"};
   for(int i = 0; i < 3; i++)
      if(ObjectFind(0, lines[i]) >= 0)
         ObjectDelete(0, lines[i]);
}

//+------------------------------------------------------------------+
// Helper: Draw Stats Table (top right corner)
//+------------------------------------------------------------------+
void DrawStatsTable()
{
   int total_trades = total_win + total_loss;
   double win_rate  = total_trades > 0 ?
                      (double(total_win) / double(total_trades)) * 100.0 : 0.0;
   double rr        = SL_Buffer > 0 ? TP2_Points / SL_Buffer : 0.0;
   double tp1_pct   = total_win > 0 ? (double(total_tp1)/double(total_win))*100.0 : 0.0;
   double tp2_pct   = total_win > 0 ? (double(total_tp2)/double(total_win))*100.0 : 0.0;

   // Position: top right
   int x = 10; // from right
   int y = 20; // from top
   int row_h = 16;
   int col_w = 110;

   string rows[][2] = {
      {"PT BOX NY",   IntegerToString(BoxHour)+":"+(BoxMinute<10?"0":"")+IntegerToString(BoxMinute)},
      {"Total Win",       IntegerToString(total_win)},
      {"  TP1 Hit",       IntegerToString(total_tp1)+" ("+DoubleToString(tp1_pct,1)+"%)"},
      {"  TP2 Hit",       IntegerToString(total_tp2)+" ("+DoubleToString(tp2_pct,1)+"%)"},
      {"Total Loss",      IntegerToString(total_loss)},
      {"Chop Days",       IntegerToString(total_chop)},
      {"Win Rate",        DoubleToString(win_rate,1)+"%"},
      {"Net P&L (pts)",   DoubleToString(total_pnl,1)},
      {"RR (TP2/SL)",     "1:"+DoubleToString(rr,1)},
      {"SL/TP1/TP2",      DoubleToString(SL_Buffer,1)+"/"+DoubleToString(TP1_Points,1)+"/"+DoubleToString(TP2_Points,1)},
      {"Max Attempt",     IntegerToString(MaxAttempts)+"x"},
      {"Today Attempt",   IntegerToString(attempt)+"/"+IntegerToString(MaxAttempts)},
      {"Breakout Dir",    bk_dir==1?"LONG":bk_dir==-1?"SHORT":"Wait"},
      {"In Trade",        in_trade?"YES":"NO"},
   };

   int n = ArrayRange(rows, 0);
   for(int i = 0; i < n; i++)
   {
      string name_key = pfx + "Tbl_K_" + IntegerToString(i);
      string name_val = pfx + "Tbl_V_" + IntegerToString(i);

      // Key label
      if(ObjectFind(0, name_key) < 0)
         ObjectCreate(0, name_key, OBJ_LABEL, 0, 0, 0);
      ObjectSetString(0,  name_key, OBJPROP_TEXT,      rows[i][0]);
      ObjectSetInteger(0, name_key, OBJPROP_CORNER,    CORNER_RIGHT_UPPER);
      ObjectSetInteger(0, name_key, OBJPROP_XDISTANCE, col_w * 2 + x);
      ObjectSetInteger(0, name_key, OBJPROP_YDISTANCE, y + i * row_h);
      ObjectSetInteger(0, name_key, OBJPROP_COLOR,
                       i==0 ? clrWhite : clrSilver);
      ObjectSetInteger(0, name_key, OBJPROP_FONTSIZE,  i==0 ? 9 : 8);
      ObjectSetString(0,  name_key, OBJPROP_FONT,     i==0 ? "Arial Bold" : "Arial");
      ObjectSetInteger(0, name_key, OBJPROP_SELECTABLE, false);

      // Value label
      if(ObjectFind(0, name_val) < 0)
         ObjectCreate(0, name_val, OBJ_LABEL, 0, 0, 0);
      ObjectSetString(0,  name_val, OBJPROP_TEXT,      rows[i][1]);
      ObjectSetInteger(0, name_val, OBJPROP_CORNER,    CORNER_RIGHT_UPPER);
      ObjectSetInteger(0, name_val, OBJPROP_XDISTANCE, x);
      ObjectSetInteger(0, name_val, OBJPROP_YDISTANCE, y + i * row_h);

      // Color coding for values
      color val_clr = clrSilver;
      if(i == 1) val_clr = clrLime;         // Total Win
      else if(i == 4) val_clr = clrRed;     // Total Loss
      else if(i == 5) val_clr = clrOrange;  // Chop
      else if(i == 6) val_clr = win_rate >= 50 ? clrLime : clrRed;  // WinRate
      else if(i == 7) val_clr = total_pnl >= 0 ? clrLime : clrRed;  // PnL
      else if(i == 8) val_clr = clrYellow;  // RR
      else if(i == 12) val_clr = bk_dir==1 ? clrLime : bk_dir==-1 ? clrRed : clrGray;
      else if(i == 13) val_clr = in_trade ? clrYellow : clrGray;

      ObjectSetInteger(0, name_val, OBJPROP_COLOR,    val_clr);
      ObjectSetInteger(0, name_val, OBJPROP_FONTSIZE, i==0 ? 9 : 8);
      ObjectSetString(0,  name_val, OBJPROP_FONT,    i==0 ? "Arial Bold" : "Arial");
      ObjectSetInteger(0, name_val, OBJPROP_SELECTABLE, false);
   }
}
//+------------------------------------------------------------------+
