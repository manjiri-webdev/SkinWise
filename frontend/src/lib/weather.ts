const API_KEY = process.env.NEXT_PUBLIC_OPENWEATHER_API_KEY;

export async function fetchWeather(lat: number, lon: number) {
    const response = await fetch(
        `https://api.openweathermap.org/data/2.5/weather?lat=${lat}&lon=${lon}&appid=${API_KEY}&units=metric`
    );

    if (!response.ok) {
        throw new Error("Failed to fetch weather.");
    }

    return response.json();
}