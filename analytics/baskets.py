"""Association rules by own Apriori (itemsets up to size 3) on invoice baskets of SKUs. Sparse-matrix counting; deterministic."""
from __future__ import annotations

import itertools

import numpy as np
import polars as pl
from scipy import sparse

from analytics import data

MIN_SUPPORT = 0.005
MIN_CONFIDENCE = 0.4
MIN_LIFT = 1.0
MAX_LEN = 3


def baskets_matrix():
    s = data.sales().select("invoice_no", "sku", "family", "description").unique(["invoice_no", "sku"])
    inv = {k: i for i, k in enumerate(sorted(s["invoice_no"].unique().to_list()))}
    skus = sorted(s["sku"].unique().to_list())
    sk = {k: i for i, k in enumerate(skus)}
    rows = np.array([inv[x] for x in s["invoice_no"]]); cols = np.array([sk[x] for x in s["sku"]])
    X = sparse.csr_matrix((np.ones(len(rows), dtype=np.int32), (rows, cols)), shape=(len(inv), len(skus)))
    meta = s.group_by("sku").agg(pl.col("family").first(), pl.col("description").first())
    d = dict(zip(meta["sku"], zip(meta["family"], meta["description"])))
    return X, skus, d


def mine(X, min_support=MIN_SUPPORT):
    nb = X.shape[0]
    minc = int(np.ceil(min_support * nb))
    c1 = np.asarray(X.sum(0)).ravel()
    f1 = np.where(c1 >= minc)[0]
    Xf = X[:, f1].tocsc()
    C = (Xf.T @ Xf).tocoo()
    pairs = {}
    for a, b, v in zip(C.row, C.col, C.data):
        if a < b and v >= minc:
            pairs[(int(a), int(b))] = int(v)
    pset = set(pairs)
    # triples: extend frequent pairs; all three sub-pairs must be frequent
    nbr = {}
    for a, b in pset:
        nbr.setdefault(a, set()).add(b)
    triples = {}
    for (a, b) in pset:
        for c in nbr.get(b, ()):
            if (a, c) in pset:
                cnt = int(Xf[:, a].multiply(Xf[:, b]).multiply(Xf[:, c]).sum())
                if cnt >= minc:
                    triples[(a, b, c)] = cnt
    return nb, minc, f1, c1[f1], pairs, triples


def rules(nb, f1, c1f, pairs, triples, min_conf=MIN_CONFIDENCE, min_lift=MIN_LIFT):
    cnt1 = {i: int(c) for i, c in enumerate(c1f)}
    cnt = {(i,): c for i, c in cnt1.items()}
    cnt.update({k: v for k, v in pairs.items()}); cnt.update({k: v for k, v in triples.items()})
    out = []
    for items, c in list(pairs.items()) + list(triples.items()):
        for r in range(1, len(items)):
            for ante in itertools.combinations(items, r):
                cons = tuple(i for i in items if i not in ante)
                ca, cc = cnt[ante], cnt[cons]
                conf = c / ca
                lift = conf / (cc / nb)
                if conf >= min_conf and lift > min_lift:
                    sup = c / nb
                    lev = sup - (ca / nb) * (cc / nb)
                    conv = (1 - cc / nb) / (1 - conf) if conf < 1 else None
                    out.append((ante, cons, c, sup, conf, lift, lev, conv))
    return out
