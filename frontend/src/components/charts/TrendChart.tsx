import React from 'react';
import { Plot } from './PlotWrapper';
import { TimeSeriesData, TrendResult } from '../../types';

export interface TrendChartProps {
  timeseries: TimeSeriesData;
  trend: TrendResult;
  height?: number;
}

export const TrendChart: React.FC<TrendChartProps> = ({ timeseries, trend, height = 300 }) => {
  // Aggregate data annually to visualize multi-decadal trends cleanly
  const annualMap = new Map<string, { sum: number; count: number }>();

  timeseries.data.forEach((d) => {
    if (d.value === null || d.value === undefined) return;
    const year = d.date.slice(0, 4);
    const existing = annualMap.get(year) || { sum: 0, count: 0 };
    annualMap.set(year, { sum: existing.sum + d.value, count: existing.count + 1 });
  });

  const years = Array.from(annualMap.keys()).sort();
  const annualMeans = years.map((yr) => {
    const item = annualMap.get(yr)!;
    return item.count > 0 ? item.sum / item.count : 0;
  });

  const traces: any[] = [
    {
      x: years,
      y: annualMeans,
      type: 'bar',
      name: 'Annual Mean',
      marker: {
        color: '#EEF1ED',
        line: { color: '#84978B', width: 1 },
      },
      hovertemplate: '<b>%{x}</b><br>Annual Mean: %{y:.2f}<extra></extra>',
    },
  ];

  if (years.length >= 2) {
    const meanVal = annualMeans.reduce((a, b) => a + b, 0) / annualMeans.length;
    const halfYears = years.length / 2;
    const yStart = meanVal - (trend.slope * halfYears);
    const yEnd = meanVal + (trend.slope * halfYears);

    traces.push({
      x: [years[0], years[years.length - 1]],
      y: [yStart, yEnd],
      type: 'scatter',
      mode: 'lines',
      name: `Sen's Trend (${trend.slope >= 0 ? '+' : ''}${trend.slope.toFixed(2)} / yr)`,
      line: {
        color: '#31594B',
        width: 2.5,
      },
    });
  }

  const layout: any = {
    autosize: true,
    height,
    margin: { t: 20, r: 20, b: 40, l: 60 },
    showlegend: true,
    legend: {
      orientation: 'h',
      y: 1.1,
      x: 1,
      xanchor: 'right',
      font: { family: 'Inter, sans-serif', size: 10, color: '#69736D' },
    },
    paper_bgcolor: '#FFFFFF',
    plot_bgcolor: '#FFFFFF',
    xaxis: {
      tickfont: { family: 'Inter, sans-serif', size: 10, color: '#69736D' },
      gridcolor: '#EEF1ED',
    },
    yaxis: {
      title: {
        text: `Mean (${timeseries.units})`,
        font: { family: 'Inter, sans-serif', size: 10, color: '#202824' },
      },
      tickfont: { family: 'Inter, sans-serif', size: 10, color: '#69736D' },
      gridcolor: '#EEF1ED',
    },
  };

  const config = {
    responsive: true,
    displayModeBar: false,
  };

  return (
    <div className="w-full bg-white rounded-lg border border-bhima-border p-3">
      <Plot data={traces} layout={layout} config={config} />
    </div>
  );
};
