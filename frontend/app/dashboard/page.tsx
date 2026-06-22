import { getEvaluations } from '@/lib/api';

export default async function DashboardPage() {
  const data = await getEvaluations();

  return (
    <div className="p-8 max-w-6xl mx-auto w-full text-neutral-100">
      <h1 className="text-3xl font-bold mb-8 tracking-tight">Evaluation Dashboard</h1>
      
      {/* Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <MetricCard title="Total Queries" value={data.metrics.total_queries} />
        <MetricCard title="Avg Latency" value={`${data.metrics.avg_latency_ms} ms`} />
        <MetricCard title="Positive Feedback" value={`${data.metrics.positive_ratio}%`} subtitle={`${data.metrics.up_votes} up / ${data.metrics.down_votes} down`} />
        <MetricCard title="Coverage Gaps" value={data.coverage_gaps.length} subtitle="Recent 'No Info' queries" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        {/* Top Cited Chunks */}
        <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6">
          <h2 className="text-xl font-semibold mb-4 text-white">Top Cited Chunks</h2>
          <div className="space-y-4">
            {data.top_chunks.length === 0 ? (
              <p className="text-sm text-neutral-500">No data available.</p>
            ) : (
              data.top_chunks.map((chunk: any, i: number) => (
                <div key={i} className="flex justify-between items-center bg-neutral-800/50 p-3 rounded-lg border border-neutral-700">
                  <div className="flex flex-col">
                    <span className="text-sm font-medium text-blue-400">{chunk.filename}</span>
                    {chunk.page && <span className="text-xs text-neutral-400">Page {chunk.page}</span>}
                  </div>
                  <span className="text-sm bg-neutral-700 px-2 py-1 rounded text-neutral-200">{chunk.count} cites</span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Coverage Gaps */}
        <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6">
          <h2 className="text-xl font-semibold mb-4 text-white">Recent Coverage Gaps</h2>
          <div className="space-y-4">
            {data.coverage_gaps.length === 0 ? (
              <p className="text-sm text-neutral-500">No coverage gaps detected.</p>
            ) : (
              data.coverage_gaps.slice(0, 5).map((gap: any, i: number) => (
                <div key={i} className="flex flex-col bg-neutral-800/50 p-3 rounded-lg border border-neutral-700">
                  <span className="text-sm text-neutral-200">"{gap.question}"</span>
                  <span className="text-xs text-neutral-500 mt-2">{new Date(gap.created_at).toLocaleString()}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Recent Feedback */}
      <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6">
        <h2 className="text-xl font-semibold mb-4 text-white">Recent Feedback</h2>
        <div className="space-y-4">
          {data.recent_feedback.length === 0 ? (
            <p className="text-sm text-neutral-500">No feedback available.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-neutral-400">
                <thead className="text-xs text-neutral-500 uppercase bg-neutral-800/50 rounded-lg">
                  <tr>
                    <th className="px-4 py-3">Rating</th>
                    <th className="px-4 py-3">Question</th>
                    <th className="px-4 py-3">Answer Snippet</th>
                    <th className="px-4 py-3">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {data.recent_feedback.map((log: any) => (
                    <tr key={log.id} className="border-b border-neutral-800 hover:bg-neutral-800/30">
                      <td className="px-4 py-3 font-medium">
                        {log.feedback === 'up' ? '👍 Up' : '👎 Down'}
                      </td>
                      <td className="px-4 py-3 text-neutral-200">"{log.question}"</td>
                      <td className="px-4 py-3 truncate max-w-xs">{log.answer}</td>
                      <td className="px-4 py-3">{new Date(log.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

    </div>
  );
}

function MetricCard({ title, value, subtitle }: { title: string, value: string | number, subtitle?: string }) {
  return (
    <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6 flex flex-col justify-center">
      <h3 className="text-sm font-medium text-neutral-500 uppercase tracking-wider mb-2">{title}</h3>
      <div className="text-3xl font-bold text-white">{value}</div>
      {subtitle && <div className="text-xs text-neutral-400 mt-2">{subtitle}</div>}
    </div>
  );
}
