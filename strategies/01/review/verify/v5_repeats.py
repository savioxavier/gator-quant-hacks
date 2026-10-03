"""V5 (descriptive sensitivity): repeated deliveries of the same text counted once (same speaker, title, H, D)."""
import json
import pandas as pd
import vlib as V

o, ohlc = V.our_opens()
sc = V.kept_scores(V.EXT / "speech_scores_2011_2026.csv")
sc["spk"] = sc["slug"].str.extract(r"^([a-z]+)")[0]
dup = sc.duplicated(["spk", "title", "H", "D"], keep="first")
tf = V.their_fomc(); sch = V.scheduled_fomc()
fomc = tf[tf <= V.IS_END].append(sch[(sch > V.IS_END) & (sch <= V.END)])
b = V.build(o, sc[~dup], fomc)
e1 = V.engine_run(b["w"], ohlc, tbill=True)
out = {"n_repeat_docs_dropped": int(dup.sum()), "n_dropped_post_cut": int((dup & (sc["speech_date"] > V.IS_END)).sum()),
       "dropped": sc.loc[dup, "slug"].tolist(),
       "sharpe_ex_1x": {w: V.sharpe(V.win(e1["ex"], w)) for w in V.WINDOWS}}
print(json.dumps(out, indent=1))
(V.HERE / "out" / "v5_repeats.json").write_text(json.dumps(out, indent=1))
