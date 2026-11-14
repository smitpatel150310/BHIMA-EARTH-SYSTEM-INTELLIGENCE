import React from 'react';
import { Plot } from './PlotWrapper';
import { TimeSeriesData, TrendResult } from '../../types';

export interface TimeSeriesChartProps {
  timeseries: TimeSeriesData;
  trend?: TrendResult | null;
  height?: number;
  showTrendLine?: boolean;
}

export const TimeSeriesChart: React.FC<TimeSeriesChartProps> = ({
  timeseries,
  trend,
  height = 360,
  showTrendLine = true,
}) => {
  const dates = timeseries.data.map((d) => d.date);
  const values = timeseries.data.map((d) => d.value);

  // Raw observation trace
  const traces: any[] = [
    {
      x: dates,
      y: values,
      type: 'scatter',
      mode: 'lines+markers',
      name: timeseries.variable || 'Observed Data',
      line: {
        color: '#31594B',
        width: 1.75,
      },
      marker: {
        size: 3.5,
        color: '#31594B',
      },
      hovertemplate: '<b>%{x}</b><br>Value: %{y:.2f} ' + (timeseries.units || '') + '<extra></extra>',
    },
  ];

  // Optional Trend Line overlay computed from Sen's slope or start-end points
  if (showTrendLine && trend && dates.length > 1) {
    const validPoints = timeseries.data.filter((d) => d.value !== null && d.value !== undefined);
    if (validPoints.length >= 2) {
      const firstDate = dates[0];
      const lastDate = dates[dates.length - 1];

      // Calculate approximate trend endpoints
      // Slope is per year. Number of years between start and end:
      const nYears = Math.max(1, dates.length / 12);
      const meanVal = validPoints.reduce((acc, p) => acc + (p.value || 0), 0) / validPoints.length;
      
      const yStart = meanVal - (trend.slope * nYears) / 2;
      const yEnd = meanVal + (trend.slope * nYears) / 2;

      traces.push({
        x: [firstDate, lastDate],
        y: [yStart, yEnd],
        type: 'scatter',
        mode: 'lines',
        name: `Sen's Trend (${trend.slope >= 0 ? '+' : ''}${trend.slope.toFixed(3)} ${trend.slope_units})`,
        line: {
          color: trend.is_significant ? '#B2782A' : '#84978B',
          width: 2,
          dash: 'dash',
        },
        hoverinfo: 'name',
      });
    }
  }

  const layout: any = {
    autosize: true,
    height,
    margin: { t: 24, r: 24, b: 48, l: 64 },
    showlegend: true,
    legend: {
      orientation: 'h',
      yanchor: 'bottom',
      y: 1.02,
      xanchor: 'right',
      x: 1,
      font: { family: 'Inter, sans-serif', size: 11, color: '#69736D' },
    },
    paper_bgcolor: '#FFFFFF',
    plot_bgcolor: '#FFFFFF',
    xaxis: {
      type: 'date',
      showgrid: true,
      gridcolor: '#EEF1ED',
      linecolor: '#E4E8E4',
      tickfont: { family: 'Inter, sans-serif', size: 10, color: '#69736D' },
      zeroline: false,
    },
    yaxis: {
      title: {
        text: `${timeseries.variable} (${timeseries.units})`,
        font: { family: 'Inter, sans-serif', size: 11, color: '#202824' },
      },
      showgrid: true,
      gridcolor: '#EEF1ED',
      linecolor: '#E4E8E4',
      tickfont: { family: 'Inter, sans-serif', size: 10, color: '#69736D' },
      zeroline: false,
    },
    hoverlabel: {
      bgcolor: '#202824',
      font: { family: 'Inter, sans-serif', size: 11, color: '#FFFFFF' },
      bordercolor: '#202824',
    },
  };

  const config: any = {
    responsive: true,
    displayModeBar: true,
    displaylogo: false,
    modeBarButtonsToRemove: ['lasso2d', 'select2d'],
  };

  return (
    <div className="w-full bg-white rounded-lg border border-bhima-border p-3 sm:p-4">
      <Plot data={traces} layout={layout} config={config} />
    </div>
  );
};
