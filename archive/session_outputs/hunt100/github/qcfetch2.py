import urllib.request, urllib.parse, re, html, os, sys
base="https://raw.githubusercontent.com/QuantConnect/Tutorials/master/04%20Strategy%20Library/"
folders=["04 The Dynamic Breakout II Strategy","05 Dual Thrust Trading Algorithm","06 Can Crude Oil Predict Equity Returns",
"102 Option Expiration Week Effect","1025 Leveraged ETFs with Systematic Risk Management","1026 Intraday ETF Momentum",
"113 January Barometer","118 Time Series Momentum Effect","12 Asset Class Trend Following","13 Asset Class Momentum","14 Sector Momentum",
"16 Overnight Anomaly","198 Exploiting Term Structure of VIX Futures","22 Momentum Effect in Country Equity Indexes",
"23 Mean Reversion Effect in Country Equity Indexes","269 Seasonality Effect based on Same-Calendar Month Returns",
"27 Momentum Effect in Commodities Futures","270 Risk Premia in Forex Markets","29 Term Structure Effect in Commodities",
"30 Momentum Effect Combined with Term Structure in Commodities","32 Gold Market Timing","33 Paired Switching",
"356 Improved Momentum Strategy on Commodities Futures","357 Commodities Futures Trend Following","37 Momentum and State of Market Filters",
"58 VIX Predicts Stock Index Returns","71 Short Term Reversal with Futures","78 Beta Factor in Country Equity Indexes","83 Pre-Holiday Effect",
"17 Forex Momentum","20 Forex Carry Trade","35 Turn of the Month in Equity Indexes","02 Combining Mean Reversion and Momentum in Forex Market",
"08 The Momentum Strategy Based on the Low Frequency Component of Forex Market","1023 Intraday Arbitrage Between Index ETFs","100 Trading with WTI BRENT Spread"]
files=["01 Introduction.html","02 Method.html","03 Algorithm.html","04 Source.html","03 Results.html","01 Abstract.html","02 Introduction.html","03 Method.html","04 Summary.html","04 Results.html","05 Summary.html","05 Results.html","06 Summary.html","07 Summary.html","06 References.html","05 References.html","07 References.html"]
import os
for fo in folders:
    name0=re.sub(r"[^A-Za-z0-9]+","_",fo)
    if os.path.exists("qclib/"+name0+".txt") and os.path.getsize("qclib/"+name0+".txt")>0: continue
    out=[]
    for f in files:
        u=base+urllib.parse.quote(fo)+"/"+urllib.parse.quote(f)
        try:
            t=urllib.request.urlopen(u,timeout=20).read().decode('utf-8','ignore')
        except Exception as e:
            continue
        t=re.sub(r'<script.*?</script>','',t,flags=re.S)
        t=re.sub(r'<(br|p|li|tr|h\d)[^>]*>','\n',t)
        t=re.sub(r'<[^>]+>',' ',t)
        t=html.unescape(t)
        t=re.sub(r'[ \t]+',' ',t); t=re.sub(r'\n\s*\n+','\n',t)
        out.append("### "+f+"\n"+t.strip())
    name=re.sub(r'[^A-Za-z0-9]+','_',fo)
    open("qclib/"+name+".txt","w",encoding="utf-8").write("\n".join(out))
    print(fo, len(out), sum(len(x) for x in out))
