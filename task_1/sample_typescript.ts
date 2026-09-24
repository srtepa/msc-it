const FRAGILE = 1 << 0;
const HAZARDOUS = 1 << 1;
const EXPRESS = 1 << 2;

type Zone = "local" | "regional" | "international";

interface Shipment {
  id: string;
  zone: Zone;
  weight: number;
  flags: number;
  code?: string | null;
}

function tariff(zone: Zone, distance: number): number {
  let rate = 50;

  switch (zone) {
    case "local": rate += 20; break;
    case "regional": rate += 60; break;
    case "international": rate += 150; break;
    default: rate += 10;
  }

  const extra = distance > 0 ? distance * 0.15 : 5;

  if (distance > 1000 && rate > 100)
    rate += 30;
  else if (distance > 300 || rate >= 150)
    rate += 10;
  else
    rate -= 5;

  return rate + extra;
}

function process(data: Shipment[]): string {
  let total = 0;
  let index = 0;
  const result: string[] = [];

  for (const shipment of data) {
    if (shipment.weight <= 0)
      continue;

    const base = tariff(shipment.zone, 450);
    const fragile = (shipment.flags & FRAGILE) !== 0;
    const hazardous = (shipment.flags & HAZARDOUS) !== 0;
    const express = (shipment.flags & EXPRESS) !== 0;

    const extra = fragile ? 40 : 0;
    const penalty = hazardous && !fragile ? 75 : 150;
    const multiplier = express ? 1.5 : 1;
    const cost = (base + extra + penalty) * multiplier;
    const code = shipment.code ?? "NONE";

    result.push(`${shipment.id}: ${cost.toFixed(2)} ${code}`);
    total += cost;
    index++;
  }

  while (index > 0) {
    index--;
    result[index] += " OK";
  }

  return result.join("\n") + `\nTotal: ${total.toFixed(2)}`;
}

const cargo: Shipment[] = [
  { id: "A01", zone: "international", weight: 20, flags: FRAGILE | EXPRESS, code: "X1" },
  { id: "B02", zone: "local", weight: 8, flags: HAZARDOUS, code: null },
  { id: "C03", zone: "regional", weight: 15, flags: 0 }
];

console.log(process(cargo));
console.log(new Date().toISOString());

enum Priority {
    Low = 1,
    High = 2
}

class Box {
    constructor(public value: number) {}

    getValue(): number {
        return this.value;
    }
}

const check = (x: number): boolean => x >= 10;

try {
    if (check(20)) {
        throw new Error("Test");
    }
} catch (error) {
    console.log(error);
}
