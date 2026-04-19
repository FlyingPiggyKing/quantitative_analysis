"use client";

import { useEffect, useRef, useState } from "react";
import {
  createChart,
  IChartApi,
  ISeriesApi,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
  CandlestickData,
  HistogramData,
  LineData,
  Time,
  SeriesOptionsMap,
} from "lightweight-charts";

interface KLineData {
  date: string;
  open: number;
  close: number;
  high: number;
  low: number;
  volume: number;
}

interface ValuationSeriesData {
  date: string;
  value: number | null;
}

interface StockChartProps {
  data: KLineData[];
  peData?: ValuationSeriesData[];
  pbData?: ValuationSeriesData[];
}

export default function StockChart({ data, peData, pbData }: StockChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const [legendData, setLegendData] = useState<{ pe: number | null; pb: number | null }>({ pe: null, pb: null });

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { color: "#1e293b" },
        textColor: "#94a3b8",
      },
      grid: {
        vertLines: { color: "#334155" },
        horzLines: { color: "#334155" },
      },
      crosshair: {
        mode: 1,
        vertLine: {
          color: "#64748b",
          labelBackgroundColor: "#475569",
        },
        horzLine: {
          color: "#64748b",
          labelBackgroundColor: "#475569",
        },
      },
      rightPriceScale: {
        borderColor: "#334155",
      },
      timeScale: {
        borderColor: "#334155",
        timeVisible: true,
      },
      handleScroll: {
        vertTouchDrag: false,
      },
    });

    chartRef.current = chart;

    // Candlestick series (v5 API)
    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#ef4444",
      downColor: "#22c55e",
      borderUpColor: "#ef4444",
      borderDownColor: "#22c55e",
      wickUpColor: "#ef4444",
      wickDownColor: "#22c55e",
    });

    // Volume series (v5 API)
    const volumeSeries = chart.addSeries(HistogramSeries, {
      color: "#64748b",
      priceFormat: {
        type: "volume",
      },
      priceScaleId: "",
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.8,
        bottom: 0,
      },
    });

    // PE line series
    let peSeries: ISeriesApi<"Line"> | null = null;
    if (peData && peData.length > 0) {
      peSeries = chart.addSeries(LineSeries, {
        color: "#fbbf24",
        lineWidth: 2,
        priceScaleId: "pe",
      });
      peSeries.priceScale().applyOptions({
        scaleMargins: {
          top: 0.85,
          bottom: 0,
        },
      });
    }

    // PB line series
    let pbSeries: ISeriesApi<"Line"> | null = null;
    if (pbData && pbData.length > 0) {
      pbSeries = chart.addSeries(LineSeries, {
        color: "#8b5cf6",
        lineWidth: 2,
        priceScaleId: "pb",
      });
      pbSeries.priceScale().applyOptions({
        scaleMargins: {
          top: 0.92,
          bottom: 0,
        },
      });
    }

    // Set data
    if (data.length > 0) {
      const candleData: CandlestickData<Time>[] = data.map((d) => ({
        time: d.date as Time,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
      }));

      const volumeData: HistogramData<Time>[] = data.map((d) => ({
        time: d.date as Time,
        value: d.volume,
        color: d.close >= d.open ? "#22c55e80" : "#ef444480",
      }));

      candlestickSeries.setData(candleData);
      volumeSeries.setData(volumeData);

      // Set PE data, filtering out null values
      if (peSeries && peData) {
        const peLineData: LineData<Time>[] = peData
          .filter((d) => d.value != null)
          .map((d) => ({
            time: d.date as Time,
            value: d.value!,
          }));
        peSeries.setData(peLineData);

        // Set initial legend value
        const lastValidPe = [...peData].reverse().find((d) => d.value != null);
        if (lastValidPe) {
          setLegendData((prev) => ({ ...prev, pe: lastValidPe.value }));
        }
      }

      // Set PB data, filtering out null values
      if (pbSeries && pbData) {
        const pbLineData: LineData<Time>[] = pbData
          .filter((d) => d.value != null)
          .map((d) => ({
            time: d.date as Time,
            value: d.value!,
          }));
        pbSeries.setData(pbLineData);

        // Set initial legend value
        const lastValidPb = [...pbData].reverse().find((d) => d.value != null);
        if (lastValidPb) {
          setLegendData((prev) => ({ ...prev, pb: lastValidPb.value }));
        }
      }

      chart.timeScale().fitContent();
    }

    // Handle crosshair move for legend update
    chart.subscribeCrosshairMove((param) => {
      if (param.seriesData.size > 0) {
        const peDataAt = param.seriesData.get(peSeries!) as LineData<Time> | undefined;
        const pbDataAt = param.seriesData.get(pbSeries!) as LineData<Time> | undefined;
        if (peDataAt || pbDataAt) {
          setLegendData({
            pe: peDataAt?.value ?? null,
            pb: pbDataAt?.value ?? null,
          });
        }
      }
    });

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        const isMobile = window.innerWidth < 640;
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
          height: isMobile ? 250 : 400,
        });
      }
    };

    window.addEventListener("resize", handleResize);
    handleResize();

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, [data, peData, pbData]);

  return (
    <div className="relative">
      {/* Legend */}
      <div className="absolute top-2 left-2 z-10 flex gap-4 text-sm">
        {legendData.pe !== null && (
          <div className="flex items-center gap-1">
            <span className="w-3 h-0.5 bg-yellow-400"></span>
            <span className="text-slate-400">PE:</span>
            <span className="text-white">{legendData.pe.toFixed(2)}</span>
          </div>
        )}
        {legendData.pb !== null && (
          <div className="flex items-center gap-1">
            <span className="w-3 h-0.5 bg-purple-500"></span>
            <span className="text-slate-400">PB:</span>
            <span className="text-white">{legendData.pb.toFixed(2)}</span>
          </div>
        )}
      </div>
      <div ref={chartContainerRef} className="w-full h-[250px] sm:h-[400px]" />
    </div>
  );
}
