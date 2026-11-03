"""Peer districts -> mart_peers: the 10 nearest districts in the latest year on standardized
log enrollment, log property wealth per student and economically disadvantaged share."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

K = 10


def run(con) -> None:
    df = con.execute("""
        SELECT y.cdn, y.enrollment, y.wealth_per_student_real, d.econ_disadv_pct
        FROM mart_district_year y JOIN mart_districts d USING (cdn)
        WHERE y.is_current AND y.year = (SELECT max(year) FROM mart_district_year)
          AND y.enrollment > 0 AND y.wealth_per_student_real > 0 AND d.econ_disadv_pct IS NOT NULL
    """).df()
    X = StandardScaler().fit_transform(
        np.column_stack(
            [np.log(df.enrollment), np.log(df.wealth_per_student_real), df.econ_disadv_pct]
        )
    )
    dist, idx = NearestNeighbors(n_neighbors=K + 1).fit(X).kneighbors(X)
    rows = [
        {"cdn": df.cdn[i], "peer_cdn": df.cdn[j], "peer_rank": r, "distance": d}
        for i in range(len(df))
        for r, (j, d) in enumerate(zip(idx[i][1:], dist[i][1:], strict=True), 1)
    ]
    out = pd.DataFrame(rows)
    con.register("tmp_df", out)
    con.execute("CREATE OR REPLACE TABLE mart_peers AS SELECT * FROM tmp_df")
    con.unregister("tmp_df")
    print(f"   mart_peers: {df.shape[0]} districts x {K} peers")
