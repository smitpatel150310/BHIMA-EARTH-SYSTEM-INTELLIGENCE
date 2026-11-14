import React from 'react';
import { Plot } from './PlotWrapper';
import { AnalysisResult } from '../../types';

export interface ComparisonChartProps {
  regionA: AnalysisResult;
  regionB: AnalysisResult;
  height?: number;
}

export const ComparisonChart: React.FC<ComparisonChartProps> = ({
  regionA,
  regionB,
  height = 380,
}) => {
  const nameA =
    typeof regionA.timeseries.region === 'string'
      ? regionA.timeseries.region
      : regionA.timeseries.region?.name || 'Region A';

  const nameB =
    typeof regionB.timeseries.region === 'string'
      ? regionB.timeseries.region
      : regionB.timeseries.region?.name || 'Region B';

  const traces: any[] = [
    {
      x: regionA.timeseries.data.map((d) => d.date),
      y: regionA.timeseries.data.map((d) => d.value),
      type: 'scatter',
      mode: 'lines',
      name: `${nameA}`,
      line: {
        color: '#31594B', // Forest green
        width: 1.8,
      },
      hovertemplate: `<b>${nameA}</b><br>%{x}: %{y:.2f} ${regionA.timeseries.units}<extra></extra>`,
    },
    {
      x: regionB.timeseries.data.map((d) => d.date),
      y: regionB.timeseries.data.map((d) => d.value),
      type: 'scatter',
      mode: 'lines',
      name: `${nameB}`,
      line: {
        color: '#A85A3F', // Warm terra-cotta/earth brown
        width: 1.8,
      },
      hovertemplate: `<b>${nameB}</b><br>%{x}: %{y:.2f} ${regionB.timeseries.units}<extra></extra>`,
    },
  ];

  const layout: any = {
    autosize: true,
    height,
    margin: { t: 24, r: 24, b: 48, l: 64 },
    showlegend: true,
    legend: {
      orientation: 'h',
      y: 1.08,
      x: 1,
      xanchor: 'right',
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
    },
    yaxis: {
      title: {
        text: `${regionA.timeseries.variable} (${regionA.timeseries.units})`,
        font: { family: 'Inter, sans-serif', size: 11, color: '#202824' },
      },
      showgrid: true,
      gridcolor: '#EEF1ED',
      linecolor: '#E4E8E4',
      tickfont: { family: 'Inter, sans-serif', size: 10, color: '#69736D' },
    },
    hoverlabel: {
      bgcolor: '#202824',
      font: { family: 'Inter, sans-serif', size: 11, color: '#FFFFFF' },
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
