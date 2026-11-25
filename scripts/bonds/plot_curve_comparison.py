"""Professional comparison of today's Treasury curve with recent snapshots."""
import argparse, os
import pandas as pd
import matplotlib.pyplot as plt

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--files",nargs=3,required=True)
    p.add_argument("--out",default="pipelines/bonds/curve_comparison.png")
    args=p.parse_args()
    data=[]
    for f in args.files:
        df=pd.read_csv(f,parse_dates=["date"])
        if not {"date","yield_pct"} <= set(df.columns): raise ValueError(f"Invalid CSV: {f}")
        df=df[["date","yield_pct"]].rename(columns={"yield_pct":os.path.basename(f)})
        data.append(df)
    merged=data[0]
    for d in data[1:]: merged=merged.merge(d,on="date",how="inner")
    merged=merged.sort_values("date").dropna()
    if len(merged)<1: raise RuntimeError("No common curve observations")
    cols=[c for c in merged.columns if c!="date"]
    latest=merged.iloc[-1]
    selected=[len(merged)-1]
    for n in (5,30):
        if len(merged)>n: selected.append(len(merged)-1-n)
    selected=list(dict.fromkeys(selected))
    fig,ax=plt.subplots(figsize=(10,5.5))
    labels=["2Y","10Y","30Y"]
    for idx in selected:
        row=merged.iloc[idx]
        label="Current" if idx==selected[0] else f"{(latest['date']-row['date']).days} days ago"
        ax.plot(labels,[row[c] for c in cols],marker="o",linewidth=2,label=label)
    ax.set_title("US Treasury Yield Curve | Recent Comparisons")
    ax.set_ylabel("Yield (%)")
    ax.grid(True,alpha=.25)
    ax.legend()
    ax.text(.99,.02,f"Current observation: {latest['date'].date()}",transform=ax.transAxes,ha="right",va="bottom")
    os.makedirs(os.path.dirname(args.out) or ".",exist_ok=True)
    fig.tight_layout(); fig.savefig(args.out,dpi=180); plt.close(fig)
    print("Saved:",args.out)
if __name__=="__main__": main()
