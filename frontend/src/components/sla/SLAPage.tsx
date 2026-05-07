import React, { useRef, useState } from 'react';
import {
  AlertTriangle, CheckCircle, ChevronDown, ChevronUp,
  FileText, Shield, TrendingDown, Upload, Zap, BookOpen, Info, BarChart2, Table2
} from 'lucide-react';
import { API_BASE_URL } from '../../services/api';
import './SLAPage.css';

// ── Types ─────────────────────────────────────────────────────────────────────

interface SLAClause {
  clause_type:         string;
  raw_text:            string;
  section_context:     string;
  value:               number | null;
  unit:                string;
  currency:            string;
  confidence:          'HIGH' | 'MEDIUM' | 'LOW';
  bottleneck_severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'NONE';
  bottleneck_reason:   string;
}

interface SLAParseResponse {
  total_clauses:         number;
  critical_count:        number;
  high_risk_count:       number;
  overall_confidence:    string;
  penalty_rate:          number | null;
  flat_fee_per_day:      number | null;
  force_majeure_applies: boolean;
  cap_limit:             number | null;
  clauses:               SLAClause[];
  bottleneck_clauses:    SLAClause[];
  llm_assisted:          boolean;
}

interface SLAPenaltyDetail {
  financial_penalty:  number;
  effective_delay:    number;
  grace_days_applied: number;
  contract_type:      string;
  otif_breach_level:  string;
  otif_multiplier:    number;
  penalty_source:     string;
  breach_level:       string;
}

interface SLAAnalysisResult {
  contract_text_preview: string;
  extraction:            SLAParseResponse;
  penalty:               SLAPenaltyDetail | null;
  risk_score:            number;
  severity_distribution: Record<string, number>;
  top_bottlenecks:       SLAClause[];
  processing_pipeline:   string[];
}

interface NegotiateResult {
  supplier_id:      string;
  strategy:         string;
  suggested_actions: string[];
  leverage_clauses: SLAClause[];
  penalty_summary:  any[];
  status:           string;
}

interface ShipmentFinding {
  shipment_id:    string;
  order_value:    number;
  delay_days:     number;
  otif_actual:    number | null;
  in_full_pct:    number;
  contract_type:  string;
  customer_tier:  string;
  route:          string;
  carrier:        string;
  breach_level:   'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'NONE';
  penalty_amount: number;
}

interface CsvInsight {
  severity: string;
  message:  string;
}

interface CsvFindingsResult {
  total_shipments:     number;
  on_time_count:       number;
  breach_count:        number;
  avg_otif_pct:        number | null;
  avg_delay_days:      number;
  total_penalty_usd:   number;
  breach_distribution: Record<string, number>;
  otif_threshold_used: number;
  detected_columns:    string[];
  insights:            CsvInsight[];
  shipments:           ShipmentFinding[];
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function authHeader(): HeadersInit {
  const token = localStorage.getItem('access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function severityColor(sev: string): string {
  return (
    sev === 'CRITICAL' ? '#dc2626' :
    sev === 'HIGH'     ? '#f97316' :
    sev === 'MEDIUM'   ? '#d97706' :
    sev === 'LOW'      ? '#059669' : '#94a3b8'
  );
}

function severityBg(sev: string): string {
  return (
    sev === 'CRITICAL' ? 'rgba(220,38,38,0.1)' :
    sev === 'HIGH'     ? 'rgba(249,115,22,0.1)' :
    sev === 'MEDIUM'   ? 'rgba(217,119,6,0.1)' :
    sev === 'LOW'      ? 'rgba(5,150,105,0.1)' : 'rgba(148,163,184,0.1)'
  );
}

function riskScoreColor(score: number): string {
  if (score <= 30) return '#059669';
  if (score <= 60) return '#d97706';
  if (score <= 80) return '#f97316';
  return '#dc2626';
}

function fmt(n: number | null, unit: string): string {
  if (n === null) return '—';
  if (unit === 'pct_per_day') return `${(n * 100).toFixed(2)}% / day`;
  if (unit === 'pct_total')   return `${(n * 100).toFixed(1)}% of total`;
  if (unit === 'pct')         return `${n}%`;
  if (unit === 'days')        return `${n} days`;
  if (unit === 'flat_per_day') return `$${n.toLocaleString()} / day`;
  if (unit === 'flat_total')   return `$${n.toLocaleString()}`;
  if (unit === 'pct_per_annum') return `${(n * 100).toFixed(2)}% p.a.`;
  return String(n);
}

function labelClauseType(t: string): string {
  return t.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

// ── Sub-components ────────────────────────────────────────────────────────────

const SeverityBadge: React.FC<{ sev: string }> = ({ sev }) => (
  <span
    className="sla-badge"
    style={{ color: severityColor(sev), background: severityBg(sev), borderColor: severityColor(sev) }}
  >
    {sev}
  </span>
);

const ConfidenceDot: React.FC<{ conf: string }> = ({ conf }) => {
  const color = conf === 'HIGH' ? '#059669' : conf === 'MEDIUM' ? '#d97706' : '#dc2626';
  return <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: color, marginRight: 6 }} />;
};

const ClauseRow: React.FC<{ clause: SLAClause }> = ({ clause }) => {
  const [open, setOpen] = useState(false);
  return (
    <div className="sla-clause-row" style={{ borderLeft: `3px solid ${severityColor(clause.bottleneck_severity)}` }}>
      <div className="sla-clause-header" onClick={() => setOpen(o => !o)}>
        <div className="sla-clause-left">
          <SeverityBadge sev={clause.bottleneck_severity} />
          <span className="sla-clause-type">{labelClauseType(clause.clause_type)}</span>
          {clause.value !== null && (
            <span className="sla-clause-value">{fmt(clause.value, clause.unit)}</span>
          )}
        </div>
        <div className="sla-clause-right">
          <ConfidenceDot conf={clause.confidence} />
          <span className="sla-clause-conf">{clause.confidence}</span>
          {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </div>
      </div>
      {open && (
        <div className="sla-clause-detail">
          <div className="sla-clause-text">"{clause.raw_text}"</div>
          {clause.bottleneck_reason && (
            <div className="sla-clause-reason">
              <AlertTriangle size={12} /> {clause.bottleneck_reason}
            </div>
          )}
          {clause.section_context && (
            <div className="sla-clause-section">Section: {clause.section_context}</div>
          )}
        </div>
      )}
    </div>
  );
};

// ── Contract Document Viewer ───────────────────────────────────────────────────

const ARTICLES = [
  { id: 'art1', num: 'I',   title: 'Definitions and Interpretation' },
  { id: 'art2', num: 'II',  title: 'Service Level Commitments' },
  { id: 'art3', num: 'III', title: 'Penalty and Liquidated Damages Framework' },
  { id: 'art4', num: 'IV',  title: 'Force Majeure and Excused Performance' },
  { id: 'art5', num: 'V',   title: 'Audit, Reporting and Governance' },
  { id: 'art6', num: 'VI',  title: 'Dispute Resolution and Governing Law' },
  { id: 'art7', num: 'VII', title: 'General Provisions' },
];

const Xref: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <span className="sla-doc-xref">{children}</span>
);

const Def: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <span className="sla-doc-def">{children}</span>
);

const ArticleBlock: React.FC<{ id: string; num: string; title: string; children: React.ReactNode }> = ({ id, num, title, children }) => {
  const [open, setOpen] = useState(true);
  return (
    <div className="sla-doc-article" id={id}>
      <div className="sla-doc-article-header" onClick={() => setOpen(o => !o)}>
        <span className="sla-doc-article-num">ARTICLE {num}</span>
        <span className="sla-doc-article-title">{title}</span>
        <span className="sla-doc-article-chevron">{open ? <ChevronUp size={14}/> : <ChevronDown size={14}/>}</span>
      </div>
      {open && <div className="sla-doc-article-body">{children}</div>}
    </div>
  );
};

const ContractViewer: React.FC = () => {
  const scrollTo = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  return (
    <div className="sla-contract-layout">

      {/* Sticky TOC */}
      <aside className="sla-doc-toc glass-panel">
        <div className="sla-doc-toc-title">Table of Contents</div>
        <div className="sla-doc-toc-meta">
          <span>Master Logistics Services Agreement</span>
          <span>v3.11-FINAL · Eff. 01 Apr 2026</span>
        </div>
        {ARTICLES.map(a => (
          <button key={a.id} className="sla-doc-toc-item" onClick={() => scrollTo(a.id)}>
            <span className="sla-doc-toc-num">Art. {a.num}</span>
            <span className="sla-doc-toc-label">{a.title}</span>
          </button>
        ))}
        <div className="sla-doc-toc-legend">
          <div className="sla-doc-legend-item"><span className="sla-doc-xref">§ ref</span> Cross-reference</div>
          <div className="sla-doc-legend-item"><span className="sla-doc-def">Term</span> Defined term</div>
        </div>
        <div className="sla-doc-complexity-bar">
          <div className="sla-doc-complexity-label"><Info size={11}/> Interpretation Complexity</div>
          <div className="sla-doc-complexity-track"><div className="sla-doc-complexity-fill" style={{width:'87%', background:'#dc2626'}}/></div>
          <span className="sla-doc-complexity-score">87 / 100 — Extreme</span>
        </div>
      </aside>

      {/* Document body */}
      <div className="sla-doc-body glass-panel">

        {/* Document header */}
        <div className="sla-doc-masthead">
          <div className="sla-doc-stamp">EXECUTED COPY</div>
          <h1 className="sla-doc-main-title">MASTER LOGISTICS SERVICES AGREEMENT</h1>
          <p className="sla-doc-subtitle">Including Schedules 1-A through 9-F, Annexures I–XIV, and all Side Letters dated on or after the Commencement Date (as defined herein)</p>
          <div className="sla-doc-parties">
            <div className="sla-doc-party"><span>Service Provider</span><strong>Fiscalogix Freight Solutions Pvt. Ltd.</strong><em>CIN: U74900MH2019PTC321654 ("Provider")</em></div>
            <div className="sla-doc-party-and">AND</div>
            <div className="sla-doc-party"><span>Principal Buyer</span><strong>[Counterparty Entity Name] ("Buyer")</strong><em>As further identified in Schedule 1-A, Part III, Row 7</em></div>
          </div>
          <div className="sla-doc-meta-row">
            <div><span>Effective Date</span><strong>01 April 2026</strong></div>
            <div><span>Initial Term</span><strong>36 calendar months (subject to <Xref>§ 7.4.1(b)</Xref>)</strong></div>
            <div><span>Governing Law</span><strong>Laws of England and Wales (Arbitration per <Xref>§ 6.2</Xref>)</strong></div>
            <div><span>Version</span><strong>v3.11-FINAL (supersedes v3.10-RC2 and all prior drafts)</strong></div>
          </div>
        </div>

        {/* Article I */}
        <ArticleBlock id="art1" num="I" title="Definitions and Interpretation">
          <p className="sla-doc-preamble">In this Agreement, unless the context otherwise expressly requires or a contrary intention is evident from the surrounding provisions, the following terms shall bear the meanings ascribed to them below, and references to the singular shall include the plural and vice versa, references to any gender shall include all genders, and references to a statute or statutory provision include that statute or provision as amended, extended, re-enacted or consolidated from time to time and any orders, regulations, instruments or other subordinate legislation made under it:</p>
          <div className="sla-doc-defs-grid">
            {[
              { term: '"Adjusted OTIF Rate"', def: 'Shall have the meaning set forth in Schedule 4-B, Clause 3.2, as recalculated quarterly in accordance with the Measurement Methodology described in § 2.2.3, subject to the Exclusion Event carve-outs enumerated in Annex VII and any Exceptional Volume Adjustment agreed under § 2.4.2(c)(iii), but expressly excluding any periods classified as Force Majeure Events (§ 4.1) or Calendar Exceptions (as defined herein).' },
              { term: '"Calendar Exception"', def: 'Any day designated as a public or bank holiday in any jurisdiction through which a Consignment (as defined herein) passes during any segment of its Transit Journey (§ 2.1.4), including but not limited to gazetted holidays, state-specific closures, and any day on which the relevant Port Authority (§ 1 passim) suspends or materially curtails operations for any reason, which definition shall be deemed to incorporate the Rolling Exception Calendar maintained by Provider under § 5.3.1 and updated not less than fourteen (14) Business Days prior to each Measurement Window.' },
              { term: '"Cascading Penalty Multiplier"', def: 'The product obtained by applying sequentially (a) the Base Rate as specified in Schedule 3-A Column D, (b) the OTIF Tier Coefficient from Schedule 3-B, (c) the Concentration Factor computed under § 3.2.4(b), and (d) the Annualised Volume Adjustment Factor set out in Annex IX, Table 2, Row applicable to the Buyer\'s trailing-twelve-month shipped volume, the result of which shall in no case exceed the Aggregate Liability Cap save as provided in § 3.3.2(f).' },
              { term: '"Commencement Date"', def: 'The later of (i) 01 April 2026, or (ii) the date on which the last of the Conditions Precedent enumerated in Schedule 9-A has been satisfied or waived in writing by both Parties, provided that if the Commencement Date so determined falls on a day that is not a Business Day in Mumbai, London, and the jurisdiction of the relevant Port Authority simultaneously, the Commencement Date shall be deemed to be the immediately following day that satisfies all three criteria.' },
              { term: '"Consignment"', def: 'Any cargo, goods, materials, or articles tendered by or on behalf of the Buyer for carriage by the Provider pursuant to an individual Shipment Order (as defined herein), irrespective of whether such cargo is consolidated, groupaged, or shipped as a full container load (FCL), less-than-container load (LCL), break-bulk, or any other mode, together with all associated documentation, including but not limited to the Bill of Lading, Packing List, Commercial Invoice, Certificate of Origin, and any phytosanitary, veterinary, or regulatory certificates required under Applicable Law (§ 1 passim).' },
              { term: '"Effective Delay Period"', def: 'The number of calendar days (or fractions thereof, calculated to two decimal places using the methodology in Annex III, § 3.1) by which the Actual Delivery Date exceeds the Contractual Delivery Date, after deducting (i) any Grace Period (§ 3.1.2), (ii) any days attributable to a Buyer-Caused Delay (§ 2.3.4(a)), and (iii) any days falling within a validated Force Majeure Period (§ 4.3.2), but before application of the Cascading Penalty Multiplier (§ 1 passim) and subject to the minimum threshold in § 3.1.1(c).' },
              { term: '"OTIF Threshold"', def: 'Ninety-four point five percent (94.5%) on-time and in-full delivery performance measured over any rolling thirteen (13) week period (the "Measurement Window"), adjusted as follows: (a) upward by 1.5 percentage points for Buyer\'s classified as Tier-1 (§ 1, "Tier Classification"); (b) downward by 2.0 percentage points during any Elevated Congestion Period (§ 2.2.6) declared by Provider with no less than 72 hours\' written notice; and (c) subject to mutual written agreement for any period during which Exceptional Volume (as defined in Schedule 4-B) is tendered, it being agreed that no such adjustment shall cumulatively reduce the OTIF Threshold below 88.0% without the prior written consent of the Buyer\'s authorised signatory (§ 5.4.1(b)).' },
            ].map(({ term, def }) => (
              <div key={term} className="sla-doc-def-row">
                <div className="sla-doc-def-term"><Def>{term}</Def></div>
                <div className="sla-doc-def-body">{def}</div>
              </div>
            ))}
          </div>
          <p className="sla-doc-clause" style={{marginTop: 16}}>
            <span className="sla-doc-clause-num">1.2</span>
            <span><strong>Rules of Interpretation.</strong> Unless the context requires otherwise: (a) any reference to "days" shall mean calendar days unless qualified as "Business Days"; (b) "including" means "including without limitation"; (c) headings are for convenience only and shall not affect interpretation; (d) references to "writing" include electronic communications meeting the authentication standard in Schedule 8-C; (e) where two or more provisions conflict, the order of precedence shall be: (i) this Agreement; (ii) Schedules 1-A through 5-F; (iii) Annexures; (iv) Shipment Orders — notwithstanding that a specific Shipment Order may purport to override this precedence, which purported override shall be of no effect save to the extent authorised in advance in writing under § 7.3.2.</span>
          </p>
        </ArticleBlock>

        {/* Article II */}
        <ArticleBlock id="art2" num="II" title="Service Level Commitments">
          <p className="sla-doc-clause">
            <span className="sla-doc-clause-num">2.1</span>
            <span><strong>Primary Service Standard.</strong> Subject always to the conditions set out in §§ 2.3, 2.4, and 4.1, and without prejudice to the Provider's right to invoke the Cascading Measurement Adjustment as defined in <Xref>Schedule 4-B § 3.7</Xref>, the Provider shall deliver each Consignment On-Time and In-Full ("OTIF") in accordance with the <Def>OTIF Threshold</Def> and the Transit Time Matrix appended as <Xref>Schedule 2-D</Xref>, which Matrix shall be deemed automatically updated upon any Route Amendment Notice (§ 2.1.6) issued not less than ten (10) Business Days prior to the commencement of the affected Measurement Window, save where such Route Amendment Notice triggers a Material Variation Event (§ 7.3.1), in which case the amendment shall require mutual written agreement before taking effect.</span>
          </p>
          <div className="sla-doc-clause">
            <span className="sla-doc-clause-num">2.2</span>
            <div>
              <strong>Measurement Methodology.</strong>
              <div className="sla-doc-subclause">
                <span className="sla-doc-clause-num">2.2.1</span>
                <span>OTIF performance shall be computed by Provider's Logistics Intelligence Platform ("LIP") using the formula: <span className="sla-doc-formula">OTIF% = (Qualifying Deliveries ÷ Total Tendered Consignments) × 100</span>, where "Qualifying Deliveries" excludes any Consignment (i) affected by a Buyer-Caused Delay; (ii) for which a valid Proof of Delivery was not obtainable due to a Systemic Documentation Failure (as defined in <Xref>Annex VI § 2.1</Xref>); or (iii) classified as a Test Shipment (§ 2.2.8) — provided that exclusions under (i)–(iii) collectively shall not exceed 3.0% of Total Tendered Consignments in any Measurement Window without the Buyer's express prior written consent.</span>
              </div>
              <div className="sla-doc-subclause">
                <span className="sla-doc-clause-num">2.2.2</span>
                <span>For the avoidance of doubt, "In-Full" shall mean delivery of not less than ninety-eight percent (98%) of the ordered quantity by weight, count, or volume, whichever is the lower as a proportion of the total Consignment value, where "value" is determined by reference to the Commercial Invoice submitted at the time of booking, adjusted pro-rata for any partial substitution authorised under a Contingency Cargo Protocol (§ 2.4.3).</span>
              </div>
              <div className="sla-doc-subclause">
                <span className="sla-doc-clause-num">2.2.3</span>
                <span>The Measurement Window shall be a rolling thirteen (13) complete calendar weeks, assessed as at 23:59:59 hours Indian Standard Time on the last day of each such week, except where a Calendar Exception falls on such last day, in which case the Measurement Window shall be extended by the number of Calendar Exception days encountered, up to a maximum of five (5) additional days, subject always to § 2.2.4.</span>
              </div>
              <div className="sla-doc-subclause">
                <span className="sla-doc-clause-num">2.2.4</span>
                <span><strong>(Interaction with Force Majeure)</strong> Any day falling within a validated Force Majeure Period (§ 4.3.2) shall be excluded from the Measurement Window denominator but shall not extend the Window beyond the Contractual Quarter End, as defined in <Xref>Schedule 5-A § 1.1</Xref>, such exclusion to be computed after all Calendar Exception extensions under § 2.2.3 have been applied but before the Cascading Penalty Multiplier (§ 1) is determined.</span>
              </div>
            </div>
          </div>
          <p className="sla-doc-clause">
            <span className="sla-doc-clause-num">2.3</span>
            <span><strong>Exclusion Events.</strong> Provider's obligation to meet the OTIF Threshold shall be suspended (but not extinguished) during, and to the extent directly caused by, any one or more of the following events: (a) Buyer-Caused Delays, including without limitation failure to tender Consignments with accurate documentation, late provision of Letters of Credit, refusal of customs examiners directly attributable to Buyer's cargo misclassification, or Buyer-directed route changes communicated less than forty-eight (48) hours prior to the Contractual Pickup Time; (b) Port Congestion Events at any Port of Loading or Port of Discharge where average vessel waiting time exceeds seventy-two (72) hours, as evidenced by data published by the relevant Port Authority or, in the absence of such publication, by Lloyd's List Intelligence or an equivalent recognised industry source agreed by the Parties in writing; (c) Sovereign Interventions, including customs embargoes, export licensing suspensions, or temporary import bans introduced after the Shipment Order Confirmation Date; (d) Carrier Equipment Failures beyond the scope of Provider's duty to maintain an adequate fleet under <Xref>Schedule 6-B § 4</Xref>; or (e) any other event specified in <Xref>Schedule 7-A (Exclusion Event Register)</Xref>, as updated from time to time in accordance with § 5.4.2, it being agreed that the Buyer shall have the right to object to any proposed addition to the Exclusion Event Register within ten (10) Business Days of receiving notice thereof, failing which the addition shall be deemed accepted.</span>
          </p>
        </ArticleBlock>

        {/* Article III */}
        <ArticleBlock id="art3" num="III" title="Penalty and Liquidated Damages Framework">
          <div className="sla-doc-warning-banner">
            <AlertTriangle size={14}/>
            <span>This Article contains cascading, multi-tier, and mutually conditional penalty provisions. Independent legal advice is strongly recommended before executing or waiving rights hereunder.</span>
          </div>
          <p className="sla-doc-clause">
            <span className="sla-doc-clause-num">3.1</span>
            <span><strong>Primary Penalty Schedule.</strong> Subject to §§ 3.1.1 through 3.1.5 (Grace Period, Minimum Threshold, Penalty Computation, Cap Application, and Set-Off respectively), § 3.2 (Cascading Multiplier Matrix), § 3.3 (Aggregate Cap), and § 4.1 (Force Majeure), and expressly without prejudice to the Buyer's right to pursue general damages under Clause 3.4 in the event the Aggregate Cap is reached and the Provider's conduct is found to constitute Gross Negligence or Wilful Misconduct (as each term is defined in <Xref>Annex II § 1.3</Xref>), the Provider shall pay to the Buyer Liquidated Damages computed as follows:</span>
          </p>
          <div className="sla-doc-penalty-matrix">
            <div className="sla-doc-pm-header">
              <div>OTIF Attainment Band</div>
              <div>Effective Delay (days)</div>
              <div>Base Penalty Rate</div>
              <div>Multiplier Tier</div>
              <div>Maximum per Event</div>
            </div>
            {[
              ['≥ 92.0% — &lt; 94.5%', '1 – 3 (after Grace)', '0.25% of Consignment Value / day', 'Tier A (×1.0)', 'USD 25,000'],
              ['≥ 88.0% — &lt; 92.0%', '4 – 7', '0.50% of Consignment Value / day', 'Tier B (×1.35)', 'USD 75,000'],
              ['≥ 82.0% — &lt; 88.0%', '8 – 14', '0.75% of Consignment Value / day', 'Tier C (×1.75)', 'USD 150,000'],
              ['&lt; 82.0%', '> 14 (or any Full Rejection Event)', '1.50% of Consignment Value / day', 'Tier D (×2.50 + OTIF Surcharge)', 'Per § 3.3.2(f)'],
            ].map((row, i) => (
              <div key={i} className="sla-doc-pm-row" style={i === 3 ? { background: 'rgba(220,38,38,0.06)', borderLeft: '3px solid #dc2626' } : {}}>
                {row.map((cell, j) => <div key={j} dangerouslySetInnerHTML={{__html: cell}} />)}
              </div>
            ))}
          </div>
          <div className="sla-doc-clause">
            <span className="sla-doc-clause-num">3.1.1</span>
            <div>
              <strong>Grace Period.</strong>
              <div className="sla-doc-subclause">
                <span className="sla-doc-clause-num">(a)</span>
                <span>A grace period of two (2) Business Days ("Standard Grace Period") shall apply to each Consignment unless: (i) the Consignment is designated as a Priority-1 Shipment under the Buyer's Criticality Classification (§ 2.1.3), in which case the grace period shall be reduced to twelve (12) hours; (ii) the Consignment forms part of a Just-in-Time Production Run (as notified by the Buyer at the time of booking and confirmed in the Shipment Order), in which case no grace period shall apply; or (iii) the cumulative Effective Delay Period in the immediately preceding Measurement Window exceeded 5.0% of total transit days, in which case the Standard Grace Period shall be reduced by one (1) Business Day for the duration of the following Measurement Window, subject to reinstatement upon written agreement of both Parties.</span>
              </div>
              <div className="sla-doc-subclause">
                <span className="sla-doc-clause-num">(b)</span>
                <span>The grace period under § 3.1.1(a) shall not apply to any Consignment that is subject to a Full Rejection Event, defined as any instance in which the consignee refuses acceptance of the entire Consignment due to delay, temperature exceedance, or documentation non-compliance, irrespective of whether such refusal is subsequently determined to have been commercially motivated rather than contractually justified, and irrespective of whether the Effective Delay Period would otherwise have fallen within the Standard Grace Period.</span>
              </div>
            </div>
          </div>
          <div className="sla-doc-clause">
            <span className="sla-doc-clause-num">3.2</span>
            <div>
              <strong>Cascading Multiplier Matrix.</strong> The Base Penalty Rate determined under § 3.1 shall be multiplied sequentially (not cumulatively) by each of the following factors, in the order listed, to produce the Final Penalty Amount:
              <div className="sla-doc-subclause">
                <span className="sla-doc-clause-num">3.2.1</span>
                <span><strong>OTIF Tier Coefficient</strong> — as specified in Column F of <Xref>Schedule 3-B</Xref>, selected by reference to the Buyer's OTIF attainment band in the current Measurement Window. Where the attainment band boundary falls exactly on the Adjusted OTIF Rate (to two decimal places), the higher Coefficient shall apply.</span>
              </div>
              <div className="sla-doc-subclause">
                <span className="sla-doc-clause-num">3.2.2</span>
                <span><strong>Route Concentration Factor</strong> — equal to 1.0 + (R / 10), where R is the number of distinct affected lanes (Origin–Destination pairs as defined in <Xref>Schedule 2-D § 1</Xref>) on which OTIF fell below the applicable OTIF Threshold in the same Measurement Window, subject to a maximum of 2.5, except where the affected lanes collectively represent more than forty percent (40%) of the Buyer's Total Tendered Consignments by value, in which case the factor shall be 2.5 plus an additional 0.1 for each additional percentage point above 40%, subject to an absolute ceiling of 3.0, as further described in § 3.2.4(b).</span>
              </div>
              <div className="sla-doc-subclause">
                <span className="sla-doc-clause-num">3.2.3</span>
                <span><strong>Recurrence Surcharge</strong> — an additional multiplier of 1.25 shall apply if the Provider has been subject to a Tier C or Tier D penalty event (§ 3.1) on the same lane in any of the three (3) immediately preceding Measurement Windows, escalating to 1.50 upon the fourth and subsequent occurrences within any rolling 52-week period, it being agreed that a lane shall be deemed "the same" if the Port of Loading and the final Place of Delivery (as defined in the relevant Bill of Lading) are identical, notwithstanding any intermediate transhipment point or change of vessel.</span>
              </div>
            </div>
          </div>
          <p className="sla-doc-clause">
            <span className="sla-doc-clause-num">3.3</span>
            <span><strong>Aggregate Cap.</strong> Notwithstanding any other provision of this Agreement, the total aggregate liability of the Provider to the Buyer under this Article III for Liquidated Damages in any rolling twelve (12) calendar month period shall not exceed the lesser of: (a) fifteen percent (15%) of the total Contract Value (as defined in <Xref>Schedule 1-A § 3</Xref>) paid or payable in that twelve-month period; or (b) USD 2,000,000 (two million United States Dollars), in each case adjusted upward in proportion to any Exceptional Volume premium paid under § 2.4.2(c), provided always that this Cap shall not apply where the Provider's liability arises from Gross Negligence or Wilful Misconduct (§ 3.4), in which case the parties agree that the Cap shall be replaced by a limit equal to three times (3×) the annual Contract Value, subject to the further provisos in § 3.3.2(f) and the insurer notification requirements of <Xref>Schedule 9-B § 2.3</Xref>.</span>
          </p>
        </ArticleBlock>

        {/* Article IV */}
        <ArticleBlock id="art4" num="IV" title="Force Majeure and Excused Performance">
          <p className="sla-doc-clause">
            <span className="sla-doc-clause-num">4.1</span>
            <span><strong>Qualifying Force Majeure Events.</strong> For the purposes of this Agreement, a "Force Majeure Event" means any event or circumstance beyond the reasonable control of the affected Party that (i) could not have been reasonably foreseen at the date of execution of this Agreement or the relevant Shipment Order (whichever is later), (ii) could not have been avoided or overcome by the exercise of a standard of care no less than that of a Prudent Operator (as defined in <Xref>Annex II § 1.5</Xref>), and (iii) directly prevents or delays performance of the relevant obligation. Without limiting the foregoing, and without prejudice to the requirement that each specific event be separately notified and validated under § 4.2, Force Majeure Events include (but are not limited to): (a) acts of God, including cyclones, typhoons, tsunamis, earthquakes exceeding 5.5 on the Richter scale at the point of impact, volcanic eruptions, and flash floods resulting in road or port closure for a period exceeding forty-eight (48) consecutive hours; (b) war, armed conflict, invasion, hostilities (whether or not war is declared), insurrection, rebellion, revolution, military or usurped power, or any act of terrorism as designated by a recognised international authority; (c) strikes, lockouts, or labour disputes of a general or industry-wide nature (but expressly excluding disputes limited to the Provider's own workforce, which shall not constitute Force Majeure); (d) governmental, regulatory, or administrative action including sanctions, embargoes, export controls, port closures, quarantine orders, or any directive of a Port Authority or competent governmental body; (e) pandemic, epidemic, or widespread outbreak of infectious disease designated as a Public Health Emergency of International Concern ("PHEIC") by the World Health Organisation or equivalent, provided that endemic conditions that were known or reasonably foreseeable at the Commencement Date shall not qualify; (f) cyberattacks on critical national infrastructure directly affecting the Provider's operations, provided that internal IT security failures shall not qualify unless directly caused by such national infrastructure attack; and (g) any other event designated in writing by both Parties as a Force Majeure Event pursuant to § 4.1.1.</span>
          </p>
          <p className="sla-doc-clause">
            <span className="sla-doc-clause-num">4.2</span>
            <span><strong>Notification, Validation, and Cure.</strong> A Party seeking to invoke Force Majeure must: (a) notify the other Party in writing within twenty-four (24) hours of becoming aware of the Force Majeure Event (or, if earlier, within twenty-four (24) hours of the time at which a Prudent Operator would have become aware); (b) provide, within five (5) Business Days of such notice, reasonably detailed evidence of the Force Majeure Event and its causative link to the affected obligation; (c) use commercially reasonable efforts at all times to mitigate the impact of and overcome the Force Majeure Event, including but not limited to procuring alternative carriers, rerouting Consignments, or obtaining regulatory dispensations; and (d) provide weekly written updates to the other Party during the continuance of the Force Majeure Period. Failure to comply with (a) above shall not preclude invocation of Force Majeure in respect of events of which the affected Party genuinely could not have been aware within the prescribed period, provided that notice is given as soon as reasonably practicable thereafter, but any delay in notification shall entitle the non-affected Party to claim compensation for any incremental loss attributable solely to the notification delay, subject to § 3.3.</span>
          </p>
        </ArticleBlock>

        {/* Article V */}
        <ArticleBlock id="art5" num="V" title="Audit, Reporting and Governance">
          <p className="sla-doc-clause">
            <span className="sla-doc-clause-num">5.1</span>
            <span><strong>Monthly Performance Reports.</strong> Provider shall deliver to Buyer, by no later than the seventh (7th) Business Day following the end of each calendar month, a Performance Report in the format specified in <Xref>Schedule 5-C</Xref>, containing: (a) Adjusted OTIF Rate by lane; (b) breakdown of Exclusion Events invoked, with supporting evidence; (c) Cascading Penalty computation for the month, if applicable; (d) trend analysis against the three preceding Measurement Windows; and (e) a forward-looking risk assessment for the following Measurement Window, produced in accordance with the Risk Scoring Methodology in <Xref>Annex XI § 4</Xref>. Failure to deliver the Performance Report within the specified period shall not constitute a material breach unless such failure occurs in three (3) or more consecutive months, in which case the Buyer shall be entitled, in addition to all other remedies, to appoint an independent auditor at Provider's cost pursuant to § 5.2.</span>
          </p>
          <p className="sla-doc-clause">
            <span className="sla-doc-clause-num">5.2</span>
            <span><strong>Audit Rights.</strong> The Buyer (or its duly authorised representative, including a third-party auditor subject to execution of a non-disclosure agreement in the form set out in <Xref>Schedule 8-D</Xref>) shall have the right, upon not less than fifteen (15) Business Days' prior written notice, to audit the Provider's records, systems, and processes relevant to performance under this Agreement, not more than once per twelve (12) month period, except in the event of a material discrepancy identified in a Performance Report or a Tier D penalty event, in which case no limit on frequency shall apply, subject to reasonable operational constraints as agreed in the Audit Protocol in <Xref>Schedule 5-D</Xref>.</span>
          </p>
        </ArticleBlock>

        {/* Article VI */}
        <ArticleBlock id="art6" num="VI" title="Dispute Resolution and Governing Law">
          <p className="sla-doc-clause">
            <span className="sla-doc-clause-num">6.1</span>
            <span><strong>Escalation Ladder.</strong> In the event of any dispute, controversy, or claim arising out of or in connection with this Agreement, or the breach, termination, or invalidity thereof (each a "Dispute"), the Parties shall first attempt to resolve the Dispute through good-faith negotiations between their respective operational teams within ten (10) Business Days of written notice of the Dispute by either Party ("Tier 1"). If unresolved, the Dispute shall be escalated to the respective C-suite executives of each Party within a further ten (10) Business Days ("Tier 2"). If still unresolved after Tier 2 escalation, either Party may refer the Dispute to mediation under the ICC Mediation Rules ("Tier 3") before commencing arbitration, provided that either Party may bypass Tier 3 mediation in respect of any Dispute involving an undisputed sum exceeding USD 500,000 or any allegation of Gross Negligence or Wilful Misconduct.</span>
          </p>
          <p className="sla-doc-clause">
            <span className="sla-doc-clause-num">6.2</span>
            <span><strong>Arbitration.</strong> Any Dispute not resolved through the process in § 6.1 shall be finally settled by arbitration administered by the London Court of International Arbitration ("LCIA") in accordance with the LCIA Arbitration Rules in force at the date of commencement of the arbitration. The seat of arbitration shall be London, England. The tribunal shall consist of three (3) arbitrators, each with not less than fifteen (15) years' experience in international freight and logistics law; the Claimant and Respondent shall each nominate one arbitrator, and the third (presiding) arbitrator shall be appointed by the two party-nominated arbitrators within twenty (20) days of the confirmation of the second, failing which the LCIA Court shall make the appointment. The language of arbitration shall be English, and all evidence, submissions, and hearings shall be conducted in English, provided that either Party may submit primary source documents in Hindi or Mandarin Chinese with certified English translations at its own cost. The award shall be final and binding, and may be enforced in any court of competent jurisdiction pursuant to the New York Convention on the Recognition and Enforcement of Foreign Arbitral Awards 1958.</span>
          </p>
          <p className="sla-doc-clause">
            <span className="sla-doc-clause-num">6.3</span>
            <span><strong>Governing Law.</strong> This Agreement and any non-contractual obligations arising out of or in connection with it shall be governed by and construed in accordance with the laws of England and Wales, without giving effect to any choice of law or conflict of law rules that would cause the application of laws of any other jurisdiction, save that: (a) any mandatory provisions of Indian law applicable to operations conducted within the territory of India shall apply to the extent they cannot be excluded by contract; and (b) any customs, port, or regulatory matters shall be governed by the law of the relevant jurisdiction, as further specified in <Xref>Schedule 7-B (Jurisdictional Matrix)</Xref>.</span>
          </p>
        </ArticleBlock>

        {/* Article VII */}
        <ArticleBlock id="art7" num="VII" title="General Provisions">
          <p className="sla-doc-clause">
            <span className="sla-doc-clause-num">7.1</span>
            <span><strong>Entire Agreement.</strong> This Agreement, together with all Schedules, Annexures, and Side Letters executed on or after the Commencement Date (each of which is incorporated herein by reference), constitutes the entire agreement between the Parties with respect to its subject matter and supersedes all prior agreements, representations, warranties, negotiations, and understandings, whether written or oral, relating to the same subject matter, provided that no representation made in any pre-contractual disclosure document shall be deemed incorporated except where expressly identified in <Xref>Schedule 1-B (Representations Register)</Xref>.</span>
          </p>
          <p className="sla-doc-clause">
            <span className="sla-doc-clause-num">7.2</span>
            <span><strong>Amendments.</strong> No amendment, modification, or supplement to this Agreement shall be valid or binding unless made in writing and duly executed by an authorised signatory of each Party, provided that: (a) amendments to Schedules 2-D (Transit Time Matrix), 4-B (Measurement Methodology), and 7-A (Exclusion Event Register) may be effected by written notice from Provider accepted in writing by Buyer within the timeframes specified in those Schedules; and (b) amendments to the Penalty Schedule (§ 3.1) and Aggregate Cap (§ 3.3) shall require approval by the respective Boards of Directors of both Parties or their duly delegated committee, and shall only take effect from the commencement of the Measurement Window immediately following the date of the amendment.</span>
          </p>
          <p className="sla-doc-clause">
            <span className="sla-doc-clause-num">7.4</span>
            <span><strong>Termination for Convenience and Sustained Underperformance.</strong> Either Party may terminate this Agreement for convenience upon not less than ninety (90) days' prior written notice, subject to payment of the Early Termination Fee calculated under <Xref>Schedule 9-E § 3</Xref>. In addition, without prejudice to any other remedy, the Buyer may terminate this Agreement for cause if the Adjusted OTIF Rate falls below eighty-five percent (85.0%) in any two (2) consecutive Measurement Windows (each such event a "Sustained Underperformance Event"), provided that: (a) the Buyer has issued a formal Remediation Notice pursuant to § 5.3.3 within ten (10) Business Days of identifying the first Sustained Underperformance Event; (b) the Provider has not submitted and obtained Buyer's written acceptance of a Remediation Plan within fifteen (15) Business Days of such Remediation Notice; and (c) the second consecutive Measurement Window OTIF result has been independently verified through the audit mechanism in § 5.2. Upon termination under this clause, the Aggregate Cap in § 3.3 shall be disapplied and the Provider's liability shall revert to the general law, subject only to the gross negligence and wilful misconduct cap at three times Contract Value as set out in § 3.3.2(f).</span>
          </p>

          {/* Signature block */}
          <div className="sla-doc-signature-block">
            <div className="sla-doc-sig-col">
              <div className="sla-doc-sig-label">For and on behalf of</div>
              <div className="sla-doc-sig-entity">Fiscalogix Freight Solutions Pvt. Ltd.</div>
              <div className="sla-doc-sig-line" />
              <div className="sla-doc-sig-meta">Authorised Signatory | Name: ___________________</div>
              <div className="sla-doc-sig-meta">Designation: ___________________</div>
              <div className="sla-doc-sig-meta">Date: ___________________</div>
            </div>
            <div className="sla-doc-sig-col">
              <div className="sla-doc-sig-label">For and on behalf of</div>
              <div className="sla-doc-sig-entity">[Buyer Entity Name]</div>
              <div className="sla-doc-sig-line" />
              <div className="sla-doc-sig-meta">Authorised Signatory | Name: ___________________</div>
              <div className="sla-doc-sig-meta">Designation: ___________________</div>
              <div className="sla-doc-sig-meta">Date: ___________________</div>
            </div>
          </div>
          <p className="sla-doc-footer-note">This document is subject to Schedule 1-A through Schedule 9-F and Annexures I–XIV, each of which forms an integral part of this Agreement. In the event of any conflict between this main body and any Schedule or Annexure, the conflict resolution mechanism in § 1.2(e) shall apply. For full text of all Schedules and Annexures, refer to the Executed Contract Bundle maintained by both Parties' legal departments.</p>
        </ArticleBlock>

      </div>
    </div>
  );
};

// ── Main page ─────────────────────────────────────────────────────────────────

export const SLAPage: React.FC = () => {
  const [tab, setTab] = useState<'analyze' | 'negotiate' | 'contract' | 'csv'>('analyze');

  // Analyze state
  const fileRef         = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging]         = useState(false);
  const [loading, setLoading]           = useState(false);
  const [error, setError]               = useState<string | null>(null);
  const [result, setResult]             = useState<SLAAnalysisResult | null>(null);

  // Shipment context form
  const [orderValue, setOrderValue]     = useState('');
  const [contractType, setContractType] = useState('standard');
  const [customerTier, setCustomerTier] = useState('standard');
  const [delayDays, setDelayDays]       = useState('');
  const [otifActual, setOtifActual]     = useState('');
  const [useLlm, setUseLlm]             = useState(false);
  const [showAllClauses, setShowAllClauses] = useState(false);

  // CSV Findings state
  const csvFileRef                              = useRef<HTMLInputElement>(null);
  const [csvFile, setCsvFile]                   = useState<File | null>(null);
  const [csvDragging, setCsvDragging]           = useState(false);
  const [csvLoading, setCsvLoading]             = useState(false);
  const [csvError, setCsvError]                 = useState<string | null>(null);
  const [csvResult, setCsvResult]               = useState<CsvFindingsResult | null>(null);
  const [csvOtifThreshold, setCsvOtifThreshold] = useState('94.5');
  const [csvContractType, setCsvContractType]   = useState('standard');
  const [csvCustomerTier, setCsvCustomerTier]   = useState('standard');
  const [csvDefaultValue, setCsvDefaultValue]   = useState('');
  const [csvPenaltyRate, setCsvPenaltyRate]     = useState('');
  const [csvShowAll, setCsvShowAll]             = useState(false);

  // Negotiate state
  const [supplierId, setSupplierId]         = useState('');
  const [currentTerms, setCurrentTerms]     = useState('30');
  const [targetTerms, setTargetTerms]       = useState('60');
  const [waccCost, setWaccCost]             = useState('');
  const [negLoading, setNegLoading]         = useState(false);
  const [negError, setNegError]             = useState<string | null>(null);
  const [negResult, setNegResult]           = useState<NegotiateResult | null>(null);

  // ── Analyze handlers ────────────────────────────────────────────────────────

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped?.type === 'application/pdf') { setFile(dropped); setResult(null); setError(null); }
    else setError('Only PDF files are accepted.');
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setFile(f); setResult(null); setError(null);
  };

  const handleAnalyze = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const params = new URLSearchParams({
        use_llm:              String(useLlm),
        order_value:          orderValue || '0',
        contract_type:        contractType,
        customer_tier:        customerTier,
        predicted_delay_days: delayDays || '0',
        otif_threshold_pct:   '95',
        ...(otifActual ? { otif_actual_pct: otifActual } : {}),
      });

      const fd = new FormData();
      fd.append('file', file);

      const resp = await fetch(`${API_BASE_URL}/sla/analyze?${params}`, {
        method:  'POST',
        headers: authHeader() as Record<string, string>,
        body:    fd,
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || `Analysis failed (${resp.status})`);
      }

      setResult(await resp.json());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  // ── CSV Findings handler ────────────────────────────────────────────────────

  const handleCsvDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setCsvDragging(false);
    const f = e.dataTransfer.files[0];
    if (f?.name.endsWith('.csv') || f?.type === 'text/csv') { setCsvFile(f); setCsvResult(null); setCsvError(null); }
    else setCsvError('Only CSV files are accepted.');
  };

  const handleCsvAnalyze = async () => {
    if (!csvFile) return;
    setCsvLoading(true); setCsvError(null); setCsvResult(null);
    try {
      const params = new URLSearchParams({
        otif_threshold:      csvOtifThreshold || '94.5',
        contract_type:       csvContractType,
        customer_tier:       csvCustomerTier,
        default_order_value: csvDefaultValue || '0',
        ...(csvPenaltyRate ? { penalty_rate: csvPenaltyRate } : {}),
      });
      const fd = new FormData();
      fd.append('file', csvFile);
      const resp = await fetch(`${API_BASE_URL}/sla/analyze-csv?${params}`, {
        method: 'POST',
        headers: authHeader() as Record<string, string>,
        body: fd,
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || `CSV analysis failed (${resp.status})`);
      }
      setCsvResult(await resp.json());
    } catch (e: any) {
      setCsvError(e.message);
    } finally {
      setCsvLoading(false);
    }
  };

  // ── Negotiate handler ───────────────────────────────────────────────────────

  const handleNegotiate = async () => {
    if (!supplierId) { setNegError('Supplier ID is required.'); return; }
    setNegLoading(true); setNegError(null); setNegResult(null);

    try {
      const contractClauses = result?.extraction.bottleneck_clauses ?? undefined;
      const resp = await fetch(`${API_BASE_URL}/sla/negotiate`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json', ...(authHeader() as Record<string, string>) },
        body: JSON.stringify({
          supplier_data: {
            supplier_id:                     supplierId,
            historical_delay_variance_pct:   parseFloat(delayVariance) || undefined,
            current_payment_terms:           parseInt(currentTerms) || 30,
            target_payment_terms:            parseInt(targetTerms) || 60,
            wacc_carrying_cost_usd:          parseFloat(waccCost) || 0,
          },
          contract_clauses: contractClauses,
          tenant_id: 'default_tenant',
        }),
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || `Negotiation failed (${resp.status})`);
      }
      setNegResult(await resp.json());
    } catch (e: any) {
      setNegError(e.message);
    } finally {
      setNegLoading(false);
    }
  };

  // ── Render ──────────────────────────────────────────────────────────────────

  const scoreColor = result ? riskScoreColor(result.risk_score) : '#94a3b8';
  const displayClauses = result
    ? (showAllClauses ? result.extraction.clauses : result.extraction.clauses.slice(0, 8))
    : [];

  return (
    <div className="sla-page">

      {/* Header */}
      <header className="sla-header glass-panel">
        <div className="sla-header-left">
          <Shield size={28} className="sla-header-icon" />
          <div>
            <h1 className="page-title">SLA Contract Analyser</h1>
            <p className="page-subtitle">
              Upload a contract PDF — extract penalty clauses, bottleneck triggers, and compute financial exposure in seconds.
            </p>
          </div>
        </div>
        <div className="sla-pipeline-badges">
          {['Parse', 'Extract', 'Calculate', 'Score', 'Output'].map((s, i) => (
            <React.Fragment key={s}>
              <span className="sla-pipeline-step">{s}</span>
              {i < 4 && <span className="sla-pipeline-arrow">→</span>}
            </React.Fragment>
          ))}
        </div>
      </header>

      {/* Tabs */}
      <div className="sla-tabs">
        <button className={`sla-tab-btn ${tab === 'analyze' ? 'active' : ''}`} onClick={() => setTab('analyze')}>
          <FileText size={16} /> Analyze Contract
        </button>
        <button className={`sla-tab-btn ${tab === 'negotiate' ? 'active' : ''}`} onClick={() => setTab('negotiate')}>
          <Zap size={16} /> Negotiation Brief
          {result && <span className="sla-tab-badge">Ready</span>}
        </button>
        <button className={`sla-tab-btn ${tab === 'contract' ? 'active' : ''}`} onClick={() => setTab('contract')}>
          <BookOpen size={16} /> Live Contract
        </button>
        <button className={`sla-tab-btn ${tab === 'csv' ? 'active' : ''}`} onClick={() => setTab('csv')}>
          <Table2 size={16} /> CSV Findings
          {csvResult && <span className="sla-tab-badge">{csvResult.total_shipments}</span>}
        </button>
      </div>

      {/* ── Analyze Tab ── */}
      {tab === 'analyze' && (
        <div className={`sla-analyze-layout ${result ? 'has-result' : ''}`}>

          {/* Upload + context panel */}
          <div className="sla-upload-panel glass-panel">
            <h3 className="sla-panel-title">Contract Upload</h3>

            {/* Drop zone */}
            <div
              className={`sla-dropzone ${dragging ? 'dragging' : ''} ${file ? 'has-file' : ''}`}
              onDragOver={e => { e.preventDefault(); setDragging(true); }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
              onClick={() => fileRef.current?.click()}
            >
              <input ref={fileRef} type="file" accept=".pdf" hidden onChange={handleFileChange} />
              {file ? (
                <>
                  <CheckCircle size={28} color="#059669" />
                  <div className="sla-dropzone-filename">{file.name}</div>
                  <div className="sla-dropzone-size">{(file.size / 1024).toFixed(1)} KB — click to replace</div>
                </>
              ) : (
                <>
                  <Upload size={28} />
                  <div className="sla-dropzone-label">Drop contract PDF here</div>
                  <div className="sla-dropzone-sub">or click to browse · max 20 MB</div>
                </>
              )}
            </div>

            {/* Shipment context */}
            <div className="sla-form-section">
              <div className="sla-form-label">Shipment Context <span className="sla-form-hint">(optional — required for penalty amount)</span></div>

              <div className="sla-form-row">
                <div className="sla-field">
                  <label>Order Value (USD)</label>
                  <input type="number" placeholder="e.g. 250000" value={orderValue}
                    onChange={e => setOrderValue(e.target.value)} className="sla-input" />
                </div>
                <div className="sla-field">
                  <label>Delay Days</label>
                  <input type="number" placeholder="e.g. 5" value={delayDays}
                    onChange={e => setDelayDays(e.target.value)} className="sla-input" />
                </div>
              </div>

              <div className="sla-form-row">
                <div className="sla-field">
                  <label>Contract Type</label>
                  <select value={contractType} onChange={e => setContractType(e.target.value)} className="sla-input">
                    <option value="standard">Standard</option>
                    <option value="strict">Strict</option>
                    <option value="lenient">Lenient</option>
                    <option value="full_rejection">Full Rejection (Walmart)</option>
                  </select>
                </div>
                <div className="sla-field">
                  <label>Customer Tier</label>
                  <select value={customerTier} onChange={e => setCustomerTier(e.target.value)} className="sla-input">
                    <option value="enterprise">Enterprise</option>
                    <option value="strategic">Strategic</option>
                    <option value="growth">Growth</option>
                    <option value="standard">Standard</option>
                    <option value="spot">Spot</option>
                    <option value="trial">Trial</option>
                  </select>
                </div>
              </div>

              <div className="sla-form-row">
                <div className="sla-field">
                  <label>Actual OTIF % (if known)</label>
                  <input type="number" placeholder="e.g. 88" value={otifActual}
                    onChange={e => setOtifActual(e.target.value)} className="sla-input" />
                </div>
                <div className="sla-field sla-field-toggle">
                  <label>
                    <input type="checkbox" checked={useLlm} onChange={e => setUseLlm(e.target.checked)} />
                    Force LLM extraction
                  </label>
                  <span className="sla-form-hint">Slower but captures complex cross-referenced clauses</span>
                </div>
              </div>
            </div>

            {error && (
              <div className="sla-error">
                <AlertTriangle size={14} /> {error}
              </div>
            )}

            <button
              className="sla-analyze-btn"
              onClick={handleAnalyze}
              disabled={!file || loading}
            >
              {loading ? (
                <><span className="sla-spinner" /> Analysing…</>
              ) : (
                <><FileText size={16} /> Analyse Contract</>
              )}
            </button>
          </div>

          {/* Results panel */}
          {result && (
            <div className="sla-results-panel">

              {/* Risk score banner */}
              <div className="sla-risk-banner glass-panel" style={{ borderLeft: `5px solid ${scoreColor}` }}>
                <div className="sla-risk-score-block">
                  <div className="sla-risk-score-num" style={{ color: scoreColor }}>{result.risk_score}</div>
                  <div className="sla-risk-score-label">/ 100 Risk Score</div>
                </div>
                <div className="sla-risk-dist">
                  {(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'] as const).map(s => (
                    <div key={s} className="sla-risk-dist-item">
                      <div className="sla-risk-dist-num" style={{ color: severityColor(s) }}>
                        {result.severity_distribution[s] ?? 0}
                      </div>
                      <div className="sla-risk-dist-label">{s}</div>
                    </div>
                  ))}
                </div>
                <div className="sla-risk-meta">
                  <div className="sla-risk-meta-item">
                    <span>Confidence</span><strong>{result.extraction.overall_confidence}</strong>
                  </div>
                  <div className="sla-risk-meta-item">
                    <span>Total Clauses</span><strong>{result.extraction.total_clauses}</strong>
                  </div>
                  <div className="sla-risk-meta-item">
                    <span>Force Majeure</span>
                    <strong style={{ color: result.extraction.force_majeure_applies ? '#059669' : '#94a3b8' }}>
                      {result.extraction.force_majeure_applies ? 'Present' : 'Absent'}
                    </strong>
                  </div>
                  {result.extraction.llm_assisted && (
                    <div className="sla-risk-meta-item">
                      <span>Extraction</span><strong style={{ color: '#6366f1' }}>LLM-assisted</strong>
                    </div>
                  )}
                </div>
              </div>

              {/* Penalty card */}
              {result.penalty && (
                <div className="sla-penalty-card glass-panel">
                  <div className="sla-penalty-title">
                    <TrendingDown size={16} />
                    Computed Financial Penalty
                    <span className="sla-penalty-source">{result.penalty.penalty_source === 'nlp_contract' ? 'from contract' : 'tier heuristic'}</span>
                  </div>
                  <div className="sla-penalty-amount" style={{ color: severityColor(result.penalty.breach_level.toUpperCase()) }}>
                    ${result.penalty.financial_penalty.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </div>
                  <div className="sla-penalty-meta-row">
                    <div className="sla-penalty-meta-item">
                      <span>Effective Delay</span><strong>{result.penalty.effective_delay}d</strong>
                    </div>
                    <div className="sla-penalty-meta-item">
                      <span>Grace Applied</span><strong>{result.penalty.grace_days_applied}d</strong>
                    </div>
                    <div className="sla-penalty-meta-item">
                      <span>OTIF Breach</span>
                      <strong style={{ color: severityColor(result.penalty.otif_breach_level.toUpperCase()) }}>
                        {result.penalty.otif_breach_level} ({result.penalty.otif_multiplier}×)
                      </strong>
                    </div>
                    <div className="sla-penalty-meta-item">
                      <span>Severity</span>
                      <strong style={{ color: severityColor(result.penalty.breach_level.toUpperCase()) }}>
                        {result.penalty.breach_level.toUpperCase()}
                      </strong>
                    </div>
                  </div>
                </div>
              )}

              {/* Top bottlenecks */}
              {result.top_bottlenecks.length > 0 && (
                <div className="sla-section glass-panel">
                  <h4 className="sla-section-title"><AlertTriangle size={15} /> Top Bottleneck Clauses</h4>
                  <div className="sla-bottleneck-table">
                    <div className="sla-bottleneck-thead">
                      <div>Clause Type</div>
                      <div>Severity</div>
                      <div>Value</div>
                      <div>Risk Reason</div>
                    </div>
                    {result.top_bottlenecks.map((c, i) => (
                      <div key={i} className="sla-bottleneck-row">
                        <div className="sla-bottleneck-type">{labelClauseType(c.clause_type)}</div>
                        <div><SeverityBadge sev={c.bottleneck_severity} /></div>
                        <div className="sla-bottleneck-value">{fmt(c.value, c.unit) || '—'}</div>
                        <div className="sla-bottleneck-reason">{c.bottleneck_reason}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* All clauses */}
              {result.extraction.clauses.length > 0 && (
                <div className="sla-section glass-panel">
                  <h4 className="sla-section-title"><FileText size={15} /> All Extracted Clauses ({result.extraction.total_clauses})</h4>
                  <div className="sla-clauses-list">
                    {displayClauses.map((c, i) => <ClauseRow key={i} clause={c} />)}
                  </div>
                  {result.extraction.clauses.length > 8 && (
                    <button className="sla-show-more-btn" onClick={() => setShowAllClauses(v => !v)}>
                      {showAllClauses ? <><ChevronUp size={14} /> Show less</> : <><ChevronDown size={14} /> Show all {result.extraction.clauses.length} clauses</>}
                    </button>
                  )}
                </div>
              )}

              {/* Processing pipeline */}
              <div className="sla-pipeline-trace">
                {result.processing_pipeline.map((s, i) => (
                  <React.Fragment key={s}>
                    <span className="sla-trace-step"><CheckCircle size={11} /> {s}</span>
                    {i < result.processing_pipeline.length - 1 && <span className="sla-trace-arrow">›</span>}
                  </React.Fragment>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── CSV Findings Tab ── */}
      {tab === 'csv' && (
        <div className={`sla-analyze-layout ${csvResult ? 'has-result' : ''}`}>

          {/* Upload + config panel */}
          <div className="sla-upload-panel glass-panel">
            <h3 className="sla-panel-title">Shipment CSV Upload</h3>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 14 }}>
              Upload a shipment data CSV. Columns are auto-detected by name — supported headers include{' '}
              <code>delay_days</code>, <code>order_value</code>, <code>otif_actual</code>, <code>carrier</code>, <code>route</code>, and more.
            </p>

            {/* Drop zone */}
            <div
              className={`sla-dropzone ${csvDragging ? 'dragging' : ''} ${csvFile ? 'has-file' : ''}`}
              onDragOver={e => { e.preventDefault(); setCsvDragging(true); }}
              onDragLeave={() => setCsvDragging(false)}
              onDrop={handleCsvDrop}
              onClick={() => csvFileRef.current?.click()}
            >
              <input ref={csvFileRef} type="file" accept=".csv,text/csv" hidden
                onChange={e => { const f = e.target.files?.[0]; if (f) { setCsvFile(f); setCsvResult(null); setCsvError(null); } }} />
              {csvFile ? (
                <>
                  <CheckCircle size={28} color="#059669" />
                  <div className="sla-dropzone-filename">{csvFile.name}</div>
                  <div className="sla-dropzone-size">{(csvFile.size / 1024).toFixed(1)} KB — click to replace</div>
                </>
              ) : (
                <>
                  <Upload size={28} />
                  <div className="sla-dropzone-label">Drop shipment CSV here</div>
                  <div className="sla-dropzone-sub">or click to browse · UTF-8 or Latin-1</div>
                </>
              )}
            </div>

            {/* SLA parameters */}
            <div className="sla-form-section">
              <div className="sla-form-label">SLA Parameters <span className="sla-form-hint">(applied to rows missing those columns)</span></div>
              <div className="sla-form-row">
                <div className="sla-field">
                  <label>OTIF Threshold (%)</label>
                  <input type="number" placeholder="94.5" value={csvOtifThreshold}
                    onChange={e => setCsvOtifThreshold(e.target.value)} className="sla-input" />
                </div>
                <div className="sla-field">
                  <label>Default Order Value (USD)</label>
                  <input type="number" placeholder="e.g. 100000" value={csvDefaultValue}
                    onChange={e => setCsvDefaultValue(e.target.value)} className="sla-input" />
                </div>
              </div>
              <div className="sla-form-row">
                <div className="sla-field">
                  <label>Contract Type</label>
                  <select value={csvContractType} onChange={e => setCsvContractType(e.target.value)} className="sla-input">
                    <option value="standard">Standard</option>
                    <option value="strict">Strict</option>
                    <option value="lenient">Lenient</option>
                    <option value="full_rejection">Full Rejection</option>
                  </select>
                </div>
                <div className="sla-field">
                  <label>Customer Tier</label>
                  <select value={csvCustomerTier} onChange={e => setCsvCustomerTier(e.target.value)} className="sla-input">
                    <option value="enterprise">Enterprise</option>
                    <option value="strategic">Strategic</option>
                    <option value="growth">Growth</option>
                    <option value="standard">Standard</option>
                    <option value="spot">Spot</option>
                  </select>
                </div>
              </div>
              <div className="sla-form-row">
                <div className="sla-field">
                  <label>Override Penalty Rate (fraction/day)</label>
                  <input type="number" step="0.001" placeholder="e.g. 0.005 = 0.5%/day"
                    value={csvPenaltyRate} onChange={e => setCsvPenaltyRate(e.target.value)} className="sla-input" />
                </div>
              </div>
            </div>

            {csvError && <div className="sla-error"><AlertTriangle size={14} /> {csvError}</div>}

            <button className="sla-analyze-btn" onClick={handleCsvAnalyze} disabled={!csvFile || csvLoading}>
              {csvLoading
                ? <><span className="sla-spinner" /> Interpreting…</>
                : <><BarChart2 size={16} /> Interpret CSV</>}
            </button>
          </div>

          {/* Results */}
          {csvResult && (
            <div className="sla-results-panel">

              {/* Summary KPIs */}
              <div className="sla-csv-kpi-grid glass-panel">
                {[
                  { label: 'Total Shipments', val: csvResult.total_shipments, color: '#94a3b8' },
                  { label: 'On-Time', val: csvResult.on_time_count, color: '#059669' },
                  { label: 'In Breach', val: csvResult.breach_count, color: csvResult.breach_count > 0 ? '#f97316' : '#94a3b8' },
                  { label: 'Avg OTIF', val: csvResult.avg_otif_pct != null ? `${csvResult.avg_otif_pct}%` : '—', color: csvResult.avg_otif_pct != null && csvResult.avg_otif_pct < csvResult.otif_threshold_used ? '#dc2626' : '#059669' },
                  { label: 'Avg Delay', val: `${csvResult.avg_delay_days}d`, color: csvResult.avg_delay_days > 3 ? '#f97316' : '#94a3b8' },
                  { label: 'Total Penalty', val: `$${csvResult.total_penalty_usd.toLocaleString(undefined, { maximumFractionDigits: 0 })}`, color: csvResult.total_penalty_usd > 0 ? '#dc2626' : '#059669' },
                ].map(kpi => (
                  <div key={kpi.label} className="sla-csv-kpi">
                    <div className="sla-csv-kpi-val" style={{ color: kpi.color }}>{kpi.val}</div>
                    <div className="sla-csv-kpi-label">{kpi.label}</div>
                  </div>
                ))}
              </div>

              {/* Breach distribution */}
              <div className="sla-section glass-panel">
                <h4 className="sla-section-title"><BarChart2 size={15} /> Breach Distribution</h4>
                <div className="sla-csv-breach-row">
                  {(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'NONE'] as const).map(s => {
                    const cnt = csvResult.breach_distribution[s] ?? 0;
                    const pct = csvResult.total_shipments ? (cnt / csvResult.total_shipments) * 100 : 0;
                    return (
                      <div key={s} className="sla-csv-breach-col">
                        <div className="sla-csv-breach-bar">
                          <div className="sla-csv-breach-fill" style={{ height: `${pct}%`, background: severityColor(s) }} />
                        </div>
                        <div className="sla-csv-breach-cnt" style={{ color: severityColor(s) }}>{cnt}</div>
                        <div className="sla-csv-breach-lbl">{s}</div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Insights */}
              {csvResult.insights.length > 0 && (
                <div className="sla-section glass-panel">
                  <h4 className="sla-section-title"><AlertTriangle size={15} /> Key Findings</h4>
                  <div className="sla-csv-insights">
                    {csvResult.insights.map((ins, i) => (
                      <div key={i} className="sla-csv-insight-row" style={{ borderLeft: `3px solid ${severityColor(ins.severity)}` }}>
                        <SeverityBadge sev={ins.severity} />
                        <span className="sla-csv-insight-msg">{ins.message}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Detected columns */}
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 4 }}>
                <span style={{ fontSize: 11, opacity: 0.5 }}>Detected columns:</span>
                {csvResult.detected_columns.map(c => (
                  <span key={c} style={{ fontSize: 11, background: 'rgba(99,102,241,0.12)', color: '#818cf8', padding: '2px 7px', borderRadius: 4 }}>{c}</span>
                ))}
              </div>

              {/* Per-shipment table */}
              <div className="sla-section glass-panel">
                <h4 className="sla-section-title"><Table2 size={15} /> Per-Shipment Findings ({csvResult.total_shipments})</h4>
                <div style={{ overflowX: 'auto' }}>
                  <table className="sla-csv-table">
                    <thead>
                      <tr>
                        {['Shipment ID', 'Delay (d)', 'OTIF %', 'In-Full %', 'Breach', 'Penalty (USD)', 'Carrier', 'Route'].map(h => (
                          <th key={h}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {(csvShowAll ? csvResult.shipments : csvResult.shipments.slice(0, 20)).map((s, i) => (
                        <tr key={i} style={{ background: s.breach_level === 'CRITICAL' ? 'rgba(220,38,38,0.05)' : s.breach_level === 'HIGH' ? 'rgba(249,115,22,0.04)' : undefined }}>
                          <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{s.shipment_id}</td>
                          <td style={{ color: s.delay_days > 0 ? severityColor(s.breach_level) : 'inherit' }}>{s.delay_days}</td>
                          <td style={{ color: s.otif_actual != null && s.otif_actual < csvResult.otif_threshold_used ? '#f97316' : 'inherit' }}>
                            {s.otif_actual != null ? `${s.otif_actual}%` : '—'}
                          </td>
                          <td>{s.in_full_pct != null ? `${s.in_full_pct}%` : '—'}</td>
                          <td><SeverityBadge sev={s.breach_level} /></td>
                          <td style={{ color: s.penalty_amount > 0 ? '#f97316' : 'inherit', fontWeight: s.penalty_amount > 0 ? 600 : 400 }}>
                            {s.penalty_amount > 0 ? `$${s.penalty_amount.toLocaleString(undefined, { maximumFractionDigits: 0 })}` : '—'}
                          </td>
                          <td style={{ fontSize: 12 }}>{s.carrier || '—'}</td>
                          <td style={{ fontSize: 12 }}>{s.route || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {csvResult.shipments.length > 20 && (
                  <button className="sla-show-more-btn" onClick={() => setCsvShowAll(v => !v)}>
                    {csvShowAll ? <><ChevronUp size={14} /> Show less</> : <><ChevronDown size={14} /> Show all {csvResult.shipments.length} rows</>}
                  </button>
                )}
              </div>

            </div>
          )}
        </div>
      )}

      {/* ── Contract Tab ── */}
      {tab === 'contract' && <ContractViewer />}

      {/* ── Negotiate Tab ── */}
      {tab === 'negotiate' && (
        <div className="sla-negotiate-layout">
          <div className="sla-upload-panel glass-panel">
            <h3 className="sla-panel-title">Supplier Data</h3>
            {result && (
              <div className="sla-neg-prefill-notice">
                <CheckCircle size={13} color="#059669" />
                {result.extraction.bottleneck_clauses.length} bottleneck clauses from your analysis will be included automatically.
              </div>
            )}

            <div className="sla-form-section">
              <div className="sla-form-row">
                <div className="sla-field">
                  <label>Supplier ID *</label>
                  <input value={supplierId} onChange={e => setSupplierId(e.target.value)}
                    placeholder="e.g. SUPPLIER-001" className="sla-input" />
                </div>
                <div className="sla-field">
                  <label>Delay Variance (%)</label>
                  <input type="number" value={delayVariance} onChange={e => setDelayVariance(e.target.value)}
                    placeholder="e.g. 14.5" className="sla-input" />
                </div>
              </div>
              <div className="sla-form-row">
                <div className="sla-field">
                  <label>Current Payment Terms (days)</label>
                  <input type="number" value={currentTerms} onChange={e => setCurrentTerms(e.target.value)} className="sla-input" />
                </div>
                <div className="sla-field">
                  <label>Target Payment Terms (days)</label>
                  <input type="number" value={targetTerms} onChange={e => setTargetTerms(e.target.value)} className="sla-input" />
                </div>
              </div>
              <div className="sla-form-row">
                <div className="sla-field">
                  <label>WACC Carrying Cost (USD/year)</label>
                  <input type="number" value={waccCost} onChange={e => setWaccCost(e.target.value)}
                    placeholder="e.g. 48000" className="sla-input" />
                </div>
              </div>
            </div>

            {negError && <div className="sla-error"><AlertTriangle size={14} /> {negError}</div>}

            <button className="sla-analyze-btn" onClick={handleNegotiate} disabled={negLoading}>
              {negLoading ? <><span className="sla-spinner" /> Generating…</> : <><Zap size={16} /> Generate Strategy</>}
            </button>
          </div>

          {negResult && (
            <div className="sla-results-panel">
              <div className="sla-section glass-panel">
                <h4 className="sla-section-title"><Zap size={15} /> Negotiation Strategy — {negResult.supplier_id}</h4>
                <pre className="sla-strategy-text">{negResult.strategy}</pre>
              </div>

              {negResult.suggested_actions?.length > 0 && (
                <div className="sla-section glass-panel">
                  <h4 className="sla-section-title">Suggested Actions</h4>
                  <ul className="sla-actions-list">
                    {negResult.suggested_actions.map((a, i) => (
                      <li key={i}><CheckCircle size={13} color="#059669" /> {a}</li>
                    ))}
                  </ul>
                </div>
              )}

              {negResult.leverage_clauses?.length > 0 && (
                <div className="sla-section glass-panel">
                  <h4 className="sla-section-title"><AlertTriangle size={15} /> Leverage Clauses</h4>
                  {negResult.leverage_clauses.map((c, i) => <ClauseRow key={i} clause={c} />)}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
