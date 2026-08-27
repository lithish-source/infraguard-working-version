import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  RadialLinearScale,
  Filler,
} from 'chart.js';
import { Bar, Line, Doughnut, Radar } from 'react-chartjs-2';
import { useMemo } from 'react';

ChartJS.register(
  CategoryScale, LinearScale, PointElement, LineElement, BarElement,
  ArcElement, Title, Tooltip, Legend, RadialLinearScale, Filler
);

const THEME_COLORS = {
  brand: '#1f44f5',
  green: '#22c55e',
  amber: '#f59e0b',
  red: '#ef4444',
  purple: '#7c3aed',
  blue: '#3b82f6',
  slate: '#64748b',
};

export function SeverityDoughnut({ data }) {
  const chartData = useMemo(() => {
    const labels = (data || []).map((d) => d.severity);
    const counts = (data || []).map((d) => d.count);
    const colors = labels.map((l) => THEME_COLORS[
      l === 'Low' ? 'green' :
      l === 'Moderate' ? 'amber' :
      l === 'High' ? 'red' :
      l === 'Critical' ? 'purple' : 'slate'
    ]);
    return {
      labels,
      datasets: [{
        data: counts,
        backgroundColor: colors,
        borderColor: '#fff',
        borderWidth: 2,
      }],
    };
  }, [data]);

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'bottom', labels: { boxWidth: 12, padding: 12 } },
    },
    cutout: '65%',
  };

  return (
    <div style={{ height: '280px' }}>
      <Doughnut data={chartData} options={options} />
    </div>
  );
}

export function CategoryBar({ data }) {
  const chartData = useMemo(() => ({
    labels: (data || []).map((d) => d.category),
    datasets: [
      {
        label: 'Total Reports',
        data: (data || []).map((d) => d.count),
        backgroundColor: THEME_COLORS.brand,
        borderRadius: 4,
      },
      {
        label: 'Critical',
        data: (data || []).map((d) => d.critical_count),
        backgroundColor: THEME_COLORS.red,
        borderRadius: 4,
      },
    ],
  }), [data]);

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { position: 'bottom' } },
    scales: { x: { stacked: false }, y: { beginAtZero: true } },
  };

  return (
    <div style={{ height: '300px' }}>
      <Bar data={chartData} options={options} />
    </div>
  );
}

export function MonthlyTrendLine({ data }) {
  const chartData = useMemo(() => ({
    labels: (data || []).map((d) => d.month),
    datasets: [
      {
        label: 'Reports',
        data: (data || []).map((d) => d.reports),
        borderColor: THEME_COLORS.brand,
        backgroundColor: 'rgba(31, 68, 245, 0.1)',
        tension: 0.35,
        fill: true,
      },
      {
        label: 'Resolved',
        data: (data || []).map((d) => d.resolved),
        borderColor: THEME_COLORS.green,
        backgroundColor: 'rgba(34, 197, 94, 0.1)',
        tension: 0.35,
        fill: true,
      },
    ],
  }), [data]);

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { position: 'bottom' } },
    scales: { y: { beginAtZero: true } },
  };

  return (
    <div style={{ height: '300px' }}>
      <Line data={chartData} options={options} />
    </div>
  );
}

export function DistrictAnalyticsBar({ data }) {
  const chartData = useMemo(() => ({
    labels: (data || []).map((d) => d.district),
    datasets: [
      {
        label: 'Reports',
        data: (data || []).map((d) => d.reports),
        backgroundColor: THEME_COLORS.blue,
        borderRadius: 4,
      },
      {
        label: 'Critical',
        data: (data || []).map((d) => d.critical),
        backgroundColor: THEME_COLORS.red,
        borderRadius: 4,
      },
      {
        label: 'Resolved',
        data: (data || []).map((d) => d.resolved),
        backgroundColor: THEME_COLORS.green,
        borderRadius: 4,
      },
    ],
  }), [data]);

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { position: 'bottom' } },
    scales: { x: { stacked: false }, y: { beginAtZero: true } },
  };

  return (
    <div style={{ height: '320px' }}>
      <Bar data={chartData} options={options} />
    </div>
  );
}

export function PriorityRadar({ components }) {
  const labels = Object.keys(components || {}).map((k) =>
    k.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
  );
  const values = Object.values(components || {});

  const chartData = {
    labels,
    datasets: [
      {
        label: 'Priority Components',
        data: values,
        backgroundColor: 'rgba(31, 68, 245, 0.2)',
        borderColor: THEME_COLORS.brand,
        borderWidth: 2,
        pointBackgroundColor: THEME_COLORS.brand,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      r: {
        min: 0,
        max: 1,
        ticks: { stepSize: 0.2 },
      },
    },
  };

  return (
    <div style={{ height: '320px' }}>
      <Radar data={chartData} options={options} />
    </div>
  );
}
