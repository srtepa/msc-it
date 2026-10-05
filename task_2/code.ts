function processData(items: number[], obj: Record<string, number>): void {
    let sum: number = 0;

    for (let i = 0; i < items.length; i++) {
        sum += items[i];
    }

    for (const key in obj) {
        sum += obj[key];
    }

    for (const value of items) {
        if (value > 0) {
            sum += value;
        } else {
            sum -= value;
        }
    }

    let counter: number = 0;
    while (counter < 10) {
        counter++;
        if (counter === 5) {
            break;
        }
    }

    let attempts: number = 0;
    do {
        attempts++;
    } while (attempts < 3);

    switch (sum) {
        case 0:
            console.log("Сумма равна нулю");
            break;
        case 1:
            console.log("Сумма равна единице");
            break;
        case 2:
        case 3:
            console.log("Сумма равна двум или трём");
            break;
        default:
            console.log("Сумма больше трёх или отрицательная");
            break;
    }

    const status: string = sum > 0 ? "positive" : "non-positive";
    console.log(status);

    try {
        if (sum < 0) {
            throw new Error("Отрицательная сумма");
        }
        console.log("Обработка завершена успешно");
    } catch (e) {
        console.log("Поймана ошибка:", e);
    }
}

const numbers: number[] = [1, -2, 3, -4, 5];
const dictionary: Record<string, number> = { a: 1, b: 2, c: 3 };

processData(numbers, dictionary);
