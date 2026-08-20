import os
import json
from flask import Flask, render_template_string, jsonify, request
from google.cloud import bigquery

app = Flask(__name__)

# Environment variables
PROJECT_ID = os.environ.get("PROJECT_ID", "ai-hub-459714")
GE_DATASET = os.environ.get("GE_TRANSFORMED_DATASET", "ge_transformed")
GE_VIEW = os.environ.get("GE_VIEW", "ge_logs")

bq_client = bigquery.Client(project=PROJECT_ID)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gemini Enterprise Usage Analytics</title>
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body { background-color: #0f172a; color: #f8fafc; font-family: 'Inter', sans-serif; }
        .glass-card { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08); }
    </style>
</head>
<body class="p-6 md:p-10 min-h-screen">
    <!-- Header -->
    <div class="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4 border-b border-slate-800 pb-6">
        <div>
            <div class="flex items-center gap-3">
                <div class="p-2.5 bg-indigo-600/20 text-indigo-400 rounded-xl border border-indigo-500/30">
                    <i class="fa-solid fa-chart-line text-2xl"></i>
                </div>
                <div>
                    <h1 class="text-2xl font-bold text-white tracking-tight">Gemini Enterprise Usage Analytics</h1>
                    <p class="text-slate-400 text-sm">Real-time BigQuery Activity Observability & Metrics Dashboard</p>
                </div>
            </div>
        </div>
        <div class="flex items-center gap-3">
            <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <span class="w-2 h-2 rounded-full bg-emerald-400 mr-2 animate-pulse"></span> Connected to {{ project_id }}
            </span>
            <button onclick="fetchMetrics()" class="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition-colors duration-150 flex items-center gap-2 shadow-lg shadow-indigo-600/20">
                <i class="fa-solid fa-arrows-rotate" id="refresh-icon"></i> Refresh Data
            </button>
        </div>
    </div>

    <!-- KPI Summary Cards -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <!-- Total Queries -->
        <div class="glass-card p-6 rounded-2xl">
            <div class="flex justify-between items-center mb-4">
                <span class="text-slate-400 text-xs font-semibold uppercase tracking-wider">Total Queries</span>
                <span class="p-2 bg-blue-500/10 text-blue-400 rounded-lg"><i class="fa-solid fa-message text-lg"></i></span>
            </div>
            <div class="text-3xl font-bold text-white" id="stat-total-queries">--</div>
            <p class="text-slate-400 text-xs mt-2"><i class="fa-solid fa-clock mr-1 text-slate-500"></i> All time total queries logged</p>
        </div>

        <!-- Unique Active Users -->
        <div class="glass-card p-6 rounded-2xl">
            <div class="flex justify-between items-center mb-4">
                <span class="text-slate-400 text-xs font-semibold uppercase tracking-wider">Unique Active Users</span>
                <span class="p-2 bg-purple-500/10 text-purple-400 rounded-lg"><i class="fa-solid fa-users text-lg"></i></span>
            </div>
            <div class="text-3xl font-bold text-white" id="stat-unique-users">--</div>
            <p class="text-slate-400 text-xs mt-2"><i class="fa-solid fa-user-check mr-1 text-slate-500"></i> Unique IAM Principals</p>
        </div>

        <!-- Total Sessions -->
        <div class="glass-card p-6 rounded-2xl">
            <div class="flex justify-between items-center mb-4">
                <span class="text-slate-400 text-xs font-semibold uppercase tracking-wider">Total Sessions</span>
                <span class="p-2 bg-indigo-500/10 text-indigo-400 rounded-lg"><i class="fa-solid fa-comments text-lg"></i></span>
            </div>
            <div class="text-3xl font-bold text-white" id="stat-total-sessions">--</div>
            <p class="text-slate-400 text-xs mt-2"><i class="fa-solid fa-layer-group mr-1 text-slate-500"></i> Active Assistant Conversations</p>
        </div>

        <!-- Active Engines -->
        <div class="glass-card p-6 rounded-2xl">
            <div class="flex justify-between items-center mb-4">
                <span class="text-slate-400 text-xs font-semibold uppercase tracking-wider">Active Apps / Engines</span>
                <span class="p-2 bg-emerald-500/10 text-emerald-400 rounded-lg"><i class="fa-solid fa-robot text-lg"></i></span>
            </div>
            <div class="text-3xl font-bold text-white" id="stat-active-engines">--</div>
            <p class="text-slate-400 text-xs mt-2"><i class="fa-solid fa-cubes mr-1 text-slate-500"></i> Gemini Engines Executed</p>
        </div>
    </div>

    <!-- Main Charts Section -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        <!-- Chart 1: Daily Session Volume -->
        <div class="glass-card p-6 rounded-2xl">
            <div class="flex justify-between items-center mb-6">
                <div>
                    <h3 class="text-lg font-bold text-white">Daily Session & Query Volume</h3>
                    <p class="text-slate-400 text-xs">Query activity count aggregated by date</p>
                </div>
                <span class="px-2.5 py-1 text-xs bg-slate-800 text-slate-300 rounded-md font-mono">30 Days</span>
            </div>
            <div class="h-72">
                <canvas id="dailyVolumeChart"></canvas>
            </div>
        </div>

        <!-- Chart 2: Top Active Users -->
        <div class="glass-card p-6 rounded-2xl">
            <div class="flex justify-between items-center mb-6">
                <div>
                    <h3 class="text-lg font-bold text-white">Top Active Users</h3>
                    <p class="text-slate-400 text-xs">Most active IAM Principals by query count</p>
                </div>
                <span class="px-2.5 py-1 text-xs bg-slate-800 text-slate-300 rounded-md font-mono">Top 5</span>
            </div>
            <div class="h-72">
                <canvas id="topUsersChart"></canvas>
            </div>
        </div>
    </div>

    <!-- Bottom Section: Top Search Queries Table & Recent Queries Log -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <!-- Top Search Queries -->
        <div class="glass-card p-6 rounded-2xl">
            <div class="flex justify-between items-center mb-6">
                <div>
                    <h3 class="text-lg font-bold text-white">Top Search Queries</h3>
                    <p class="text-slate-400 text-xs">Most frequent user prompts and search questions</p>
                </div>
            </div>
            <div class="overflow-x-auto">
                <table class="w-full text-left text-sm text-slate-300">
                    <thead class="bg-slate-800/60 text-slate-400 text-xs uppercase tracking-wider border-b border-slate-700/50">
                        <tr>
                            <th class="py-3 px-4">User Prompt / Query</th>
                            <th class="py-3 px-4 text-right">Count</th>
                        </tr>
                    </thead>
                    <tbody id="top-queries-table-body" class="divide-y divide-slate-800">
                        <tr><td colspan="2" class="py-4 text-center text-slate-500">Loading queries...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Recent Activity Feed -->
        <div class="glass-card p-6 rounded-2xl">
            <div class="flex justify-between items-center mb-6">
                <div>
                    <h3 class="text-lg font-bold text-white">Recent Activity Stream</h3>
                    <p class="text-slate-400 text-xs">Latest 5 user interactions from BigQuery</p>
                </div>
            </div>
            <div class="space-y-4" id="recent-activity-container">
                <div class="text-center py-6 text-slate-500 text-sm">Loading activity feed...</div>
            </div>
        </div>
    </div>

    <script>
        let dailyChartInstance = null;
        let topUsersChartInstance = null;

        async function fetchMetrics() {
            const refreshIcon = document.getElementById('refresh-icon');
            refreshIcon.classList.add('animate-spin');

            try {
                const response = await fetch('/api/metrics');
                const data = await response.json();

                // Update KPI Cards
                document.getElementById('stat-total-queries').innerText = data.kpis.total_queries.toLocaleString();
                document.getElementById('stat-unique-users').innerText = data.kpis.unique_users.toLocaleString();
                document.getElementById('stat-total-sessions').innerText = data.kpis.total_sessions.toLocaleString();
                document.getElementById('stat-active-engines').innerText = data.kpis.active_engines.toLocaleString();

                // Render Daily Volume Chart
                renderDailyChart(data.daily_volume);

                // Render Top Users Chart
                renderTopUsersChart(data.top_users);

                // Render Top Search Queries Table
                renderTopQueriesTable(data.top_queries);

                // Render Recent Activity Stream
                renderRecentActivity(data.recent_activity);

            } catch (err) {
                console.error("Error fetching metrics:", err);
            } finally {
                refreshIcon.classList.remove('animate-spin');
            }
        }

        function renderDailyChart(dailyData) {
            const ctx = document.getElementById('dailyVolumeChart').getContext('2d');
            const labels = dailyData.map(d => d.date);
            const counts = dailyData.map(d => d.count);

            if (dailyChartInstance) dailyChartInstance.destroy();

            dailyChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Daily Queries',
                        data: counts,
                        borderColor: '#6366f1',
                        backgroundColor: 'rgba(99, 102, 241, 0.15)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.3,
                        pointBackgroundColor: '#818cf8',
                        pointRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#94a3b8' } },
                        y: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#94a3b8', beginAtZero: true } }
                    }
                }
            });
        }

        function renderTopUsersChart(usersData) {
            const ctx = document.getElementById('topUsersChart').getContext('2d');
            const labels = usersData.map(u => u.user.split('@')[0] || u.user);
            const counts = usersData.map(u => u.count);

            if (topUsersChartInstance) topUsersChartInstance.destroy();

            topUsersChartInstance = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Queries Submitted',
                        data: counts,
                        backgroundColor: 'rgba(168, 85, 247, 0.65)',
                        borderColor: '#a855f7',
                        borderWidth: 1,
                        borderRadius: 8
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { grid: { display: false }, ticks: { color: '#94a3b8' } },
                        y: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, ticks: { color: '#94a3b8', beginAtZero: true } }
                    }
                }
            });
        }

        function renderTopQueriesTable(queriesData) {
            const tbody = document.getElementById('top-queries-table-body');
            if (!queriesData || queriesData.length === 0) {
                tbody.innerHTML = '<tr><td colspan="2" class="py-4 text-center text-slate-500">No query data recorded yet.</td></tr>';
                return;
            }

            tbody.innerHTML = queriesData.map(q => `
                <tr class="hover:bg-slate-800/40 transition-colors">
                    <td class="py-3 px-4 font-mono text-xs text-indigo-300 truncate max-w-md">${escapeHtml(q.query)}</td>
                    <td class="py-3 px-4 text-right font-bold text-white">${q.count}</td>
                </tr>
            `).join('');
        }

        function renderRecentActivity(activities) {
            const container = document.getElementById('recent-activity-container');
            if (!activities || activities.length === 0) {
                container.innerHTML = '<div class="text-center py-6 text-slate-500 text-sm">No recent activity found.</div>';
                return;
            }

            container.innerHTML = activities.map(act => `
                <div class="p-3.5 bg-slate-800/50 rounded-xl border border-slate-700/40 flex items-start gap-3">
                    <div class="p-2 bg-indigo-500/10 text-indigo-400 rounded-lg mt-0.5"><i class="fa-solid fa-paper-plane text-xs"></i></div>
                    <div class="flex-1 min-w-0">
                        <div class="flex justify-between items-center mb-1">
                            <span class="text-xs font-semibold text-slate-300 truncate">${escapeHtml(act.user)}</span>
                            <span class="text-[10px] text-slate-500 font-mono">${act.timestamp}</span>
                        </div>
                        <p class="text-xs font-mono text-indigo-200 truncate">${escapeHtml(act.query || 'Method Action')}</p>
                    </div>
                </div>
            `).join('');
        }

        function escapeHtml(str) {
            if (!str) return '';
            return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
        }

        // Initial Load
        fetchMetrics();
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE, project_id=PROJECT_ID)

@app.route("/api/metrics")
def get_metrics():
    table_ref = f"`{PROJECT_ID}.{GE_DATASET}.{GE_VIEW}`"
    
    try:
        # KPI 1: Summary Counts
        kpi_query = f"""
            SELECT
                COUNT(*) as total_queries,
                COUNT(DISTINCT userIamPrincipal) as unique_users,
                COUNT(DISTINCT session_id) as total_sessions,
                COUNT(DISTINCT engine_id) as active_engines
            FROM {table_ref}
        """
        kpi_res = list(bq_client.query(kpi_query).result())[0]
        kpis = {
            "total_queries": kpi_res.total_queries or 0,
            "unique_users": kpi_res.unique_users or 0,
            "total_sessions": kpi_res.total_sessions or 0,
            "active_engines": kpi_res.active_engines or 0
        }

        # Chart 1: Daily Session & Query Volume (Last 30 Days)
        daily_query = f"""
            SELECT
                FORMAT_DATE('%Y-%m-%d', DATE(timestamp)) as date,
                COUNT(*) as count
            FROM {table_ref}
            WHERE timestamp IS NOT NULL
            GROUP BY date
            ORDER BY date ASC
            LIMIT 30
        """
        daily_res = list(bq_client.query(daily_query).result())
        daily_volume = [{"date": r.date, "count": r.count} for r in daily_res]

        # Chart 2: Top Active Users (Unique IAM Principals)
        users_query = f"""
            SELECT
                COALESCE(userIamPrincipal, 'Anonymous / Service') as user,
                COUNT(*) as count
            FROM {table_ref}
            GROUP BY user
            ORDER BY count DESC
            LIMIT 5
        """
        users_res = list(bq_client.query(users_query).result())
        top_users = [{"user": r.user, "count": r.count} for r in users_res]

        # Table 1: Top Search Queries
        queries_query = f"""
            SELECT
                userQuery as query,
                COUNT(*) as count
            FROM {table_ref}
            WHERE userQuery IS NOT NULL AND userQuery != '' AND NOT STARTS_WITH(userQuery, '{{\"')
            GROUP BY query
            ORDER BY count DESC
            LIMIT 8
        """
        queries_res = list(bq_client.query(queries_query).result())
        top_queries = [{"query": r.query, "count": r.count} for r in queries_res]

        # Stream 1: Recent Activity Log
        activity_query = f"""
            SELECT
                COALESCE(userIamPrincipal, 'Anonymous') as user,
                COALESCE(userQuery, methodName) as query,
                FORMAT_TIMESTAMP('%H:%M:%S', timestamp) as timestamp
            FROM {table_ref}
            ORDER BY timestamp DESC
            LIMIT 5
        """
        act_res = list(bq_client.query(activity_query).result())
        recent_activity = [{"user": r.user, "query": r.query, "timestamp": r.timestamp} for r in act_res]

        return jsonify({
            "kpis": kpis,
            "daily_volume": daily_volume,
            "top_users": top_users,
            "top_queries": top_queries,
            "recent_activity": recent_activity
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
