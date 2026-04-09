"use client";

import ConfigLivePage from "./ConfigLivePage";

// Legacy placeholder kept temporarily while the live page is wired for the demo.
// eslint-disable-next-line @typescript-eslint/no-unused-vars
function LegacySystemConfigPage() {
  return (
    <div className="px-8 py-7 space-y-6">
      <div>
        <h2 className="text-3xl font-black text-gray-900">System Configuration</h2>
        <p className="text-sm text-gray-500 mt-1">MacroPulse agent settings, alert thresholds, and integration preferences</p>
      </div>
      <div className="grid grid-cols-2 gap-5">
        {[
          { title: "Alert Thresholds", items: ["Anomaly Confidence: 90%", "Inflation Variance: ±0.5%", "FX Volatility: ±2%"] },
          { title: "Data Refresh", items: ["Live feeds: Every 2s", "Research data: Daily 06:00 UTC", "Reports: Weekly Monday"] },
          { title: "Notification Channels", items: ["Email: CFO team", "Slack: #macro-alerts", "SMS: Critical only"] },
          { title: "AI Model Settings", items: ["Primary: GPT-4o", "Fallback: Claude 3.5", "Confidence threshold: 85%"] },
        ].map(section => (
          <div key={section.title} className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
            <h3 className="text-sm font-bold text-gray-800 mb-4 uppercase tracking-wider">{section.title}</h3>
            <div className="space-y-2">
              {section.items.map(item => (
                <div key={item} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                  <span className="text-sm text-gray-600">{item.split(":")[0]}</span>
                  <span className="text-sm font-semibold text-gray-900">{item.split(":")[1]}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default ConfigLivePage;
