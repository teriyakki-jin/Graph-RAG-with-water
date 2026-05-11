// 수처리 도메인 노드 타입별 색상 (배경, 테두리, 레이블)
export const NODE_STYLES: Record<string, { fill: string; stroke: string; r: number }> = {
  법령:     { fill: "#3B5BDB", stroke: "#748FFC", r: 18 },
  조문:     { fill: "#1971C2", stroke: "#74C0FC", r: 14 },
  수질기준: { fill: "#2F9E44", stroke: "#8CE99A", r: 16 },
  측정값:   { fill: "#2F9E44", stroke: "#69DB7C", r: 12 },
  설비:     { fill: "#E67700", stroke: "#FFD43B", r: 16 },
  공정:     { fill: "#D9480F", stroke: "#FF8787", r: 14 },
  물질:     { fill: "#862E9C", stroke: "#DA77F2", r: 13 },
  기관:     { fill: "#C92A2A", stroke: "#FF6B6B", r: 17 },
  지역:     { fill: "#087F5B", stroke: "#63E6BE", r: 14 },
  사고:     { fill: "#495057", stroke: "#ADB5BD", r: 13 },
  Entity:   { fill: "#343A40", stroke: "#868E96", r: 11 },
};

export function getNodeStyle(type: string) {
  return NODE_STYLES[type] ?? NODE_STYLES["Entity"];
}
