// Preset stocks for guest users
// These are well-known stocks across different sectors
export const PRESET_STOCKS = [
  { symbol: "601318", name: "中国平安" },
  { symbol: "300750", name: "宁德时代" },
  { symbol: "688981", name: "中芯国际" },
  { symbol: "601899", name: "紫金矿业" },
  { symbol: "600938", name: "中海油服" },
] as const;

export type PresetStock = typeof PRESET_STOCKS[number];
