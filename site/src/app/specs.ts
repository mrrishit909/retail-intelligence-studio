import { fv, fs, type Core } from "./data";
import type { PairSpec } from "./pairView";

export function heroSpec(c: Core): PairSpec {
  return {
    id: "hero", unit: "BASKETS", sizeA: fv(c, "hero_pair_na"), sizeB: fv(c, "hero_pair_nb"), shared: fv(c, "hero_pair_nab"),
    labelA: fs(c, "hero_pair_a_desc"), labelB: fs(c, "hero_pair_b_desc"), chance: fv(c, "hero_pair_chance"),
    role: "observed", interval: null, hatch: false, refSize: fv(c, "hero_pair_na"), axis: "h",
  };
}
