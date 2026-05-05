//+------------------------------------------------------------------+
//|  PT Box Backtest                                                  |
//|  v1.40 — Tambah TP1 vs TP2 tracking                             |
//+------------------------------------------------------------------+
#property copyright "PT Box System"
#property version   "1.40"
#property strict

input int    BoxHourNY     = 1;
input int    BoxMinute     = 20;
input int    BoxDuration   = 5;
input double SL_Buffer     = 3.0;
input double TP1_Points    = 16.0;
input double TP2_Points    = 32.0;
input int    MaxAttempts   = 3;

double   bx_hi=0,bx_lo=0;
bool     bx_forming=false,bx_ready=false;
double   day_hi=0,day_lo=0;
int      attempt=0,bk_dir=0;
bool     in_trade=false;
double   entry_px=0,sl_px=0,tp1_px=0,tp2_px=0;
bool     day_done=false;
datetime bk_bar_time=0,sl_bar_time=0,last_bar_time=0;
int      total_win=0,total_loss=0,total_chop=0;
int      total_tp1=0,total_tp2=0;
double   total_pnl=0.0;
const int SERVER_OFFSET=4;

int OnInit()
  {
   int s=(BoxHourNY+SERVER_OFFSET)%24;
   Print("PT Box EA v1.40 | NY: ",BoxHourNY,":",BoxMinute<10?"0":"",BoxMinute,
         " | Server: ",s,":",BoxMinute<10?"0":"",BoxMinute,
         " - ",s,":",BoxMinute+BoxDuration<10?"0":"",BoxMinute+BoxDuration);
   return(INIT_SUCCEEDED);
  }

void OnTick()
  {
   int bhs=(BoxHourNY+SERVER_OFFSET)%24;
   datetime cb=iTime(_Symbol,PERIOD_M1,0);
   if(cb==last_bar_time) return;
   last_bar_time=cb;
   double   c_high=iHigh(_Symbol,PERIOD_M1,1);
   double   c_low=iLow(_Symbol,PERIOD_M1,1);
   double   c_close=iClose(_Symbol,PERIOD_M1,1);
   datetime c_time=iTime(_Symbol,PERIOD_M1,1);
   MqlDateTime dt; TimeToStruct(c_time,dt);
   int ch=dt.hour,cm=dt.min,cdow=dt.day_of_week;
   bool wd=(cdow>=1&&cdow<=5);
   bool is_new_day   =wd&&ch==bhs&&cm==BoxMinute;
   bool is_box_candle=wd&&ch==bhs&&cm>=BoxMinute&&cm<(BoxMinute+BoxDuration);
   bool is_box_end   =wd&&ch==bhs&&cm==(BoxMinute+BoxDuration);
   if(is_new_day)
     {
      bx_hi=c_high;bx_lo=c_low;bx_forming=true;bx_ready=false;
      day_hi=0;day_lo=0;attempt=0;bk_dir=0;
      in_trade=false;entry_px=0;sl_px=0;tp1_px=0;tp2_px=0;
      day_done=false;bk_bar_time=0;sl_bar_time=0;
      Print("=== NEW DAY === NY: ",BoxHourNY,":",BoxMinute<10?"0":"",BoxMinute,
            " | Server: ",bhs,":",BoxMinute<10?"0":"",BoxMinute);
     }
   if(bx_forming&&is_box_candle&&!is_new_day)
     {if(c_high>bx_hi)bx_hi=c_high;if(c_low<bx_lo)bx_lo=c_low;}
   if(is_box_end&&bx_forming)
     {
      bx_forming=false;bx_ready=true;day_hi=bx_hi;day_lo=bx_lo;
      Print("Box | Hi:",DoubleToString(bx_hi,2)," Lo:",DoubleToString(bx_lo,2),
            " Range:",DoubleToString(bx_hi-bx_lo,2),"pts");
     }
   if(!bx_ready||bx_forming||day_hi==0||day_lo==0) return;
   if(in_trade&&sl_px!=0&&tp1_px!=0)
     {
      bool hit_sl =(bk_dir==1)?(c_low<=sl_px) :(c_high>=sl_px);
      bool hit_tp1=(bk_dir==1)?(c_high>=tp1_px):(c_low<=tp1_px);
      bool hit_tp2=(bk_dir==1)?(c_high>=tp2_px):(c_low<=tp2_px);
      if(hit_tp2)
        {total_win++;total_tp2++;total_pnl+=TP2_Points;in_trade=false;day_done=true;
         Print("TP2 ✓ | +",TP2_Points," pts | Total: ",DoubleToString(total_pnl,1));}
      else if(hit_tp1)
        {total_win++;total_tp1++;total_pnl+=TP1_Points;in_trade=false;day_done=true;
         Print("TP1 ✓ | +",TP1_Points," pts | Total: ",DoubleToString(total_pnl,1));}
      else if(hit_sl)
        {
         double al=MathAbs(entry_px-sl_px);
         total_loss++;total_pnl-=al;in_trade=false;bk_dir=0;bk_bar_time=0;sl_bar_time=c_time;
         if(attempt>=MaxAttempts)
           {total_chop++;day_done=true;
            Print("CHOP ✗ | -",DoubleToString(al,2)," pts | Total: ",DoubleToString(total_pnl,1));}
         else
           {Print("SL ✗ | Attempt ",attempt,"/",MaxAttempts,
                  " | -",DoubleToString(al,2)," pts | Total: ",DoubleToString(total_pnl,1));}
        }
     }
   if(day_done||in_trade||attempt>=MaxAttempts) return;
   bool is_past_sl=(sl_bar_time==0)||(c_time>sl_bar_time);
   if(is_past_sl)
     {
      if(bk_dir!=1&&c_close>day_hi)
        {bk_dir=1;bk_bar_time=c_time;
         Print("BREAKOUT UP | ",TimeToString(c_time)," | ",DoubleToString(c_close,2)," > ",DoubleToString(day_hi,2));}
      else if(bk_dir!=-1&&c_close<day_lo)
        {bk_dir=-1;bk_bar_time=c_time;
         Print("BREAKOUT DOWN | ",TimeToString(c_time)," | ",DoubleToString(c_close,2)," < ",DoubleToString(day_lo,2));}
     }
   if(bk_dir==0||bk_bar_time==0) return;
   if(c_time<=bk_bar_time) return;
   bool pu=(bk_dir==1) &&(c_close>day_hi)&&(c_low<=day_hi);
   bool pd=(bk_dir==-1)&&(c_close<day_lo)&&(c_high>=day_lo);
   if(!pu&&!pd) return;
   attempt++;in_trade=true;entry_px=c_close;
   if(bk_dir==1)
     {sl_px=c_low-SL_Buffer;tp1_px=entry_px+TP1_Points;tp2_px=entry_px+TP2_Points;
      Print("BUY ",attempt,"x | Entry:",DoubleToString(entry_px,2),
            " SL:",DoubleToString(sl_px,2)," TP1:",DoubleToString(tp1_px,2)," TP2:",DoubleToString(tp2_px,2));}
   else
     {sl_px=c_high+SL_Buffer;tp1_px=entry_px-TP1_Points;tp2_px=entry_px-TP2_Points;
      Print("SELL ",attempt,"x | Entry:",DoubleToString(entry_px,2),
            " SL:",DoubleToString(sl_px,2)," TP1:",DoubleToString(tp1_px,2)," TP2:",DoubleToString(tp2_px,2));}
  }

void OnDeinit(const int reason)
  {
   int tt=total_win+total_loss;
   double wr=tt>0?(double(total_win)/double(tt))*100.0:0.0;
   double rr=SL_Buffer>0?TP2_Points/SL_Buffer:0.0;
   double tp1_pct=total_win>0?(double(total_tp1)/double(total_win))*100.0:0.0;
   double tp2_pct=total_win>0?(double(total_tp2)/double(total_win))*100.0:0.0;
   Print("==========================================");
   Print("=== PT BOX — FINAL STATS ===");
   Print("==========================================");
   Print("Total Win   : ",total_win);
   Print("  TP1 Hit   : ",total_tp1," (",DoubleToString(tp1_pct,1),"%)");
   Print("  TP2 Hit   : ",total_tp2," (",DoubleToString(tp2_pct,1),"%)");
   Print("Total Loss  : ",total_loss);
   Print("Chop Days   : ",total_chop);
   Print("Win Rate    : ",DoubleToString(wr,1),"%");
   Print("Net P&L     : ",DoubleToString(total_pnl,1)," pts");
   Print("RR (TP2/SL) : 1:",DoubleToString(rr,1));
   Print("SL/TP1/TP2  : ",SL_Buffer,"/",TP1_Points,"/",TP2_Points);
   Print("Max Attempt : ",MaxAttempts,"x");
   Print("==========================================");
  }
