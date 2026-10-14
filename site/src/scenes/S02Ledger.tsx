import { StoryDeck, type DeckCard } from "../components/StoryDeck";
import { Track } from "../scroll/Track";
import { HonestyChip } from "../components/HonestyChip";
import { ArtifactStatus } from "../components/StateUI";
import { useArtifact } from "../data/useArtifact";
import { RECON } from "../app/artifacts";
import { fmt, fs, fv, gbp, useCore } from "../app/data";
import { setPair } from "../app/pairView";
import { useSteps } from "./common";
import { MiniPair } from "./MiniPair";
import type { SceneDef } from "../app/scenes";

/** S02 Origin of the Data: the ledger, refunds, guests, no demographics. */
export function S02Ledger({ def }: { def: SceneDef }) {
  const cs = useCore();
  const [rec, retry] = useArtifact(RECON);
  useSteps(def.id, [], () => setPair({ alpha: 0.2 }));
  const c = cs.status === "ready" ? cs.data : null;
  const r = rec.status === "ready" ? rec.data : null;
  const cards: DeckCard[] = c ? [
    {
      variant: "dark", chip: "THE LEDGER", title: "A million lines, every one counted.",
      body: <>EVERY ROW IS KEPT OR DROPPED FOR A STATED REASON. THE TOTALS RECONCILE TO THE PENNY.</>,
      visual: <div className="deck-vis">
        <ArtifactStatus file="reconciliation.json" state={rec} retry={retry} empty="UNAVAILABLE">{(x) => (
          <>
            <p>{fmt(x.row_ledger.raw_rows)} RAW ROWS</p>
            <p>− {fmt(fv(c, "rows_overlap_duplicates"))} SHEET OVERLAP (DEC 2010 IN BOTH SHEETS)</p>
            <p>− {fmt(fv(c, "rows_exact_duplicates"))} EXACT DUPLICATES</p>
            <p>= {fmt(x.row_ledger.kept)} KEPT {x.identities.every((i) => i.pass) ? "✓" : "✗"}</p>
          </>
        )}</ArtifactStatus>
        <p>PIPELINE {c.meta.pipeline_version} · DBT {c.meta.engine.dbt_version} · DUCKDB {c.meta.engine.duckdb_version}</p>
      </div>,
      tag: <HonestyChip tag="OBSERVED" />,
    },
    {
      variant: "dark", chip: "REFUNDS", title: "Refunds are their own set.",
      body: <>A REFUND IS NEVER HIDDEN INSIDE A SALE. SOME REFUND A SALE FROM BEFORE THE DATA BEGINS.</>,
      visual: r ? <div className="deck-vis">
        <MiniPair a={r.refunds.sale_units} b={r.refunds.refunded_qty} shared={r.refunds.matched_qty} />
        <p>REFUNDED, NO SALE ON RECORD: {fmt(r.refunds.refunded_qty - r.refunds.matched_qty)} UNITS</p>
        <p>{gbp(Math.abs(fv(c, "revenue_refunds_gbp")))} REFUNDED · {(fv(c, "refund_value_share_of_sales") * 100).toFixed(1)}% OF SALES · MATCHED LIFO WITHIN CUSTOMER AND SKU</p>
      </div> : <ArtifactStatus file="reconciliation.json" state={rec} retry={retry} empty="UNAVAILABLE">{() => null}</ArtifactStatus>,
      tag: <HonestyChip tag="OBSERVED" />,
    },
    {
      variant: "dark", chip: "GUESTS", title: "A fifth of the lines have no name.",
      body: <>GUEST LINES COUNT FOR REVENUE AND BASKETS. THEY CANNOT COUNT AS CUSTOMERS.</>,
      visual: <div className="deck-vis">
        <p>{(fv(c, "guest_line_share") * 100).toFixed(1)}% OF LINES · {(fv(c, "guest_revenue_share") * 100).toFixed(1)}% OF REVENUE HAVE NO CUSTOMER ID</p>
        <p>IN REVENUE: YES · IN BASKETS: YES · IN RFM, COHORTS, CLV: NO</p>
      </div>,
      tag: <HonestyChip tag="OBSERVED" />,
    },
    {
      variant: "blue", chip: "NO DEMOGRAPHICS", title: "No ages. No genders. No personas.",
      body: <>{c.meta.no_demographics.toUpperCase()}</>,
      visual: <div className="deck-vis">
        <p>{c.meta.source.attribution.toUpperCase()}</p>
        <p><a className="doi" href={`https://doi.org/${c.meta.source.doi}`} rel="noreferrer">DOI {c.meta.source.doi}</a> · CC BY 4.0 · DERIVED AGGREGATES, NOT THE ORIGINAL FILE</p>
        <p>{fs(c, "currency")}</p>
      </div>,
      tag: <HonestyChip tag="OBSERVED" />,
    },
  ] : [];
  return (
    <Track id={def.id} height={def.track} landing={def.landing} className="scene scene-ledger">
      <p className="scene-kicker s02-kicker">WHAT THE LEDGER HOLDS · WHAT IT DOESN&apos;T · AND WHAT WE LEFT OUT</p>
      {cards.length ? <StoryDeck track={def.id} cards={cards} /> : <p className="state-line">LOADING FACTS</p>}
    </Track>
  );
}
