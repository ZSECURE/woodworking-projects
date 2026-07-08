"""
Conservatory Hip Roof Calculator
=================================
All linear dimensions are in millimetres (mm) internally.
All angles are in degrees in the output.

Roof type: 4-corner hip roof (the most common conservatory style).

Key geometry:
  - Ridge runs along the long axis.
  - Common rafters are perpendicular to the ridge (span = W/2 each side).
  - Hip rafters run diagonally at 45° plan angle from each corner to a
    ridge end (or to the apex if L == W).
  - Jack rafters are parallel to common rafters but shorter; they run
    from the long-wall plate to a hip rafter inside each hip-end zone.
  - Pods are OSB-skinned insulation cassettes that slot between adjacent
    rafter bays for a warm, ventilated timber roof.
"""

import math


# ── Standard timber section sizes (UK C24 / CLS) ─────────────────────────────
RIDGE_W = 47          # mm  ridge-beam width
RIDGE_D = 200         # mm  ridge-beam depth
HIP_W   = 47          # mm  hip-rafter width
HIP_D   = 200         # mm  hip-rafter depth (deeper allows backing bevel)
RAF_W   = 47          # mm  common / jack rafter width
RAF_D   = 150         # mm  common / jack rafter depth
WP_W    = 100         # mm  wall-plate width
WP_D    = 47          # mm  wall-plate depth (laid flat)

# ── Pod / insulation spec ─────────────────────────────────────────────────────
INSUL_D  = 100        # mm  PIR insulation thickness
AIR_GAP  = 50         # mm  ventilated air gap above insulation
OSB_T    = 18         # mm  OSB/3 board thickness (each face)

# ── Standard OSB sheet sizes ──────────────────────────────────────────────────
OSB_SHEETS = [
    {"label": "2440 × 1220 mm (standard)",  "l": 2440, "w": 1220},
    {"label": "2400 × 1200 mm (metric)",    "l": 2400, "w": 1200},
]
DEFAULT_OSB = OSB_SHEETS[0]


def _mm(val, dp=0):
    """Round to dp decimal places and return as a number."""
    return round(val, dp) if dp else round(val)


class ConservatoryRoof:
    """
    Calculates all dimensions and cut-lists for replacing an aluminium
    conservatory roof with a solid insulated timber hip roof.
    """

    def __init__(
        self,
        length_m: float,
        width_m: float,
        pitch_deg: float = 30.0,
        overhang_mm: float = 300.0,
        rafter_spacing_mm: float = 600.0,
    ):
        if width_m > length_m:
            length_m, width_m = width_m, length_m   # ensure L >= W

        self.L = length_m * 1000          # mm
        self.W = width_m  * 1000          # mm
        self.pitch_deg = float(pitch_deg)
        self.pitch     = math.radians(pitch_deg)
        self.overhang  = float(overhang_mm)
        self.spacing   = float(rafter_spacing_mm)

        # Validate minimum dimensions
        if self.W < 1000:
            raise ValueError("Conservatory width must be at least 1 m.")
        if self.pitch_deg < 10 or self.pitch_deg > 60:
            raise ValueError("Roof pitch must be between 10° and 60°.")
        if self.spacing < 300 or self.spacing > 900:
            raise ValueError("Rafter spacing must be between 300 mm and 900 mm.")

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def calculate(self) -> dict:
        """Return a complete results dictionary."""
        r = {}

        # 1. Basic geometry
        r.update(self._geometry())

        # 2. Rafter counts
        r.update(self._rafter_counts(r))

        # 3. Angles
        r.update(self._angles(r))

        # 4. Wall plates
        r.update(self._wall_plates())

        # 5. Pod specification
        r.update(self._pods(r))

        # 6. OSB optimisation
        r.update(self._osb_optimisation(r))

        # 7. Consolidated cut list
        r["cut_list"] = self._cut_list(r)

        # 8. Timber running totals (for ordering)
        r["timber_totals"] = self._timber_totals(r)

        return r

    # ─────────────────────────────────────────────────────────────────────────
    # Geometry
    # ─────────────────────────────────────────────────────────────────────────

    def _geometry(self) -> dict:
        """Core roof geometry."""
        half_w = self.W / 2.0

        # Vertical rise at ridge
        rise = half_w * math.tan(self.pitch)

        # Ridge length (zero if square plan)
        ridge_len = max(0.0, self.L - self.W)

        # ── Common rafter ────────────────────────────────────────────────────
        # Structural run (wall plate to ridge centreline)
        cr_run = half_w
        # Length along slope (structural only, no overhang)
        cr_struct = cr_run / math.cos(self.pitch)
        # Overhang portion along slope
        cr_ovhng = self.overhang / math.cos(self.pitch)
        # Total length (wall plate bird's-mouth to rafter tail end)
        cr_total = cr_struct + cr_ovhng

        # ── Hip rafter ───────────────────────────────────────────────────────
        # Plan run of hip (diagonal at 45° from corner to ridge end)
        hip_plan = half_w * math.sqrt(2.0)
        # Hip pitch angle (shallower than common-rafter pitch)
        hip_pitch = math.atan(math.tan(self.pitch) / math.sqrt(2.0))
        # Structural length
        hip_struct = hip_plan / math.cos(hip_pitch)
        # Overhang: the hip extends beyond the corner to carry the eave soffit.
        # The eave overhang measured perpendicular to the wall = self.overhang.
        # Diagonally the plan overhang = overhang × √2.
        hip_ovhng_plan = self.overhang * math.sqrt(2.0)
        hip_ovhng_slope = hip_ovhng_plan / math.cos(hip_pitch)
        hip_total = hip_struct + hip_ovhng_slope

        # ── Ridge beam ───────────────────────────────────────────────────────
        # Add half-ridge-thickness at each end to centre over the hip:
        # typical allowance = hip_rafter_width / 2 (≈ 24 mm each end)
        ridge_full = ridge_len + HIP_W  # allow one hip width (split between 2 ends)

        return {
            "L_mm":                 _mm(self.L),
            "W_mm":                 _mm(self.W),
            "pitch_deg":            round(self.pitch_deg, 1),
            "rise_mm":              _mm(rise),
            "ridge_len_mm":         _mm(ridge_len),
            "ridge_full_mm":        _mm(ridge_full),
            "common_run_mm":        _mm(cr_run),
            "common_struct_mm":     _mm(cr_struct),
            "common_total_mm":      _mm(cr_total),
            "hip_plan_mm":          _mm(hip_plan),
            "hip_pitch_deg":        round(math.degrees(hip_pitch), 1),
            "hip_struct_mm":        _mm(hip_struct),
            "hip_total_mm":         _mm(hip_total),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Rafter counts
    # ─────────────────────────────────────────────────────────────────────────

    def _rafter_counts(self, g: dict) -> dict:
        ridge_span = self.L - self.W  # plan length of ridge

        # ── Common rafters ──────────────────────────────────────────────────
        # Pairs sitting along the ridge span (front + back = 2 per position).
        # Include rafters at BOTH ends of the ridge span (at x = W/2 and x = L-W/2).
        if ridge_span <= 0:
            n_common_pairs = 0
        else:
            n_common_pairs = math.floor(ridge_span / self.spacing) + 1
        n_common = n_common_pairs * 2  # front and back

        # ── Jack rafters ────────────────────────────────────────────────────
        # In each hip-end zone (x = 0 → W/2), jack rafters on both long-wall
        # plates at positions x = s, 2s, … where x < W/2.
        half_w = self.W / 2.0
        n_jacks_per_side = max(0, math.floor((half_w - 1e-6) / self.spacing))
        # 4 corners × 1 jack per corner per unique length
        n_jacks_per_len = 4

        jack_lengths = []
        for j in range(1, n_jacks_per_side + 1):
            run = j * self.spacing          # horizontal run (mm)
            struct_len = run / math.cos(self.pitch)
            total_len  = struct_len + (self.overhang / math.cos(self.pitch))
            jack_lengths.append({
                "j":            j,
                "run_mm":       _mm(run),
                "struct_mm":    _mm(struct_len),
                "total_mm":     _mm(total_len),
                "qty":          n_jacks_per_len,
            })

        n_jack_total = len(jack_lengths) * n_jacks_per_len

        return {
            "n_common_pairs":    n_common_pairs,
            "n_common":          n_common,
            "n_jacks_per_side":  n_jacks_per_side,
            "jack_lengths":      jack_lengths,
            "n_jack_total":      n_jack_total,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Angles
    # ─────────────────────────────────────────────────────────────────────────

    def _angles(self, g: dict) -> dict:
        α  = self.pitch
        αh = math.radians(g["hip_pitch_deg"])

        # ── Common / Jack rafter ──────────────────────────────────────────────
        # Plumb cut: the saw is set to the pitch angle (measured from vertical).
        plumb = self.pitch_deg

        # Seat cut (bird's mouth): the horizontal cut, complement of plumb.
        seat = 90.0 - plumb

        # ── Hip rafter ────────────────────────────────────────────────────────
        # Plumb cut (through the depth of the hip, measured from vertical):
        hip_plumb = g["hip_pitch_deg"]

        # Backing (bevel) angle: the bevel planed or sawn along the top arris
        # of the hip rafter so that the roof decking lies flat on both sides.
        # Formula: tan(backing) = sin(45°) × tan(α)
        backing = math.degrees(math.atan(math.sin(math.radians(45.0)) * math.tan(α)))

        # Ridge compound cut for hip rafter:
        # Set mitre (rotation in plan) to 45°.
        # Set bevel (blade tilt from vertical) to hip_plumb angle.
        hip_ridge_mitre = 45.0
        hip_ridge_bevel = hip_plumb

        # ── Jack rafter side (cheek) cut ─────────────────────────────────────
        # Where the jack meets the hip rafter, a side cut is required.
        # For a 45° hip: tan(side_cut) = cos(pitch)
        # This gives the angle measured on the face of the rafter from its
        # centre-line (plumb reference).
        jack_side = math.degrees(math.atan(math.cos(α)))

        # ── Bird's mouth depth ───────────────────────────────────────────────
        # Maximum seat depth = 1/3 × rafter depth (structural rule).
        seat_depth = round(RAF_D / 3.0)

        # ── Rafter tail cut ───────────────────────────────────────────────────
        # The bottom (tail) of the rafter is cut plumb (vertical) so the
        # fascia board sits truly vertical.
        # Saw set to same plumb angle.

        return {
            "plumb_cut_deg":        round(plumb, 1),
            "seat_cut_deg":         round(seat, 1),
            "hip_plumb_deg":        round(hip_plumb, 1),
            "hip_backing_deg":      round(backing, 1),
            "hip_ridge_mitre_deg":  round(hip_ridge_mitre, 1),
            "hip_ridge_bevel_deg":  round(hip_ridge_bevel, 1),
            "jack_side_cut_deg":    round(jack_side, 1),
            "bird_mouth_depth_mm":  seat_depth,
            "bird_mouth_width_mm":  WP_W,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Wall plates
    # ─────────────────────────────────────────────────────────────────────────

    def _wall_plates(self) -> dict:
        return {
            "wp_long_mm":   _mm(self.L),
            "wp_short_mm":  _mm(self.W),
            "wp_total_mm":  _mm(2 * self.L + 2 * self.W),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Pod specification
    # ─────────────────────────────────────────────────────────────────────────

    def _pods(self, r: dict) -> dict:
        """
        Each pod is an OSB-skinned cassette that slots between two adjacent
        rafters.  From inside to outside (bottom to top):

          ┌─────────────────────────────────────────────┐  18 mm OSB (inner face)
          │            47 × 150 mm frame                │
          │  ┌───────────────────────────────────────┐  │  ─── 100 mm PIR insulation
          │  │                                       │  │
          │  │             [insulation]              │  │
          │  └───────────────────────────────────────┘  │  ─── 50 mm air gap
          │            (air gap maintained by frame)     │
          └─────────────────────────────────────────────┘  18 mm OSB (outer deck)

        Total pod depth = 18 + 150 + 18 = 186 mm.
        """
        # Outer pod width: clear opening between rafter faces minus 5 mm
        # tolerance each side so the pod slides in without binding.
        pod_w = _mm(self.spacing - RAF_W - 10)   # 10 mm total tolerance

        # Pod length = structural rafter length (wall plate to ridge only,
        # NOT including the overhang tail which stays open for ventilation).
        # Common pod
        cpod_l = r["common_struct_mm"]

        # Jack pods (one per unique jack length)
        jack_pods = []
        for jk in r["jack_lengths"]:
            jack_pods.append({
                "j":      jk["j"],
                "l_mm":   jk["struct_mm"],
                "qty":    jk["qty"],
            })

        # Frame timber per pod (two long sides + two short ends)
        # Long sides: 47 × 150 × pod_length  (2 per pod)
        # Short ends:  47 × 150 × (pod_w − 2×47)  (2 per pod, fit inside ends)
        frame_depth = INSUL_D + AIR_GAP    # = 150 mm  ← matches RAF_D exactly

        pod_total_depth = OSB_T + frame_depth + OSB_T

        return {
            "pod_width_mm":         pod_w,
            "pod_total_depth_mm":   pod_total_depth,
            "insul_depth_mm":       INSUL_D,
            "air_gap_mm":           AIR_GAP,
            "frame_depth_mm":       frame_depth,
            "common_pod_l_mm":      cpod_l,
            "n_common_pods":        r["n_common"],
            "jack_pods":            jack_pods,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # OSB optimisation
    # ─────────────────────────────────────────────────────────────────────────

    def _osb_optimisation(self, r: dict) -> dict:
        """
        Determine the most efficient way to cut pods from standard OSB sheets.

        Strategy
        --------
        Cut the 1220 mm dimension of each sheet into strips of pod_width.
        Each resulting strip is pod_width × 2440 mm.
        Pack pod panels (each pod_width × pod_length) along the 2440 mm strip.

        Two OSB faces are needed per pod (inner + outer deck).
        """
        pod_w  = r["pod_width_mm"]
        sh_l   = DEFAULT_OSB["l"]       # 2440
        sh_w   = DEFAULT_OSB["w"]       # 1220

        strips_per_sheet = math.floor(sh_w / pod_w)
        if strips_per_sheet < 1:
            strips_per_sheet = 1        # very wide pods – one strip per sheet

        # Build list of all panel lengths required (×2 for two faces per pod)
        panel_lengths: list[int] = []

        cpod_l = r["common_pod_l_mm"]
        for _ in range(r["n_common_pods"]):
            panel_lengths.append(cpod_l)
            panel_lengths.append(cpod_l)

        for jp in r["jack_pods"]:
            for _ in range(jp["qty"]):
                panel_lengths.append(jp["l_mm"])
                panel_lengths.append(jp["l_mm"])

        total_panels = len(panel_lengths)
        total_osb_area_m2 = round(
            sum(pod_w * l for l in panel_lengths) / 1e6, 2
        )

        # Bin-packing: first-fit decreasing into strips
        panel_lengths_sorted = sorted(panel_lengths, reverse=True)
        strips: list[int] = []     # each entry = remaining space in that strip

        for panel_l in panel_lengths_sorted:
            if panel_l > sh_l:
                # Panel too long for one sheet – flag but continue
                continue
            placed = False
            for i, rem in enumerate(strips):
                if rem >= panel_l:
                    strips[i] -= panel_l
                    placed = True
                    break
            if not placed:
                strips.append(sh_l - panel_l)

        n_strips = len(strips)
        n_sheets = math.ceil(n_strips / strips_per_sheet)

        # Waste
        used_area   = total_osb_area_m2
        bought_area = round(n_sheets * sh_l * sh_w / 1e6, 2)
        waste_pct   = round((1 - used_area / bought_area) * 100, 1) if bought_area else 0

        # Cutting schedule summary per sheet
        cutting_summary = _build_cutting_schedule(
            panel_lengths_sorted, pod_w, sh_l, sh_w, strips_per_sheet
        )

        return {
            "osb_sheet_label":      DEFAULT_OSB["label"],
            "osb_strips_per_sheet": strips_per_sheet,
            "osb_pod_w_mm":         pod_w,
            "osb_total_panels":     total_panels,
            "osb_total_area_m2":    total_osb_area_m2,
            "osb_sheets_required":  n_sheets,
            "osb_bought_area_m2":   bought_area,
            "osb_waste_pct":        waste_pct,
            "osb_cutting_schedule": cutting_summary,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Cut list
    # ─────────────────────────────────────────────────────────────────────────

    def _cut_list(self, r: dict) -> list[dict]:
        α    = self.pitch_deg
        cuts = []

        # 1. Ridge beam
        cuts.append({
            "item":    "Ridge Beam",
            "section": f"{RIDGE_W} × {RIDGE_D} mm C24",
            "length":  r["ridge_full_mm"],
            "qty":     1,
            "cuts":    f"Square end cuts. Install level at apex.",
            "notes":   (
                f"Spans {r['ridge_len_mm']} mm between hip rafter centres. "
                "For spans > 3 000 mm consider LVL or glulam."
            ),
        })

        # 2. Hip rafters
        cuts.append({
            "item":    "Hip Rafter",
            "section": f"{HIP_W} × {HIP_D} mm C24",
            "length":  r["hip_total_mm"],
            "qty":     4,
            "cuts": (
                f"Ridge end: compound cut — mitre {r['hip_ridge_mitre_deg']}°, "
                f"bevel {r['hip_ridge_bevel_deg']}°. "
                f"Eave end: plumb cut {r['hip_plumb_deg']}° + bird's mouth "
                f"({r['bird_mouth_depth_mm']} mm seat depth). "
                f"Backing bevel along top arris: {r['hip_backing_deg']}°."
            ),
            "notes":   (
                "Back the top arris with a plane or circular saw set to the "
                f"backing angle ({r['hip_backing_deg']}°) so the roof deck lies flat."
            ),
        })

        # 3. Common rafters
        if r["n_common"] > 0:
            cuts.append({
                "item":    "Common Rafter",
                "section": f"{RAF_W} × {RAF_D} mm C24",
                "length":  r["common_total_mm"],
                "qty":     r["n_common"],
                "cuts": (
                    f"Ridge end: plumb cut {r['plumb_cut_deg']}°. "
                    f"Eave: bird's mouth (seat {r['bird_mouth_depth_mm']} mm deep × "
                    f"{r['bird_mouth_width_mm']} mm wide). "
                    f"Tail: plumb cut {r['plumb_cut_deg']}° for fascia."
                ),
                "notes":   f"Spaced at {int(self.spacing)} mm c/c along ridge.",
            })

        # 4. Jack rafters (one entry per unique length, longest first)
        for jk in reversed(r["jack_lengths"]):
            cuts.append({
                "item":    f"Jack Rafter  (j = {jk['j']})",
                "section": f"{RAF_W} × {RAF_D} mm C24",
                "length":  jk["total_mm"],
                "qty":     jk["qty"],
                "cuts": (
                    f"Ridge end: plumb cut {r['plumb_cut_deg']}° PLUS side (cheek) cut "
                    f"{r['jack_side_cut_deg']}°. "
                    f"Eave: bird's mouth as common rafter. "
                    f"Tail: plumb cut {r['plumb_cut_deg']}°."
                ),
                "notes": (
                    f"Structural length (plate → hip) = {jk['struct_mm']} mm. "
                    "Side cut faces the hip rafter; bevel away from ridge."
                ),
            })

        # 5. Wall plates — long walls
        cuts.append({
            "item":    "Wall Plate (long walls)",
            "section": f"{WP_D} × {WP_W} mm C16 treated",
            "length":  r["wp_long_mm"],
            "qty":     2,
            "cuts":    "Square ends. Bed on DPC. Fix with frame anchors.",
            "notes":   "Pre-drill for anchor bolts at 600 mm c/c.",
        })

        # 6. Wall plates — end walls
        cuts.append({
            "item":    "Wall Plate (end walls)",
            "section": f"{WP_D} × {WP_W} mm C16 treated",
            "length":  r["wp_short_mm"],
            "qty":     2,
            "cuts":    "Square ends. Mitre corners to meet long-wall plates.",
            "notes":   "Halved or mortise-and-tenon corner joints recommended.",
        })

        # 7. Pod frame — long sides (47 × 150 mm)
        pod_frame_section = f"47 × {INSUL_D + AIR_GAP} mm CLS"
        pod_w = r["pod_width_mm"]
        pod_end_w = _mm(pod_w - 2 * RAF_W)   # end pieces fit between long sides

        # Common pod frames
        cpod_l = r["common_pod_l_mm"]
        n_cp   = r["n_common_pods"]
        cuts.append({
            "item":    "Pod Frame — Long Side (common pods)",
            "section": pod_frame_section,
            "length":  cpod_l,
            "qty":     n_cp * 2,
            "cuts":    "Square both ends. Two per pod.",
            "notes":   "CLS 47 × 150 mm; alternatively use 47 × 100 + 47 × 50 mm laminated.",
        })
        cuts.append({
            "item":    "Pod Frame — End Piece (common pods)",
            "section": pod_frame_section,
            "length":  pod_end_w,
            "qty":     n_cp * 2,
            "cuts":    "Square both ends. Two per pod (top and bottom).",
            "notes":   f"Width = pod_width − 2 × rafter width = {pod_end_w} mm.",
        })

        # Jack pod frames
        for jp in r["jack_pods"]:
            jl = jp["l_mm"]
            jq = jp["qty"]
            cuts.append({
                "item":    f"Pod Frame — Long Side (jack pod j={jp['j']})",
                "section": pod_frame_section,
                "length":  jl,
                "qty":     jq * 2,
                "cuts":    f"Square both ends. Two per pod. Length {jl} mm.",
                "notes":   f"Matches jack rafter structural length at position j={jp['j']}.",
            })
            cuts.append({
                "item":    f"Pod Frame — End Piece (jack pod j={jp['j']})",
                "section": pod_frame_section,
                "length":  pod_end_w,
                "qty":     jq * 2,
                "cuts":    "Square both ends.",
                "notes":   f"Width = {pod_end_w} mm.",
            })

        return cuts

    # ─────────────────────────────────────────────────────────────────────────
    # Timber running totals
    # ─────────────────────────────────────────────────────────────────────────

    def _timber_totals(self, r: dict) -> list[dict]:
        """Aggregate linear metres by section for ordering."""
        totals: dict[str, float] = {}

        def add(section, qty, length_mm):
            lm = qty * length_mm / 1000.0
            totals[section] = totals.get(section, 0.0) + lm

        for item in r["cut_list"]:
            add(item["section"], item["qty"], item["length"])

        rows = []
        for sec, lm in sorted(totals.items()):
            rows.append({
                "section": sec,
                "total_lm": round(lm, 2),
                "order_lm": round(lm * 1.10, 2),  # +10% waste allowance
            })
        return rows


# ─────────────────────────────────────────────────────────────────────────────
# OSB cutting schedule helper
# ─────────────────────────────────────────────────────────────────────────────

def _build_cutting_schedule(
    sorted_panels: list[int],
    pod_w: int,
    sh_l: int,
    sh_w: int,
    strips_per_sheet: int,
) -> list[dict]:
    """
    Build a human-readable sheet-by-sheet cutting schedule.
    Returns a list of sheet dicts, each with a list of strips,
    each strip containing a list of panel lengths cut from it.
    """
    # Bin-pack again, recording which panels go where
    strips: list[list[int]] = []    # each strip = list of panel lengths
    strip_rem: list[int]    = []    # remaining mm in each strip

    for panel_l in sorted_panels:
        if panel_l > sh_l:
            continue
        placed = False
        for i, rem in enumerate(strip_rem):
            if rem >= panel_l:
                strips[i].append(panel_l)
                strip_rem[i] -= panel_l
                placed = True
                break
        if not placed:
            strips.append([panel_l])
            strip_rem.append(sh_l - panel_l)

    # Group strips into sheets
    sheets = []
    for sheet_i, chunk in enumerate(
        [strips[i:i + strips_per_sheet] for i in range(0, len(strips), strips_per_sheet)]
    ):
        sheet_strips = []
        for strip_j, panels in enumerate(chunk):
            waste = sh_l - sum(panels)
            sheet_strips.append({
                "strip":   strip_j + 1,
                "panels":  panels,
                "waste_mm": waste,
            })
        sheets.append({
            "sheet": sheet_i + 1,
            "strips": sheet_strips,
        })
    return sheets
