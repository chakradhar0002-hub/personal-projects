#!/usr/bin/env python3
"""Probe column layouts of two existing F&O bhavcopy samples (data only)."""
import io, sys, zipfile
import pandas as pd
for p in sys.argv[1:]:
    z = zipfile.ZipFile(p)
    df = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])), dtype=str)
    df.columns = [c.strip() for c in df.columns]
    print(p, z.namelist(), df.shape)
    print(list(df.columns))
    k = 'TckrSymb' if 'TckrSymb' in df.columns else 'SYMBOL'
    sub = df[df[k].str.strip() == 'INFY']
    print(sub.head(8).to_string())
