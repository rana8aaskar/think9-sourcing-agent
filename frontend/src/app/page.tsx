"use client";

import { useEffect, useState, FormEvent } from "react";

// Types
type BundleOpportunity = {
  canonical_id: string;
  canonical_name: string;
  category: string;
  brands: string[];
  combined_monthly_qty: number;
  current_blended_price: number;
  best_vendor: string;
  best_price: number;
  unit_saving: number;
  monthly_saving: number;
  annual_saving: number;
  rationale: string;
};

type RiskFlag = {
  severity: string;
  canonical_id: string;
  canonical_name: string;
  risk_type: string;
  detail: string;
  recommended_action: string;
};

type ReportData = {
  meta: {
    extraction_mode: string;
    total_annual_savings: number;
    raw_items: number;
    normalized_quotes: number;
    unmatched: number;
    bundle_count: number;
    risk_count: number;
    high_risk_count: number;
  };
  bundles: BundleOpportunity[];
  risks: RiskFlag[];
};

type AnalyzeItem = {
  raw_description: string;
  unit_price: number;
  uom: string;
  normalized: boolean;
  canonical_name: string | null;
  category: string | null;
  match_confidence: number;
};

export default function Dashboard() {
  const [data, setData] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Analyze state
  const [analyzeText, setAnalyzeText] = useState("");
  const [analyzeType, setAnalyzeType] = useState("pdf");
  const [analyzeVendor, setAnalyzeVendor] = useState("Unknown");
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeResults, setAnalyzeResults] = useState<AnalyzeItem[] | null>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch(`${API_URL}/api/report`);
        if (!res.ok) {
          throw new Error(`Failed to fetch report (Status: ${res.status})`);
        }
        const json = await res.json();
        setData(json);
      } catch (err: any) {
        setError(err.message || "Failed to connect to backend");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [API_URL]);

  const handleAnalyze = async (e: FormEvent) => {
    e.preventDefault();
    if (!analyzeText.trim()) return;
    setAnalyzing(true);
    setAnalyzeResults(null);
    try {
      const res = await fetch(`${API_URL}/api/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: analyzeText,
          source_type: analyzeType,
          vendor: analyzeVendor,
        }),
      });
      if (!res.ok) throw new Error("Failed to analyze");
      const json = await res.json();
      setAnalyzeResults(json.items);
    } catch (err) {
      alert("Error analyzing document.");
    } finally {
      setAnalyzing(false);
    }
  };

  const formatRs = (num: number) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(num);
  };

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-base text-main">
        <p className="text-xl">Loading Sourcing Agent Report...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-screen items-center justify-center bg-base text-main">
        <div className="bg-card border-card border p-8 rounded-xl max-w-md text-center">
          <h2 className="text-red text-xl font-bold mb-4">Connection Error</h2>
          <p className="text-muted mb-4">{error}</p>
          <p className="text-sm text-muted">API URL: {API_URL}</p>
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <main className="min-h-screen bg-base text-main p-6 lg:p-12">
      <div className="max-w-6xl mx-auto space-y-8">
        
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold mb-2">Think9 Sourcing Intelligence</h1>
          <p className="text-muted">
            Cross-Portfolio Consolidation & Risk Analysis
            <span className="ml-4 px-2 py-1 bg-card rounded-full text-xs border border-card">
              {data.meta.extraction_mode}
            </span>
          </p>
        </div>

        {/* KPIs */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-card border border-card rounded-xl p-5 flex flex-col justify-between">
            <span className="text-muted text-sm uppercase tracking-wider">Annual Savings</span>
            <span className="text-mint text-3xl font-bold mt-2">{formatRs(data.meta.total_annual_savings)}</span>
          </div>
          <div className="bg-card border border-card rounded-xl p-5 flex flex-col justify-between">
            <span className="text-muted text-sm uppercase tracking-wider">Bundles</span>
            <span className="text-ice text-3xl font-bold mt-2">{data.meta.bundle_count} <span className="text-lg text-muted font-normal ml-1">Opps</span></span>
          </div>
          <div className="bg-card border border-card rounded-xl p-5 flex flex-col justify-between">
            <span className="text-muted text-sm uppercase tracking-wider">Risk Flags</span>
            <span className="text-amber text-3xl font-bold mt-2">{data.meta.risk_count} <span className="text-lg text-muted font-normal ml-1">Total</span></span>
          </div>
          <div className="bg-card border border-card rounded-xl p-5 flex flex-col justify-between">
            <span className="text-muted text-sm uppercase tracking-wider">High Severity</span>
            <span className="text-red text-3xl font-bold mt-2">{data.meta.high_risk_count} <span className="text-lg text-muted font-normal ml-1">Action Req.</span></span>
          </div>
        </div>

        {/* Bundles Table */}
        <div className="bg-card border border-card rounded-xl overflow-hidden">
          <div className="p-5 border-b border-card">
            <h2 className="text-xl font-semibold">Volume-Bundling Opportunities</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-[#151c28] text-muted text-sm uppercase tracking-wide">
                  <th className="p-4 border-b border-card font-medium">Item & Rationale</th>
                  <th className="p-4 border-b border-card font-medium">Brands</th>
                  <th className="p-4 border-b border-card font-medium">Qty/mo</th>
                  <th className="p-4 border-b border-card font-medium">Best Vendor</th>
                  <th className="p-4 border-b border-card font-medium text-right">Annual Saving</th>
                </tr>
              </thead>
              <tbody>
                {data.bundles.map((b, i) => (
                  <tr key={i} className="hover:bg-[#1a2535] transition-colors">
                    <td className="p-4 border-b border-card align-top">
                      <div className="font-semibold text-main">{b.canonical_name}</div>
                      <div className="text-xs text-muted mt-1 leading-relaxed max-w-md">{b.rationale}</div>
                    </td>
                    <td className="p-4 border-b border-card align-top text-sm">{b.brands.join(", ")}</td>
                    <td className="p-4 border-b border-card align-top text-sm">{b.combined_monthly_qty.toLocaleString()}</td>
                    <td className="p-4 border-b border-card align-top text-sm">
                      <div className="font-medium">{b.best_vendor}</div>
                      <div className="text-xs text-muted mt-1">₹{b.best_price.toFixed(2)}/unit</div>
                    </td>
                    <td className="p-4 border-b border-card align-top text-right font-bold text-mint">
                      {formatRs(b.annual_saving)}
                    </td>
                  </tr>
                ))}
                {data.bundles.length === 0 && (
                  <tr>
                    <td colSpan={5} className="p-8 text-center text-muted">No bundling opportunities found.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Risk Register Table */}
        <div className="bg-card border border-card rounded-xl overflow-hidden">
          <div className="p-5 border-b border-card">
            <h2 className="text-xl font-semibold">Supply-Risk Register</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-[#151c28] text-muted text-sm uppercase tracking-wide">
                  <th className="p-4 border-b border-card font-medium">Severity</th>
                  <th className="p-4 border-b border-card font-medium">Item / Type</th>
                  <th className="p-4 border-b border-card font-medium">Detail</th>
                  <th className="p-4 border-b border-card font-medium">Recommended Action</th>
                </tr>
              </thead>
              <tbody>
                {data.risks.map((r, i) => (
                  <tr key={i} className="hover:bg-[#1a2535] transition-colors">
                    <td className="p-4 border-b border-card align-top">
                      <span className={`px-2 py-1 rounded-full text-xs font-bold ${
                        r.severity === 'HIGH' ? 'bg-red/20 text-red border border-red/30' :
                        r.severity === 'MEDIUM' ? 'bg-amber/20 text-amber border border-amber/30' :
                        'bg-gray-700 text-gray-300'
                      }`}>
                        {r.severity}
                      </span>
                    </td>
                    <td className="p-4 border-b border-card align-top">
                      <div className="font-semibold text-main">{r.canonical_name}</div>
                      <div className="text-xs text-muted mt-1">{r.risk_type}</div>
                    </td>
                    <td className="p-4 border-b border-card align-top text-sm text-main">{r.detail}</td>
                    <td className="p-4 border-b border-card align-top text-sm text-ice">{r.recommended_action}</td>
                  </tr>
                ))}
                {data.risks.length === 0 && (
                  <tr>
                    <td colSpan={4} className="p-8 text-center text-muted">No risks detected.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Stretch: Analyze Tool */}
        <div className="bg-card border border-card rounded-xl overflow-hidden">
          <div className="p-5 border-b border-card">
            <h2 className="text-xl font-semibold">Test Extractor: Paste a Quote</h2>
            <p className="text-sm text-muted mt-1">Paste raw vendor text to see how the agent parses and normalizes it.</p>
          </div>
          <div className="p-5">
            <form onSubmit={handleAnalyze} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs uppercase text-muted mb-2">Vendor Name</label>
                  <input 
                    type="text" 
                    value={analyzeVendor}
                    onChange={(e) => setAnalyzeVendor(e.target.value)}
                    className="w-full bg-[#0F1620] border border-card rounded p-2 text-main focus:outline-none focus:border-mint"
                  />
                </div>
                <div>
                  <label className="block text-xs uppercase text-muted mb-2">Format</label>
                  <select 
                    value={analyzeType}
                    onChange={(e) => setAnalyzeType(e.target.value)}
                    className="w-full bg-[#0F1620] border border-card rounded p-2 text-main focus:outline-none focus:border-mint"
                  >
                    <option value="pdf">PDF Text</option>
                    <option value="whatsapp">WhatsApp Export</option>
                    <option value="email">Email</option>
                    <option value="csv">CSV (Raw text)</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-xs uppercase text-muted mb-2">Raw Document Text</label>
                <textarea 
                  value={analyzeText}
                  onChange={(e) => setAnalyzeText(e.target.value)}
                  placeholder="Paste messy quote here..."
                  className="w-full h-32 bg-[#0F1620] border border-card rounded p-3 text-main font-mono text-sm focus:outline-none focus:border-mint"
                  required
                />
              </div>
              <button 
                type="submit" 
                disabled={analyzing}
                className="bg-mint text-[#0F1620] font-semibold py-2 px-6 rounded hover:bg-opacity-90 disabled:opacity-50 transition-colors"
              >
                {analyzing ? "Analyzing..." : "Parse & Normalize"}
              </button>
            </form>

            {/* Analysis Results */}
            {analyzeResults && (
              <div className="mt-8 border-t border-card pt-6">
                <h3 className="text-lg font-medium mb-4">Extracted Line Items</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-sm">
                    <thead>
                      <tr className="border-b border-card text-muted">
                        <th className="py-2">Raw Description</th>
                        <th className="py-2">Price</th>
                        <th className="py-2">Normalized To</th>
                        <th className="py-2">Match Confidence</th>
                      </tr>
                    </thead>
                    <tbody>
                      {analyzeResults.map((item, i) => (
                        <tr key={i} className="border-b border-card/50">
                          <td className="py-3 pr-4 font-mono text-xs">{item.raw_description}</td>
                          <td className="py-3 pr-4">₹{item.unit_price}/{item.uom}</td>
                          <td className="py-3 pr-4">
                            {item.normalized ? (
                              <span className="text-ice">{item.canonical_name} <span className="text-xs text-muted">({item.category})</span></span>
                            ) : (
                              <span className="text-red text-xs uppercase">Unmatched</span>
                            )}
                          </td>
                          <td className="py-3 text-muted">
                            {item.normalized ? `${(item.match_confidence * 100).toFixed(0)}%` : '-'}
                          </td>
                        </tr>
                      ))}
                      {analyzeResults.length === 0 && (
                        <tr>
                          <td colSpan={4} className="py-4 text-center text-muted">No items extracted from this text.</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
