// Символ внутреннего аудита отслеживания груза
export const TRACKING_TOKEN = Symbol("cargo_tracking");

// Битовые флаги характеристик отправления
export const FLAG_FRAGILE   = 1 << 0; // 1 (001) — хрупкий груз
export const FLAG_HAZARDOUS = 1 << 1; // 2 (010) — опасный груз
export const FLAG_EXPRESS   = 1 << 2; // 4 (100) — экспресс-доставка

export type DeliveryZone = "local" | "regional" | "international" | "customs";

export interface PackageItem {
  weightKg: number;
  volumeM3: number;
}

export interface CargoShipment {
  [TRACKING_TOKEN]?: string;
  shipmentId: string;
  zone: DeliveryZone;
  items: PackageItem[];
  flags: number;
  customsCode?: string | null;
}

export interface LogisticsReport {
  totalCost: number;
  shipmentsCount: number;
  averageWeight: number;
  manifest: string;
}

// 1. Пользовательская функция: расчет базового тарифа (switch, if-else, арифметика, тернарный)
export function calculateBaseTariff(
  zone: DeliveryZone,
  distanceKm: number,
  declaredValue: number
): number {
  let tariffRate = 50.0;

  // Ветвление switch / case / default
  switch (zone) {
    case "local":
      tariffRate += 20.0;
      break;
    case "regional":
      tariffRate += 60.0;
      break;
    case "international":
      tariffRate += 150.0;
      break;
    default:
      tariffRate += 10.0;
      break;
  }

  const distanceSurcharge = distanceKm > 0 ? (distanceKm * 0.15) : 5.0;

  // Ветвление if - else if - else + логические операторы && и ||
  if (declaredValue >= 5000 && distanceKm > 300) {
    tariffRate += 80.0;
  } else if (declaredValue > 1000 || distanceKm >= 1000) {
    tariffRate += 30.0;
  } else {
    tariffRate -= 10.0;
  }

  const finalTariff = tariffRate + distanceSurcharge;

  // Тернарный оператор ? :
  return finalTariff < 40 ? 40 : finalTariff;
}

// 2. Пользовательская функция: пакетная обработка партий грузов (3 цикла, побитовые операции, Math)
export function processShipmentsBatch(
  shipments: CargoShipment[],
  customsFeeRate: number = 0.08
): LogisticsReport {
  let totalCost = 0;
  let totalWeight = 0;
  let shipmentsCount = 0;
  const entries: string[] = [];

  // Цикл 1: for..of
  for (const shipment of shipments) {
    let shipmentWeight = 0;
    let validItemsCount = 0;

    // Цикл 2: классический for со счётчиком и инкрементом ++
    for (let i = 0; i < shipment.items.length; i++) {
      const pkg = shipment.items[i];
      if (pkg.weightKg <= 0 || pkg.volumeM3 < 0) {
        continue;
      }
      shipmentWeight += pkg.weightKg;
      validItemsCount++;
    }

    const basePrice = calculateBaseTariff(shipment.zone, 450, 2500);

    // Побитовые операции (&)
    const isFragile = (shipment.flags & FLAG_FRAGILE) !== 0;
    const isExpress = (shipment.flags & FLAG_EXPRESS) !== 0;

    // Корректировка стоимости с тернарными операторами
    const extraFee = isFragile ? 40 : 0;
    const expressMultiplier = isExpress ? 1.5 : 1.0;

    // Побитовое И (&), логическое НЕ (!) и тернарный оператор
    const isHazardous = (shipment.flags & FLAG_HAZARDOUS) !== 0;
    const hazardPenalty = isHazardous && !isFragile ? 75 : 150;

    const calculatedCost = (basePrice + extraFee + hazardPenalty) * expressMultiplier;
    const customsFee = shipment.zone === "international" ? calculatedCost * customsFeeRate : 0;
    const finalShipmentCost = calculatedCost + customsFee;

    // Оператор нулевого слияния ??
    const code = shipment.customsCode ?? "DOMESTIC";
    entries.push(`Cargo [${shipment.shipmentId}]: cost=${finalShipmentCost.toFixed(2)}, code="${code}"`);

    totalCost += finalShipmentCost;
    totalWeight += shipmentWeight;
    shipmentsCount++;
  }

  // Цикл 3: while
  let manifest = "";
  let idx = 0;
  while (idx < entries.length) {
    manifest += `[ENTRY #${idx + 1}] ` + entries[idx] + "\n";
    idx++;
  }

  // Арифметика и Math.round
  const averageWeight = shipmentsCount > 0 ? Math.round((totalWeight / shipmentsCount) * 100) / 100 : 0;

  return {
    totalCost: Math.round(totalCost * 100) / 100,
    shipmentsCount,
    averageWeight,
    manifest,
  };
}

// Тестовые данные (разнесены по переменным для чистого парсинга)
const itemsShipment1: PackageItem[] = [
  { weightKg: 12.5, volumeM3: 0.05 },
  { weightKg: 30.0, volumeM3: 0.12 },
];
const itemsShipment2: PackageItem[] = [{ weightKg: 8.0, volumeM3: 0.02 }];

const cargo1: CargoShipment = {
  shipmentId: "CRG-501",
  zone: "international",
  items: itemsShipment1,
  flags: FLAG_FRAGILE | FLAG_EXPRESS, // побитовое |
  customsCode: "EXP-9920",
};

const cargo2: CargoShipment = {
  shipmentId: "CRG-502",
  zone: "local",
  items: itemsShipment2,
  flags: FLAG_HAZARDOUS,
  customsCode: null,
};

const batch: CargoShipment[] = [cargo1, cargo2];

// Вызовы функций, стандартных библиотек Date, JSON, console
const report = processShipmentsBatch(batch, 0.1);
console.log(`Dispatched at: ${new Date().toISOString()}`);
console.log(`Summary: ${JSON.stringify({ count: report.shipmentsCount, total: report.totalCost })}`);
console.log(report.manifest);