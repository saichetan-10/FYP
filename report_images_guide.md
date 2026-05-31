# Report Images & Figures — Generation Guide
**Project:** Quantifying and Reducing Semantic Drift in Text-to-SQL Systems
**Report:** RVCE Major Project Report (report_overleaf_v5.zip)

---

## Quick Reference

| # | Type | Label | Status | Aspect Ratio |
|---|---|---|---|---|
| 1 | PNG Image | `rv_logo_watermark` | File exists in zip | 1:1 (circular) |
| 2 | Bar Chart (TikZ/pgfplots) | `fig:agent-scores` | Auto-rendered by LaTeX | 2:1 landscape |
| 3 | Architecture Diagram | `fig:architecture` | **MISSING — must be created** | 4:3 landscape |
| 4 | Table | `tab:drift-failure-modes` | Auto-rendered by LaTeX | Full-width, 3-col |
| 5 | Table | `tab:related-work` | Auto-rendered by LaTeX | Full-width, 5-col |
| 6 | Table | `tab:latency-breakdown` | Auto-rendered by LaTeX | Full-width, 3-col |
| 7 | Table | `tab:baseline-comparison` | Auto-rendered by LaTeX | Full-width, 4-col |

---

## IMAGE 1 — RV College of Engineering Logo Watermark

**File name:** `rv_logo_watermark.png`
**Location in zip:** `report_overleaf/rv_logo_watermark.png` (already exists)
**LaTeX source line:** 68

### Usage in Report
- Rendered as a full-page semi-transparent background watermark on every page of the document
- Placed at the exact center of each A4 page using a TikZ overlay node
- Opacity set to **6%** — extremely faint, just visible enough to brand the page without obscuring text

### LaTeX Code
```latex
\backgroundsetup{
  scale=1, angle=0, opacity=0.06,
  contents={%
    \begin{tikzpicture}[remember picture,overlay]
      \node at (current page.center)
        {\includegraphics[width=0.55\textwidth]{rv_logo_watermark}};
    \end{tikzpicture}%
  }
}
```

### Generation Description
- The official **RV College of Engineering (RVCE), Bengaluru** institutional crest/logo
- Typically a circular emblem or shield design featuring the college name, founding year, and symbolic motifs (torch, book, gears, or laurel wreath)
- Should be a **high-contrast dark image** (navy blue or black) so it remains visible at 6% opacity
- Must be saved as PNG with transparent or white background

### Dimensions & Ratio
- **Aspect Ratio:** 1:1 (square or circular)
- **Rendered size:** 55% of textwidth (~82mm wide on A4 with 1.25in left margin)
- **Recommended export resolution:** 300 DPI minimum for print quality
- **Recommended pixel size:** At least 1000×1000 px

---

## FIGURE 1 — Per-Agent Mean Contribution Scores Bar Chart

**Label:** `fig:agent-scores`
**LaTeX source lines:** 488–519
**Chapter:** Chapter 3 — System Design and Architecture (Section: High-Level Architecture)

### Caption (exact from report)
> "Mean contribution scores per agent across the ten test queries. The IntentParser shows the widest variation (range 0.71–0.92), confirming it as the primary driver of elevated drift. The ConstraintValidator achieves near-perfect scores because most constraint rules are deterministic and the SQL builder enforces primary constraints by default."

### Chart Type
Vertical grouped bar chart (pgfplots `ybar` style)

### Data Points

| Agent | Mean Score |
|---|---|
| IntentParser | 0.832 |
| OntologyMapper | 0.956 |
| ConstraintValidator | 0.945 |
| ExecPlanner | 1.000 |
| ResultVerifier | 0.843 |

### Visual Specification
- **X-axis:** 5 categorical bars — `IntentParser`, `OntologyMapper`, `ConstraintValidator`, `ExecPlanner`, `ResultVerifier`
- **X-axis labels:** Rotated 15° clockwise, anchored to east, `\scriptsize` font (~8pt)
- **Y-axis:** `Mean Score (0–1)`, range `0` to `1.12`, tick marks at `0, 0.2, 0.4, 0.6, 0.8, 1.0`
- **Y-axis label:** `Mean Score (0–1)`, `\footnotesize` font
- **Title:** `Per-Agent Mean Contribution Scores (10 Test Queries)`, `\small` font
- **Bar fill color:** Light blue (`blue!25` in LaTeX = ~`#BFD7FF`)
- **Bar border color:** Medium blue (`blue!60` = ~`#6699FF`)
- **Bar width:** Narrow — 0.55cm in LaTeX units
- **Value labels:** Displayed above each bar, `\scriptsize` font, 1pt vertical offset
- **Grid:** No explicit grid lines specified
- **Background:** White

### Dimensions & Ratio
- **LaTeX dimensions:** `width=10cm, height=5cm`
- **Aspect Ratio:** **2:1 landscape**
- **Recommended export size:** 1000×500 px at 150 DPI, or 2000×1000 px at 300 DPI

### Context in Report
This figure appears in Section 3.2 (High-Level Architecture) but is actually a results summary chart. The surrounding text explains:
- IntentParser has widest score range (0.71–0.92), making it the primary source of drift
- OntologyMapper scores 1.0 for the 8 most common business terms, drops to ~0.75 for specialised terms like "gross margin" and "return rate"
- ConstraintValidator near-perfect (9 of 10 queries at 1.0) because rules are deterministic
- ExecutionPlanner achieved 100% SQL validity (all queries syntactically valid)
- ResultVerifier most effective for simple aggregation queries

### NOTE — Label Mismatch Bug
The text at line 486 says:
```
Figure~\ref{fig:architecture} shows the high-level component layout.
```
But the figure defined immediately after has `\label{fig:agent-scores}`, not `fig:architecture`. This means **the compiled PDF will show `??`** in place of the figure number for the architecture reference. See Figure 2 below for the missing diagram.

---

## FIGURE 2 — High-Level System Architecture Diagram (MISSING)

**Label:** `fig:architecture`
**Referenced at:** Line 486 of `main_report.tex`
**Status:** Referenced in text but **no figure with this label exists in the report** — this figure must be created and inserted

### Caption (to be written — suggested)
> "High-level component architecture of the Text-to-SQL system. The five-agent pipeline processes each query through sequential stages, consulting a shared BusinessOntology graph. The CriticLoopOrchestrator re-invokes the pipeline until the composite drift score D falls below 0.15 or five iterations are exhausted."

### What the Figure Should Show
Based on Chapter 3 (System Design and Architecture) description across lines 464–481:

#### Components to Include

**User Layer (Top)**
- Box: `User / Business Analyst`
- Input: Natural language query string (e.g., "show me total revenue by region excluding taxes")
- Arrow pointing down into the pipeline

**Five-Agent Pipeline (Center, left-to-right flow)**
Each agent is a rounded rectangle box with:

1. `IntentParser` — Extracts entities, metrics, grouping keys, filters using regex pattern matching. Falls back to Claude LLM if patterns fail.
2. `OntologyMapper` — Resolves entity tokens to ontology nodes using SequenceMatcher string similarity (threshold: 0.75). ChromaDB vector path available but not activated.
3. `ConstraintValidator` — Evaluates 9 named business rules (e.g., R01_TAX_EXCLUSION, R02_ACTIVE_ONLY). Deterministic rule lookup.
4. `ExecutionPlanner` — Constructs SQL string from GROUP_BY_CONFIG templates + METRIC_SELECT expressions. Optional ClaudeExecutionPlanner fallback.
5. `ResultVerifier` — Executes SQL against SQLite backend, computes Z-score plausibility vs historical baselines, checks row-count sanity.

**Shared Knowledge Component (Center)**
- `BusinessOntology` (NetworkX DiGraph)
- Contains: 11 entities, 12 metrics, 9 constraint rules, join path rules
- Connected with bidirectional dashed arrows to all 5 agents

**Drift Scoring Layer (Right side)**
- `SemanticDriftMetric`
- Receives: `a_i` (intent alignment, 40%), `a_c` (constraint adherence, 30%), `a_p` (result plausibility, 30%)
- Outputs: Composite drift score `D ∈ [0,1]`
- Formula: `D = 0.4(1−aᵢ) + 0.3(1−aᶜ) + 0.3(1−aₚ)`

**Critic Loop Orchestrator (Surrounding wrapper)**
- `CriticLoopOrchestrator` — large rounded rectangle wrapping the entire pipeline
- Loop condition: `D < 0.15` → serve result; else generate feedback message and re-invoke
- Max iterations: 5
- Shows iteration counter and feedback arrow looping back to IntentParser

**Databases (Bottom)**
- 5 SQLite databases shown as cylinder shapes:
  - `sales.db` (primary, 300K rows in orders table)
  - `inventory.db`
  - `analytics.db`
  - `hr.db`
  - `finance.db`
- Arrow from ResultVerifier down to databases

**Optional Enhancement Layer (Top-right)**
- `Claude LLM API` box (dashed border to indicate optional)
- Connected to IntentParser and ExecutionPlanner with dashed arrows

**Output Layer (Bottom-right)**
- `FastAPI REST API` — 8 endpoints, port 8000
- `Streamlit Dashboard` — real-time monitoring, port 8501
- Both receive output from CriticLoopOrchestrator

**Shared State**
- `QueryState` dataclass — shown as a small note/annotation connecting agents, indicating it is the communication medium passed between all pipeline stages

### Visual Style
- Clean technical architecture diagram — professional, minimal
- Rounded rectangle boxes for all components
- Cylinder shapes for databases
- Dashed box for optional Claude LLM layer
- Directional arrows (solid for main data flow, dashed for optional/reference)
- Color coding suggestion:
  - Blue: Agent pipeline boxes
  - Green: Ontology
  - Orange: Drift metric
  - Gray: Databases
  - Purple/dashed: Optional LLM layer
  - Red outline: CriticLoop wrapper

### Dimensions & Ratio
- **Aspect Ratio:** 4:3 landscape (or 16:9)
- **Recommended export size:** 1600×1200 px (4:3) or 1920×1080 px (16:9)
- **Minimum for print:** 300 DPI equivalent

### Tools to Create This
- **draw.io / diagrams.net** — recommended, free, exports clean PNG/PDF
- **Lucidchart** — professional alternative
- **TikZ** (LaTeX) — keep consistent with existing report style, use `\begin{tikzpicture}` with the `box`, `sbox`, `ebox`, `dbox`, `arr` styles already defined in the preamble (lines 74–88 of `main_report.tex`)
- **Figma / Canva** — for non-technical design approach

---

## TABLE 1 — Semantic Drift Failure Mode Categories with Examples

**Label:** `tab:drift-failure-modes`
**LaTeX source lines:** 233–247
**Chapter:** Chapter 1 — Introduction (Section: Problem Statement)

### Caption
> "Semantic Drift Failure Mode Categories with Examples"

### Content

| Drift Type | User Intent | Actual SQL Behaviour |
|---|---|---|
| Entity drift | "list clients" → COUNT customers | COUNT orders returned instead |
| Constraint drift | "excluding taxes" → net revenue | Gross revenue returned, tax not subtracted |
| Plausibility drift | "revenue last month" → $2.1M | $21M returned (join explosion with order_items) |

### LaTeX Specification
- Environment: `tabularx` with full `\textwidth`
- Column widths: auto-fit via `X` column type for middle columns; left-aligned (`l`) for first column
- Row stretch: 1.3 (`\arraystretch`)
- Style: `booktabs` (toprule, midrule, bottomrule — no vertical lines)
- Header: Bold labels

### Dimensions & Ratio
- **Aspect Ratio:** Full textwidth, 3 columns, very short (3 data rows) — approximately **8:1 wide landscape**
- **Rendered height:** ~3cm in document

---

## TABLE 2 — Comparison of Related Text-to-SQL Systems

**Label:** `tab:related-work`
**LaTeX source lines:** 439–456
**Chapter:** Chapter 2 — Literature Review (Section: Comparison of Related Systems)

### Caption
> "Comparison of Related Text-to-SQL Systems"

### Content

| System | Approach | Benchmark | Accuracy | Limitation |
|---|---|---|---|---|
| Seq2SQL | Seq2Seq + RL | WikiSQL | 59.4% exec. | Single-table, no joins |
| SQLNet | Sketch-based | WikiSQL | 68.0% exec. | Template-constrained |
| IRNet | BERT + sketch | Spider | 53.2% exact | No constraint rules |
| RAT-SQL | Graph + BERT | Spider | 69.7% exact | No plausibility check |
| PICARD | Constrained decoding | Spider | 75.1% exact | No feedback loop |
| **This work** | Ontology + 5-agent | Synthetic e-comm. | **90% success** | Domain-specific ontology |

### LaTeX Specification
- Environment: `tabularx` with full `\textwidth`
- 5 columns: `l X X X X` (first column left-fixed, rest auto-expand)
- Row stretch: 1.3
- Style: `booktabs` (no vertical lines)
- Header: Bold labels

### Dimensions & Ratio
- **Aspect Ratio:** Full textwidth, 5 columns, 6 data rows — approximately **5:2 wide landscape**

---

## TABLE 3 — Per-Stage Latency Breakdown

**Label:** `tab:latency-breakdown`
**LaTeX source lines:** 536–555
**Chapter:** Chapter 3 (placed in Chapter 5 results section in narrative) — Section: System Latency and Throughput

### Caption
> "Per-Stage Latency Breakdown (Single-Pass Query, Mean of 10 Runs)"

### Environment / Machine
- Apple M2, 16 GB RAM
- SQLite stored on NVMe SSD
- 300,000-row orders table

### Content

| Pipeline Stage | Mean Latency (ms) | Notes |
|---|---|---|
| Intent parsing | 28 | Regex compilation amortised at module load |
| Ontology mapping | 14 | SequenceMatcher over 11 entities + 12 metrics |
| Constraint validation | 6 | Deterministic rule evaluation, no I/O |
| SQL generation | 12 | Pure string construction |
| **Database execution** | **980** | SQLite full-scan on 300K-row orders table |
| Drift computation | 3 | Pure Python Z-score + adherence ratio |
| **Total (single pass)** | **1,043** | Excludes network overhead |

### Key Insight
Database execution at 980ms = **94% of total single-pass time**. All other stages combined = 63ms (6%).

### LaTeX Specification
- Environment: `tabularx` with full `\textwidth`
- 3 columns: `l r l` (stage left, latency right-aligned, notes left)
- Row stretch: 1.2
- Has midrule before Total row
- Total row in **bold**

### Dimensions & Ratio
- **Aspect Ratio:** Full textwidth, 3 columns, 7 rows — approximately **6:1 wide landscape**

---

## TABLE 4 — Per-Query Drift Comparison: Baseline vs Critic Loop

**Label:** `tab:baseline-comparison`
**LaTeX source lines:** 579–602
**Chapter:** Chapter 5 — Evaluation (Section: Comparison with Baseline)

### Caption
> "Per-Query Drift Comparison: Baseline vs Critic Loop"

### Content

| Query Summary | Baseline D (Iter. 1) | Final D | Reduction (%) |
|---|---|---|---|
| Total revenue by region, excl. taxes | 0.073 | 0.073 | 0.0 |
| Top 5 products by revenue last quarter | 0.096 | 0.096 | 0.0 |
| Customer count by tier YTD | 0.066 | 0.066 | 0.0 |
| YoY revenue comparison | 0.189 | 0.113 | 40.2 |
| Average order value by product category | 0.198 | 0.116 | 41.4 |
| Orders with status Shipped last month | 0.074 | 0.074 | 0.0 |
| Gross margin by supplier | 0.235 | 0.178 | 24.3 |
| Customers with LTV > $1,000 | 0.090 | 0.090 | 0.0 |
| Monthly revenue trend for 2024 | 0.201 | 0.122 | 39.3 |
| Return rate by product category | 0.262 | 0.205 | 21.8 |
| **Mean** | **0.148** | **0.113** | **23.6** |

### Key Insights from Data
- 6 of 10 queries converged on first pass (0% improvement) — these were already below D < 0.15
- Best improvement: Average order value by product category — 41.4% reduction
- Hardest query: Return rate by product category — still D = 0.205 after 5 iterations (above 0.15 threshold, did not converge)
- Mean drift reduced from 0.187 (4-query subset) / 0.148 (all 10) to 0.113

### LaTeX Specification
- Environment: `tabularx` with full `\textwidth`
- 4 columns: `X c c c` (query description auto-width, three numeric columns centered)
- Row stretch: 1.3
- Mean row in **bold**, separated by midrule

### Dimensions & Ratio
- **Aspect Ratio:** Full textwidth, 4 columns, 10 data rows + header + mean row — approximately **4:1 wide landscape**

---

## Report-Level Notes

### Label Bug (Action Required)
In `main_report.tex` at **line 486**:
```latex
Figure~\ref{fig:architecture} shows the high-level component layout.
```
The figure defined immediately after (lines 488–519) uses `\label{fig:agent-scores}`, not `\label{fig:architecture}`. This will render as `Figure ??` in the compiled PDF.

**Fix options:**
1. Create a proper architecture diagram (Figure 2 above) and insert it before line 488 with `\label{fig:architecture}`, then keep the bar chart as a separate figure
2. Change the reference at line 486 to `\ref{fig:agent-scores}` and update the surrounding caption text accordingly

### TikZ Styles Available in Preamble (lines 74–88)
These styles are pre-defined and can be reused for any TikZ-based diagram you add:
```
box   — blue-tinted rounded rectangle, 5cm wide
sbox  — gray-tinted rounded rectangle, 3.2cm wide (sub-component)
ebox  — green-tinted rounded rectangle, 2.6cm wide (external)
dbox  — orange-tinted diamond (decision node)
arr   — thick solid arrow with Stealth head
aarr  — thin lighter arrow (auxiliary/reference)
```

### Page Format
- Document class: A4, 12pt, twoside
- Margins: top 1in, bottom 1in, left 1.25in, right 1in
- Textwidth ≈ 150mm (after margins)
- All figures use `[H]` float placement (exact position, no floating)
