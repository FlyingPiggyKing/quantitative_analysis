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
        background: { color: "#14110d" },
        textColor: "#b8a87d",
      },
      grid: {
        vertLines: { color: "#2d251a" },
        horzLines: { color: "#2d251a" },
      },
      crosshair: {
        mode: 1,
        vertLine: {
          color: "#c89c3a",
          labelBackgroundColor: "#6b4f15",
        },
        horzLine: {
          color: "#c89c3a",
          labelBackgroundColor: "#6b4f15",
        },
      },
      rightPriceScale: {
        borderColor: "#3a3022",
      },
      timeScale: {
        borderColor: "#3a3022",
        timeVisible: true,
      },
      handleScroll: {
        vertTouchDrag: false,
      },
    });

    chartRef.current = chart;

    // Candlestick series (v5 API) — Chinese convention: up=red (oxblood), down=green (vintage emerald)
    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#c75a4a",
      downColor: "#6ea96a",
      borderUpColor: "#e07d6d",
      borderDownColor: "#86c282",
      wickUpColor: "#c75a4a",
      wickDownColor: "#6ea96a",
    });

    // Volume series (v5 API)
    const volumeSeries = chart.addSeries(HistogramSeries, {
      color: "#6b4f15",
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

    // PE line series — bright brass
    let peSeries: ISeriesApi<"Line"> | null = null;
    if (peData && peData.length > 0) {
      peSeries = chart.addSeries(LineSeries, {
        color: "#e5c163",
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

    // PB line series — vintage teal
    let pbSeries: ISeriesApi<"Line"> | null = null;
    if (pbData && pbData.length > 0) {
      pbSeries = chart.addSeries(LineSeries, {
        color: "#5a9a92",
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
        color: d.close >= d.open ? "#c75a4a80" : "#6ea96a80",
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
            <span className="w-3 h-0.5 bg-vt-brass-400"></span>
            <span className="vt-engraved not-italic text-xs uppercase tracking-wider">PE:</span>
            <span className="text-vt-parchment font-[var(--font-geist-mono)]">{legendData.pe.toFixed(2)}</span>
          </div>
        )}
        {legendData.pb !== null && (
          <div className="flex items-center gap-1">
            <span className="w-3 h-0.5 bg-vt-teal-400"></span>
            <span className="vt-engraved not-italic text-xs uppercase tracking-wider">PB:</span>
            <span className="text-vt-parchment font-[var(--font-geist-mono)]">{legendData.pb.toFixed(2)}</span>
          </div>
        )}
      </div>
      <div ref={chartContainerRef} className="w-full h-[250px] sm:h-[400px]" />
    </div>
  );
}
